import sqlite3
import json
import csv
import io
from datetime import datetime

DB_PATH = "productos.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS productos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo_barras TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            marca TEXT,
            descripcion TEXT,
            precio_referencia REAL,
            imagen_url TEXT,
            sku TEXT,
            propiedades TEXT,
            fuente TEXT,
            cantidad REAL DEFAULT 0,
            ia_analizado INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    try:
        conn.execute("ALTER TABLE productos ADD COLUMN cantidad REAL DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def guardar_producto(data):
    conn = get_db()
    propiedades_json = json.dumps(data.get("propiedades", {}), ensure_ascii=False)
    cursor = conn.execute("""
        INSERT INTO productos (codigo_barras, nombre, marca, descripcion,
            precio_referencia, imagen_url, sku, propiedades, fuente, cantidad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(codigo_barras) DO UPDATE SET
            nombre=excluded.nombre,
            marca=excluded.marca,
            descripcion=excluded.descripcion,
            precio_referencia=excluded.precio_referencia,
            imagen_url=excluded.imagen_url,
            sku=excluded.sku,
            propiedades=excluded.propiedades,
            fuente=excluded.fuente,
            cantidad=excluded.cantidad,
            updated_at=CURRENT_TIMESTAMP
    """, (
        data["codigo_barras"],
        data["nombre"],
        data.get("marca"),
        data.get("descripcion"),
        data.get("precio_referencia"),
        data.get("imagen_url"),
        data.get("sku"),
        propiedades_json,
        data.get("fuente"),
        data.get("cantidad", 0),
    ))
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def obtener_productos(search=None):
    conn = get_db()
    if search:
        rows = conn.execute(
            "SELECT * FROM productos WHERE nombre LIKE ? OR codigo_barras LIKE ? OR marca LIKE ? ORDER BY updated_at DESC",
            (f"%{search}%", f"%{search}%", f"%{search}%")
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM productos ORDER BY updated_at DESC"
        ).fetchall()
    conn.close()
    productos = [dict(r) for r in rows]
    for p in productos:
        if p["propiedades"]:
            try:
                p["propiedades"] = json.loads(p["propiedades"])
            except json.JSONDecodeError:
                p["propiedades"] = {}
        else:
            p["propiedades"] = {}
    return productos


def obtener_por_barcode(codigo_barras):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM productos WHERE codigo_barras = ?", (codigo_barras,)
    ).fetchone()
    conn.close()
    if row:
        p = dict(row)
        if p["propiedades"]:
            try:
                p["propiedades"] = json.loads(p["propiedades"])
            except json.JSONDecodeError:
                p["propiedades"] = {}
        else:
            p["propiedades"] = {}
        return p
    return None


def eliminar_producto(pid):
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


def exportar_productos(ids, formato="csv"):
    conn = get_db()
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT * FROM productos WHERE id IN ({placeholders}) ORDER BY updated_at DESC",
        ids
    ).fetchall()
    conn.close()

    productos = [dict(r) for r in rows]

    if formato == "json":
        return json.dumps(productos, ensure_ascii=False, indent=2, default=str)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["codigo_barras", "nombre", "marca", "descripcion",
                      "precio_referencia", "imagen_url", "sku", "fuente",
                      "cantidad", "propiedades", "ia_analizado", "created_at"])
    for p in productos:
        writer.writerow([
            p["codigo_barras"], p["nombre"], p["marca"], p["descripcion"],
            p["precio_referencia"], p["imagen_url"], p["sku"], p["fuente"],
            p["cantidad"], p["propiedades"], p["ia_analizado"], p["created_at"]
        ])
    return output.getvalue()
