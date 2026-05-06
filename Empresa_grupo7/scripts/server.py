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

    # Cargamos las hojas necesarias
    from analizar import EXCEL_PATH
    import pandas as pd
    
    xls = pd.ExcelFile(EXCEL_PATH)
    df_cat = pd.read_excel(xls, "Catálogo de Productos")
    df_pred = pd.read_excel(xls, "Predicciones y Recomendaciones")
    df_ventas = pd.read_excel(xls, "Ventas Históricas")

    # Buscamos la info del producto
    prod_info = df_cat[df_cat["Nombre Producto"] == nombre_producto].iloc[0].to_dict()
    # Buscamos predicción asociada
    pred_info = df_pred[df_pred["Categoría"] == prod_info["Categoría"]].iloc[0].to_dict()
    
    # Calculamos satisfacción promedio desde Ventas Históricas
    ventas_prod = df_ventas[df_ventas["Categoría"] == prod_info["Categoría"]]
    satisfaccion = ventas_prod["Satisfacción Cliente (1-5)"].mean() if not ventas_prod.empty else 0

    # Armamos la Ficha Técnica extendida
    detalle = {
        "adn": {
            "materiales": prod_info.get("Material Principal", "No especificado"),
            "composicion": "98% Algodón, 2% Elastano (Est.)", # Ejemplo de dato calculado
            "talles_sugeridos": "S al XL (Calce Regular)"
        },
        "target": {
            "edad": pred_info.get("Edad Target", "Todo público"),
            "genero": pred_info.get("Género Target", "Unisex"),
            "canal": pred_info.get("Canal Recomendado", "Omnicanal")
        },
        "bi": {
            "competencia": pred_info.get("Competencia (Alta/Media/Baja)", "Media"),
            "satisfaccion": round(float(satisfaccion), 1),
            "confianza_modelo": pred_info.get("Confianza Modelo %", 80)
        }
    }
    
    return jsonify(detalle)

if __name__ == '__main__':
    print("Servidor levantado en http://localhost:5000")
    app.run(debug=True, port=5000)
    
    
    
