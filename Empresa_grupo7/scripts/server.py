from flask import Flask, request, jsonify
from flask_cors import CORS
from analizar import analizar # Importamos tu función principal

app = Flask(__name__)
CORS(app) 

@app.route('/api/analizar', methods=['GET'])
def api_analizar():
    
    termino = request.args.get('termino')
    
    if not termino:
        return jsonify({"error": "No se envió ningún término"}), 400
        
    print(f"Buscando desde la web: {termino}")
    

    resultado = analizar(termino)
    
   
    return jsonify(resultado)

@app.route('/api/detalle', methods=['GET'])
def api_detalle():
    nombre_producto = request.args.get('nombre')
    if not nombre_producto:
        return jsonify({"error": "Falta el nombre del producto"}), 400

    from analizar import EXCEL_PATH
    import pandas as pd
    
    xls = pd.ExcelFile(EXCEL_PATH)
    df_cat = pd.read_excel(xls, "Catálogo de Productos")
    df_pred = pd.read_excel(xls, "Predicciones y Recomendaciones")
    df_ventas = pd.read_excel(xls, "Ventas Históricas")

    prod_info = df_cat[df_cat["Nombre Producto"] == nombre_producto].iloc[0].to_dict()
    
    # Manejo de error por si no hay predicción exacta
    try:
        pred_info = df_pred[df_pred["Categoría"] == prod_info["Categoría"]].iloc[0].to_dict()
    except:
        pred_info = {}
    
    ventas_prod = df_ventas[df_ventas["Categoría"] == prod_info["Categoría"]]
    satisfaccion = ventas_prod["Satisfacción Cliente (1-5)"].mean() if not ventas_prod.empty else 0

    # Diccionario de imágenes "mock" para el prototipo
    imagenes_demo = {
        "jeans": "https://images.unsplash.com/photo-1542272604-787c3835535d?w=400&q=80",
        "buzos": "https://images.unsplash.com/photo-1556821840-3a63f95609a7?w=400&q=80",
        "camisetas": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&q=80",
        "faldas": "https://images.unsplash.com/photo-1583496661160-c588c2569279?w=400&q=80",
        "default": "https://images.unsplash.com/photo-1445205170230-053b83016050?w=400&q=80"
    }
    
    cat_lower = str(prod_info.get("Categoría", "")).lower()
    img_url = imagenes_demo.get(cat_lower, imagenes_demo["default"])

    detalle = {
        "imagen_url": img_url, # <-- Nueva clave de imagen
        "adn": {
            "materiales": prod_info.get("Material Principal", "No especificado"),
            "composicion": "98% Algodón, 2% Elastano (Est.)", 
            "talles_sugeridos": "S al XL (Calce Regular)"
        },
        "target": {
            "edad": pred_info.get("Edad Target", "18-35 años"),
            "genero": pred_info.get("Género Target", "Unisex"),
            "canal": pred_info.get("Canal Recomendado", "E-commerce & Local")
        },
        "bi": {
            "competencia": pred_info.get("Competencia (Alta/Media/Baja)", "Media"),
            "satisfaccion": round(float(satisfaccion), 1) if satisfaccion else 4.2,
            "confianza_modelo": pred_info.get("Confianza Modelo %", 85)
        }
    }
    
    return jsonify(detalle)

if __name__ == '__main__':
    print("Servidor levantado en http://localhost:5000")
    app.run(debug=True, port=5000)
    
    
    
