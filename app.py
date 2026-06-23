import os
from flask import Flask, request, jsonify, send_from_directory, Response

import database
import scraper

app = Flask(__name__, static_folder="static", static_url_path="")


@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/api/lookup", methods=["POST"])
def api_lookup():
    data = request.get_json(silent=True) or {}
    barcode = data.get("barcode", "").strip()
    if not barcode:
        return jsonify({"error": "Se requiere código de barras"}), 400

    fuente = data.get("fuente")
    ia_mode = data.get("ia_mode", False)

    local = database.obtener_por_barcode(barcode)
    if local:
        local["_cached"] = True
        return jsonify(local)

    producto = scraper.lookup_producto(barcode, fuente=fuente)
    if not producto:
        return jsonify({"error": "Producto no encontrado en ninguna fuente"}), 404

    producto["ia_mode"] = ia_mode
    return jsonify(producto)


@app.route("/api/products", methods=["GET"])
def api_list_products():
    search = request.args.get("search", "").strip() or None
    categoria = request.args.get("categoria", "").strip() or None
    productos = database.obtener_productos(search=search, categoria=categoria)
    return jsonify(productos)


@app.route("/api/products", methods=["POST"])
def api_save_product():
    data = request.get_json(silent=True) or {}
    required = ["codigo_barras", "nombre"]
    for field in required:
        if not data.get(field):
            return jsonify({"error": f"Campo requerido: {field}"}), 400

    pid = database.guardar_producto(data)
    return jsonify({"id": pid, "message": "Producto guardado"})


@app.route("/api/products/<int:pid>", methods=["PUT"])
def api_update_product(pid):
    data = request.get_json(silent=True) or {}
    database.actualizar_producto(pid, data)
    return jsonify({"message": "Producto actualizado"})


@app.route("/api/products/<int:pid>", methods=["DELETE"])
def api_delete_product(pid):
    database.eliminar_producto(pid)
    return jsonify({"message": "Producto eliminado"})


@app.route("/api/products/export", methods=["POST"])
def api_export_products():
    data = request.get_json(silent=True) or {}
    ids = data.get("ids", [])
    fmt = data.get("formato", "csv")

    if not ids:
        return jsonify({"error": "Seleccioná al menos un producto"}), 400

    content = database.exportar_productos(ids, formato=fmt)

    filename = f"productos.{fmt}"
    mime = "text/csv" if fmt == "csv" else "application/json"

    return Response(
        content,
        mimetype=mime,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@app.route("/api/config", methods=["GET"])
def api_get_config():
    return jsonify(database.get_config())


@app.route("/api/config", methods=["PUT"])
def api_update_config():
    data = request.get_json(silent=True) or {}
    database.set_config(data)
    return jsonify({"message": "Configuración actualizada"})


@app.route("/api/dashboard", methods=["GET"])
def api_dashboard():
    return jsonify(database.get_dashboard())


if __name__ == "__main__":
    database.init_db()
    print("Servidor corriendo en http://localhost:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
