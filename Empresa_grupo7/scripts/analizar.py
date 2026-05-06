"""
TrendSight Co. — Motor de Análisis de Stock
==============================================
Cruza datos del Excel interno con Google Trends para generar
recomendaciones de compra de stock para emprendedores de moda.

Uso:
    python analizar.py "jeans"
    python analizar.py "buzo"
    python analizar.py "pantalon"
"""

import sys
import json
import os
import re
import pandas as pd
from datetime import datetime, timedelta
import time
import random
from pytrends.request import TrendReq
import requests

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────

EXCEL_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "FashionAnalytics_BaseDatos.xlsx")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "..", "frontend", "data.json")

# Mapeo de términos en español a palabras clave para búsqueda
KEYWORD_MAP = {
    "buzo": ["hoodie", "sweater", "buzo"],
    "buzos": ["hoodie", "sweater"],
    "hoodie": ["hoodie"],
    "hoodies": ["hoodies"],
    "sweater": ["sweater"],
    "jeans": ["jeans"],
    "jean": ["jeans"],
    "pantalon": ["pantalones", "jeans"],
    "pantalones": ["pantalones"],
    "falda": ["faldas"],
    "faldas": ["faldas"],
    "vestido": ["vestidos"],
    "vestidos": ["vestidos"],
    "camisa": ["camisas"],
    "camisas": ["camisas"],
    "camiseta": ["camisetas"],
    "remera": ["camisetas"],
    "camisetas": ["camisetas"],
    "short": ["shorts"],
    "shorts": ["shorts"],
    "abrigo": ["abrigos"],
    "abrigos": ["abrigos"],
    "chaqueta": ["chaquetas"],
    "chaquetas": ["chaquetas"],
    "blazer": ["blazers"],
    "blazers": ["blazers"],
    "leggings": ["leggings"],
    "jogger": ["joggers"],
    "joggers": ["joggers"],
    "top": ["tops"],
    "tops": ["tops"],
    "jumpsuit": ["jumpsuits"],
    "traje": ["trajes"],
    "trajes": ["trajes"],
    "overalls": ["overalls"],
    "overall": ["overalls"],
    "bodysuit": ["bodysuits"],
    "bodysuits": ["bodysuits"],
    "tunica": ["túnicas"],
    "túnica": ["túnicas"],
}


# ─── FUNCIONES DE PROCESAMIENTO DEL EXCEL ─────────────────────────────────────

def normalizar(texto: str) -> str:
    """Elimina tildes y pasa a minúsculas para comparaciones robustas."""
    t = texto.lower().strip()
    for a, b in [("á","a"),("é","e"),("í","i"),("ó","o"),("ú","u"),("ü","u"),("ñ","n")]:
        t = t.replace(a, b)
    return t


def cargar_excel(path: str) -> dict:
    """Carga todas las hojas relevantes del Excel."""
    hojas = {}
    try:
        hojas["productos"]   = pd.read_excel(path, sheet_name="Catálogo de Productos")
        hojas["tendencias"]  = pd.read_excel(path, sheet_name="Tendencias de Moda")
        hojas["predicciones"]= pd.read_excel(path, sheet_name="Predicciones y Recomendaciones")
        hojas["ventas"]      = pd.read_excel(path, sheet_name="Ventas Históricas")
    except FileNotFoundError:
        print(f"ERROR: No se encontró el archivo Excel en: {path}")
        sys.exit(1)
    return hojas


def buscar_productos(df: pd.DataFrame, termino: str) -> pd.DataFrame:
    """
    Filtra el catálogo de productos buscando el término en:
    Categoría, Subcategoría, Nombre Producto y Tendencia Asociada.
    """
    termino_norm = normalizar(termino)
    
    # Palabras clave adicionales mapeadas
    keywords = KEYWORD_MAP.get(termino_norm, [termino_norm])
    
    # Columnas donde buscar
    cols = ["Categoría", "Subcategoría", "Nombre Producto", "Tendencia Asociada"]
    
    mask = pd.Series([False] * len(df), index=df.index)
    for col in cols:
        if col in df.columns:
            col_norm = df[col].fillna("").apply(normalizar)
            for kw in keywords:
                mask = mask | col_norm.str.contains(kw, na=False)
    
    return df[mask]


def calcular_metricas_excel(productos: pd.DataFrame, ventas: pd.DataFrame) -> dict:
    """
    Calcula métricas agregadas del Excel para los productos filtrados.
    """
    if productos.empty:
        return {}

    # Puntuación Lyst promedio
    lyst_prom = productos["Puntuación Lyst (0-100)"].mean() if "Puntuación Lyst (0-100)" in productos.columns else 0
    
    # Búsquedas semanales estimadas
    busq_prom = productos["Búsquedas Semanales (est.)"].mean() if "Búsquedas Semanales (est.)" in productos.columns else 0
    
    # Margen bruto promedio
    if "Margen Bruto %" in productos.columns:
        productos = productos.copy()
        productos["margen_num"] = productos["Margen Bruto %"].apply(
            lambda x: float(str(x).replace("%","").strip()) if pd.notna(x) else 0
        )
        margen_prom = productos["margen_num"].mean()
    else:
        margen_prom = 0

    # Tendencias más frecuentes
    tendencias_count = {}
    if "Tendencia Asociada" in productos.columns:
        tendencias_count = productos["Tendencia Asociada"].value_counts().head(3).to_dict()

    # Marcas más frecuentes
    marcas_top = []
    if "Marca" in productos.columns:
        marcas_top = productos["Marca"].value_counts().head(5).index.tolist()

    # Colores más frecuentes
    colores_top = []
    if "Color Principal" in productos.columns:
        colores_top = productos["Color Principal"].value_counts().head(3).index.tolist()

    # Precio promedio
    precio_prom = 0
    if "Precio USD (retail)" in productos.columns:
        precio_prom = productos["Precio USD (retail)"].mean()

    # Temporada más frecuente
    temporada = "N/A"
    if "Temporada" in productos.columns:
        temporada = productos["Temporada"].mode().iloc[0] if not productos["Temporada"].mode().empty else "N/A"

    # Cruzar con ventas si hay datos
    revenue_total = 0
    satisfaccion_prom = 0
    if not ventas.empty and "Categoría" in ventas.columns:
        cats = productos["Categoría"].unique() if "Categoría" in productos.columns else []
        ventas_cat = ventas[ventas["Categoría"].isin(cats)] if len(cats) > 0 else pd.DataFrame()
        if not ventas_cat.empty:
            if "Revenue Neto USD" in ventas_cat.columns:
                revenue_total = ventas_cat["Revenue Neto USD"].sum()
            if "Satisfacción Cliente (1-5)" in ventas_cat.columns:
                satisfaccion_prom = ventas_cat["Satisfacción Cliente (1-5)"].mean()

    return {
        "lyst_score": round(lyst_prom, 1),
        "busquedas_semanales": round(busq_prom),
        "margen_bruto_pct": round(margen_prom, 1),
        "tendencias_top": list(tendencias_count.keys()),
        "marcas_top": marcas_top,
        "colores_top": colores_top,
        "precio_retail_prom": round(precio_prom, 2),
        "temporada_dominante": str(temporada),
        "total_productos_encontrados": len(productos),
        "revenue_historico": round(revenue_total, 2),
        "satisfaccion_cliente": round(satisfaccion_prom, 2),
    }


from datetime import datetime

def obtener_predicciones(df_pred: pd.DataFrame, termino: str) -> list:
    """
    Busca predicciones relevantes al término buscado y que sean
    de la temporada actual (2026) o futura (2027).
    """
    termino_norm = normalizar(termino)
    keywords = KEYWORD_MAP.get(termino_norm, [termino_norm])
    
    # Obtenemos el año actual dinámicamente (2026)
    anio_actual = datetime.now().year 
    
    # Filtramos por término de búsqueda
    cols = ["Categoría", "Subcategoría", "Tendencia Proyectada"]
    mask_busqueda = pd.Series([False] * len(df_pred), index=df_pred.index)
    for col in cols:
        if col in df_pred.columns:
            col_norm = df_pred[col].fillna("").apply(normalizar)
            for kw in keywords:
                mask_busqueda = mask_busqueda | col_norm.str.contains(kw, na=False)
    
    # Filtramos para que solo muestre años actuales o futuros (>= 2026)
    # Buscamos el año dentro del string "Otoño/Invierno 2025"
    def es_vigente(temp_str):
        import re
        match = re.search(r'(\d{4})', str(temp_str))
        if match:
            return int(match.group(1)) >= anio_actual
        return False

    mask_fecha = df_pred["Temporada Objetivo"].apply(es_vigente)
    
    # Aplicamos ambos filtros
    preds = df_pred[mask_busqueda & mask_fecha].head(5)
    
    # Si después de filtrar por año no quedó nada, 
    # traemos las más recientes aunque sean viejas para no dejar la web vacía
    if preds.empty:
        preds = df_pred[mask_busqueda].head(5)

    resultado = []
    for _, row in preds.iterrows():
        resultado.append({
            "temporada_objetivo": str(row.get("Temporada Objetivo", "N/A")),
            "categoria": str(row.get("Categoría", "N/A")),
            "subcategoria": str(row.get("Subcategoría", "N/A")),
            "color_recomendado": str(row.get("Color Recomendado", "N/A")),
            "tendencia": str(row.get("Tendencia Proyectada", "N/A")),
            "probabilidad_exito": str(row.get("Probabilidad de Éxito %", "N/A")),
            "rango_precio": str(row.get("Rango de Precio Óptimo USD", "N/A")),
            "recomendacion_inversion": str(row.get("Recomendación de Inversión", "N/A")),
            "nivel_riesgo": str(row.get("Nivel de Riesgo", "N/A")),
            "confianza_modelo": str(row.get("Confianza Modelo %", "N/A")),
        })
    return resultado


# ─── FUNCIONES DE GOOGLE TRENDS ───────────────────────────────────────────────

TRENDS_CACHE = {}

def consultar_google_trends(termino: str) -> dict:
    termino_norm = normalizar(termino)
    resultado = {
        "disponible": False, "interes_actual": 0, "momentum": "estable", 
        "tendencia_direccion": "estable", "variacion_pct": 0, "error": None
    }

    try:
        # 1. Creamos una sesión real para "robar" la cookie de Google
        print("  🍪 Obteniendo cookie de sesión de Google...")
        session = requests.Session()
        session.get('https://trends.google.com/?geo=AR', headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'}, timeout=10)
        cookies = session.cookies.get_dict()

        # 2. Le pasamos la cookie a pytrends
        pytrends = TrendReq(
            hl='es-AR', 
            tz=180, 
            timeout=(15, 30),
            requests_args={'cookies': cookies, 'headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/124.0.0.0 Safari/537.36'}}
        )

        kw_list = KEYWORD_MAP.get(termino_norm, [termino])[:3]
        pytrends.build_payload(kw_list, cat=0, timeframe='today 12-m', geo='AR')
        df = pytrends.interest_over_time()
        
        if df.empty:
            resultado["error"] = "Google no tiene volumen de búsquedas."
            return resultado
        
        # --- CÁLCULOS ---
        col_usar = kw_list[0] if kw_list[0] in df.columns else df.columns[0]
        serie = df[col_usar]
        ultimas_4 = serie.tail(4).mean()
        anteriores_4 = serie.iloc[-8:-4].mean() if len(serie) >= 8 else serie.head(4).mean()
        variacion = ((ultimas_4 - anteriores_4) / anteriores_4) * 100 if anteriores_4 > 0 else 0
        
        resultado.update({
            "disponible": True,
            "interes_actual": round(ultimas_4, 1),
            "momentum": "alza" if variacion > 5 else "baja" if variacion < -5 else "estable",
            "tendencia_direccion": "subiendo" if variacion > 0 else "bajando",
            "variacion_pct": round(variacion, 1),
            "interes_promedio_reciente": round(float(ultimas_4), 1),
            "interes_promedio_anterior": round(float(anteriores_4), 1)
        })

    except Exception as e:
        print(f"  ⚠ Google sigue bloqueando: {str(e)[:40]}")
        resultado["error"] = "Modo Offline activo."

    return resultado

# ─── LÓGICA DE DECISIÓN DE STOCK ──────────────────────────────────────────────

def calcular_decision_stock(metricas_excel: dict, trends: dict, predicciones: list) -> dict:
    """
    Reglas de decisión para la recomendación de stock.
    
    Combina:
    - Lyst Score (0-100): demanda global de marca/prenda
    - Búsquedas semanales estimadas
    - Momentum de Google Trends
    - Margen bruto
    - Predicciones internas
    
    Devuelve: decision, puntaje_total, explicacion, icono, color_ui
    """
    puntaje = 0
    razones = []

    lyst = metricas_excel.get("lyst_score", 0)
    margen = metricas_excel.get("margen_bruto_pct", 0)
    busquedas = metricas_excel.get("busquedas_semanales", 0)
    
    # ── REGLA 1: Lyst Score ──────────────────────────────────
    if lyst >= 80:
        puntaje += 35
        razones.append(f"Lyst Score alto ({lyst}/100): alta demanda global")
    elif lyst >= 60:
        puntaje += 20
        razones.append(f"Lyst Score moderado ({lyst}/100)")
    elif lyst >= 40:
        puntaje += 10
        razones.append(f"Lyst Score medio-bajo ({lyst}/100)")
    else:
        puntaje += 0
        razones.append(f"Lyst Score bajo ({lyst}/100): demanda limitada")

    # ── REGLA 2: Google Trends Momentum ──────────────────────
    if trends.get("disponible"):
        variacion = trends.get("variacion_pct", 0)
        if variacion > 20:
            puntaje += 30
            razones.append(f"Google Trends subiendo fuerte (+{variacion:.0f}%)")
        elif variacion > 5:
            puntaje += 20
            razones.append(f"Google Trends en alza (+{variacion:.0f}%)")
        elif variacion >= -5:
            puntaje += 10
            razones.append("Google Trends estable")
        else:
            puntaje += 0
            razones.append(f"Google Trends bajando ({variacion:.0f}%)")
    else:
        puntaje += 10  # neutro si no hay datos de trends
        razones.append("Sin datos de Google Trends (puntuación neutra)")

    # ── REGLA 3: Margen Bruto ────────────────────────────────
    if margen >= 60:
        puntaje += 20
        razones.append(f"Margen bruto alto ({margen:.0f}%): buena rentabilidad")
    elif margen >= 45:
        puntaje += 12
        razones.append(f"Margen bruto moderado ({margen:.0f}%)")
    else:
        puntaje += 5
        razones.append(f"Margen bruto bajo ({margen:.0f}%)")

    # ── REGLA 4: Predicciones internas ───────────────────────
    if predicciones:
        recs = [p.get("recomendacion_inversion", "") for p in predicciones]
        if any("prioritaria" in r.lower() for r in recs):
            puntaje += 15
            razones.append("Predicción interna: Compra prioritaria recomendada")
        elif any("moderada" in r.lower() for r in recs):
            puntaje += 8
            razones.append("Predicción interna: Compra moderada recomendada")
        elif any("evitar" in r.lower() for r in recs):
            puntaje -= 10
            razones.append("Predicción interna: Evitar por ahora")
        elif any("test" in r.lower() or "pequeña" in r.lower() for r in recs):
            puntaje += 5
            razones.append("Predicción interna: Compra de prueba recomendada")

    # ── REGLA 5: Volumen de búsquedas ────────────────────────
    if busquedas > 70000:
        puntaje += 5
        razones.append(f"Alto volumen de búsquedas estimadas ({busquedas:,.0f}/sem)")
    elif busquedas > 40000:
        puntaje += 2
        razones.append(f"Volumen de búsquedas moderado ({busquedas:,.0f}/sem)")

    # Normalizar puntaje a 0-100
    puntaje = max(0, min(100, puntaje))

    # ── DECISIÓN FINAL ───────────────────────────────────────
    if puntaje >= 75:
        decision = "Comprar fuerte"
        icono = "🚀"
        color = "green"
        descripcion = "Alta demanda + tendencia positiva. Invertir con confianza."
    elif puntaje >= 55:
        decision = "Comprar moderado"
        icono = "✅"
        color = "blue"
        descripcion = "Señales positivas. Compra recomendada con volumen moderado."
    elif puntaje >= 35:
        decision = "Probar con poco stock"
        icono = "⚠️"
        color = "orange"
        descripcion = "Señales mixtas. Entrar con pocas unidades y medir respuesta."
    else:
        decision = "Evitar / Esperar"
        icono = "❌"
        color = "red"
        descripcion = "Señales débiles o negativas. No invertir en este momento."

    return {
        "decision": decision,
        "puntaje": puntaje,
        "icono": icono,
        "color": color,
        "descripcion": descripcion,
        "razones": razones,
    }


# ─── FUNCIÓN PRINCIPAL ────────────────────────────────────────────────────────

def analizar(termino: str) -> dict:
    """
    Análisis completo para un término de búsqueda.
    """
    print(f"\n🔍 Analizando: '{termino}'")
    print("─" * 50)

    # 1. Cargar Excel
    print("📂 Cargando base de datos...")
    hojas = cargar_excel(EXCEL_PATH)

    # 2. Buscar productos relacionados
    print("🏷  Filtrando productos...")
    productos_filtrados = buscar_productos(hojas["productos"], termino)
    print(f"   → {len(productos_filtrados)} productos encontrados")

    # 3. Calcular métricas del Excel
    metricas = calcular_metricas_excel(productos_filtrados, hojas["ventas"])

    # 4. Obtener predicciones
    print("🔮 Obteniendo predicciones internas...")
    predicciones = obtener_predicciones(hojas["predicciones"], termino)
    print(f"   → {len(predicciones)} predicciones encontradas")

    # 5. Consultar Google Trends
    print("📈 Consultando Google Trends (AR)...")
    trends = consultar_google_trends(termino)
    if trends["disponible"]:
        print(f"   → Interés actual: {trends['interes_actual']}/100 | Momentum: {trends['momentum']}")
    else:
        print(f"   → {trends.get('error', 'Sin datos')}")

    # 6. Calcular decisión de stock
    print("⚡ Calculando decisión de stock...")
    decision = calcular_decision_stock(metricas, trends, predicciones)
    print(f"   → {decision['icono']} {decision['decision']} (puntaje: {decision['puntaje']}/100)")

    # 7. Armar resultado final
    resultado = {
        "meta": {
            "termino_buscado": termino,
            "fecha_analisis": datetime.now().isoformat(),
            "version": "1.0.0",
        },
        "resumen": {
            "decision": decision["decision"],
            "puntaje": decision["puntaje"],
            "icono": decision["icono"],
            "color": decision["color"],
            "descripcion": decision["descripcion"],
            "razones": decision["razones"],
        },
        "excel": metricas,
        "google_trends": trends,
        "predicciones": predicciones,
        "productos_muestra": [],
    }

    # Agregar muestra de productos top (los 5 con mayor Lyst Score)
    if not productos_filtrados.empty and "Puntuación Lyst (0-100)" in productos_filtrados.columns:
        top5 = productos_filtrados.nlargest(5, "Puntuación Lyst (0-100)")
        for _, row in top5.iterrows():
            resultado["productos_muestra"].append({
                "nombre": str(row.get("Nombre Producto", "N/A")),
                "marca": str(row.get("Marca", "N/A")),
                "categoria": str(row.get("Categoría", "N/A")),
                "tendencia": str(row.get("Tendencia Asociada", "N/A")),
                "lyst_score": int(row.get("Puntuación Lyst (0-100)", 0)),
                "precio_retail": float(row.get("Precio USD (retail)", 0)),
                "margen": str(row.get("Margen Bruto %", "N/A")),
                "color": str(row.get("Color Principal", "N/A")),
                "temporada": str(row.get("Temporada", "N/A")),
            })

    return resultado


# ─── PUNTO DE ENTRADA ─────────────────────────────────────────────────────────

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python analizar.py <termino>")
        print("Ejemplo: python analizar.py jeans")
        sys.exit(1)

    termino = " ".join(sys.argv[1:])
    
    resultado = analizar(termino)

    # Guardar JSON
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(resultado, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Resultado guardado en: {OUTPUT_PATH}")
    print(f"📊 Decisión final: {resultado['resumen']['icono']} {resultado['resumen']['decision']}")
    print(f"   Puntaje: {resultado['resumen']['puntaje']}/100")
    print(f"   {resultado['resumen']['descripcion']}")
