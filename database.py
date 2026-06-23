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
            precio_venta REAL,
            imagen_url TEXT,
            sku TEXT,
            propiedades TEXT,
            fuente TEXT,
            categoria TEXT DEFAULT '',
            cantidad REAL DEFAULT 0,
            ia_analizado INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    for col, typ in [("cantidad", "REAL DEFAULT 0"), ("precio_venta", "REAL"),
                     ("categoria", "TEXT DEFAULT ''")]:
        try:
            conn.execute(f"ALTER TABLE productos ADD COLUMN {col} {typ}")
        except sqlite3.OperationalError:
            pass

    conn.execute("""
        CREATE TABLE IF NOT EXISTS config (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    """)
    if not conn.execute("SELECT 1 FROM config WHERE key='margen'").fetchone():
        conn.execute("INSERT INTO config (key, value) VALUES ('margen', '30')")
    if not conn.execute("SELECT 1 FROM config WHERE key='redondeo'").fetchone():
        conn.execute("INSERT INTO config (key, value) VALUES ('redondeo', '50')")
    conn.commit()
    conn.close()


def get_config():
    conn = get_db()
    rows = conn.execute("SELECT key, value FROM config").fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def set_config(config_dict):
    conn = get_db()
    for key, value in config_dict.items():
        conn.execute(
            "INSERT INTO config (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value)))
    conn.commit()
    conn.close()


def guardar_producto(data):
    conn = get_db()
    propiedades_json = json.dumps(data.get("propiedades", {}), ensure_ascii=False)
    cursor = conn.execute("""
        INSERT INTO productos (codigo_barras, nombre, marca, descripcion,
            precio_referencia, precio_venta, imagen_url, sku, propiedades, fuente, categoria, cantidad)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(codigo_barras) DO UPDATE SET
            nombre=excluded.nombre,
            marca=excluded.marca,
            descripcion=excluded.descripcion,
            precio_referencia=excluded.precio_referencia,
            precio_venta=excluded.precio_venta,
            imagen_url=excluded.imagen_url,
            sku=excluded.sku,
            propiedades=excluded.propiedades,
            fuente=excluded.fuente,
            categoria=excluded.categoria,
            cantidad=excluded.cantidad,
            updated_at=CURRENT_TIMESTAMP
    """, (
        data["codigo_barras"],
        data["nombre"],
        data.get("marca"),
        data.get("descripcion"),
        data.get("precio_referencia"),
        data.get("precio_venta"),
        data.get("imagen_url"),
        data.get("sku"),
        propiedades_json,
        data.get("fuente"),
        data.get("categoria", ""),
        data.get("cantidad", 0),
    ))
    conn.commit()
    pid = cursor.lastrowid
    conn.close()
    return pid


def actualizar_producto(pid, data):
    conn = get_db()
    campos = []
    valores = []
    mapa = {
        "nombre": "nombre", "marca": "marca", "descripcion": "descripcion",
        "precio_referencia": "precio_referencia", "precio_venta": "precio_venta",
        "imagen_url": "imagen_url", "sku": "sku", "fuente": "fuente",
        "categoria": "categoria", "cantidad": "cantidad",
    }
    for key, col in mapa.items():
        if key in data:
            campos.append(f"{col}=?")
            valores.append(data[key])
    if "propiedades" in data:
        campos.append("propiedades=?")
        valores.append(json.dumps(data["propiedades"], ensure_ascii=False))
    if not campos:
        conn.close()
        return
    campos.append("updated_at=CURRENT_TIMESTAMP")
    valores.append(pid)
    conn.execute(f"UPDATE productos SET {', '.join(campos)} WHERE id=?", valores)
    conn.commit()
    conn.close()


def obtener_productos(search=None, categoria=None):
    conn = get_db()
    where = []
    params = []
    if search:
        where.append("(nombre LIKE ? OR codigo_barras LIKE ? OR marca LIKE ?)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
    if categoria:
        where.append("categoria = ?")
        params.append(categoria)
    query = "SELECT * FROM productos"
    if where:
        query += " WHERE " + " AND ".join(where)
    query += " ORDER BY updated_at DESC"
    rows = conn.execute(query, params).fetchall()
    conn.close()
    return _rows_to_dicts(rows)


def _rows_to_dicts(rows):
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
        items = _rows_to_dicts([row])
        return items[0] if items else None
    return None


def eliminar_producto(pid):
    conn = get_db()
    conn.execute("DELETE FROM productos WHERE id = ?", (pid,))
    conn.commit()
    conn.close()


def get_dashboard():
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) as c FROM productos").fetchone()["c"]
    valor = conn.execute(
        "SELECT COALESCE(SUM(precio_venta * cantidad), 0) as v FROM productos WHERE precio_venta IS NOT NULL AND cantidad > 0"
    ).fetchone()["v"]
    ultimo = conn.execute(
        "SELECT nombre, codigo_barras, updated_at FROM productos ORDER BY updated_at DESC LIMIT 1"
    ).fetchone()
    categorias = conn.execute(
        "SELECT categoria, COUNT(*) as c FROM productos WHERE categoria != '' GROUP BY categoria ORDER BY c DESC"
    ).fetchall()
    conn.close()
    return {
        "total_productos": total,
        "valor_stock": valor,
        "ultimo": dict(ultimo) if ultimo else None,
        "categorias": [dict(r) for r in categorias],
    }


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
                      "precio_referencia", "precio_venta", "imagen_url", "sku", "fuente",
                      "categoria", "cantidad", "propiedades", "ia_analizado", "created_at"])
    for p in productos:
        writer.writerow([
            p["codigo_barras"], p["nombre"], p["marca"], p["descripcion"],
            p["precio_referencia"], p["precio_venta"], p["imagen_url"], p["sku"], p["fuente"],
            p["categoria"], p["cantidad"], p["propiedades"], p["ia_analizado"], p["created_at"]
        ])
    return output.getvalue()
