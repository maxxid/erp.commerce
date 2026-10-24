"""Datos de demostración para una base recién creada.

Sólo se cargan con `SEED_DEMO=true` (apagado por defecto): un negocio real no
tiene que arrancar con cuatro productos falsos adentro. Eso ya le pasó a
producción: la base quedó vacía en un deploy temprano, el arranque sembró el
demo, después lo borraron — pero **un borrado retiene su código de barras**,
así que el `7790895000997` siguió bloqueado para siempre y ni siquiera se veía
en ninguna pantalla (ver Fase H: producto borrado no bloquea el código).
"""

from sqlalchemy.orm import Session

from app.config import settings

DEMO_PRODUCTOS = [
    {"codigo_barras": "7790895000997", "nombre": "Coca Cola 2.25L", "marca": "Coca Cola", "precio_venta": 2500, "precio_costo": 1800, "categoria_id": 2, "stock": 24},
    {"codigo_barras": "7791234567890", "nombre": "Yerba Mate Playadito 1kg", "marca": "Playadito", "precio_venta": 3200, "precio_costo": 2400, "categoria_id": 1, "stock": 12},
    {"codigo_barras": "7795555444333", "nombre": "Aceite de Girasol Natura 1.5L", "marca": "Natura", "precio_venta": 3800, "precio_costo": 2900, "categoria_id": 1, "stock": 8},
    {"codigo_barras": "7794001234567", "nombre": "Arroz Gallo Oro 1kg", "marca": "Gallo Oro", "precio_venta": 1800, "precio_costo": 1200, "categoria_id": 1, "stock": 30},
]


def sembrar_si_corresponde(db: Session) -> int:
    """Crea los datos de demo si `SEED_DEMO` está prendido y no hay productos.

    Devuelve cuántos productos creó (0 = nada que hacer).
    """
    if not settings.SEED_DEMO:
        return 0

    from app.models.producto import Producto

    if db.query(Producto).first():
        return 0

    from app.models.proveedor import Proveedor
    from app.models.compra import Compra, CompraItem
    from app.services.compra_service import generar_numero_compra

    for p in DEMO_PRODUCTOS:
        db.add(Producto(
            codigo_barras=p["codigo_barras"], nombre=p["nombre"], marca=p["marca"],
            precio_venta=p["precio_venta"], precio_costo=p["precio_costo"],
            categoria_id=p["categoria_id"], stock_actual=p["stock"],
            fuente="demo", sku=p["codigo_barras"][:8],
        ))
    db.commit()

    # Proveedor demo
    prov = Proveedor(nombre="Distribuidora Demo SA", cuit="30-99999999-9", telefono="1144445555")
    db.add(prov)
    db.flush()

    # Compra demo (para que los costos tengan fuente)
    compra = Compra(
        numero=generar_numero_compra(db), proveedor_id=prov.id,
        usuario_id=1, sucursal_id=1, estado="recibida",
        subtotal=0, total=0,
    )
    db.add(compra)
    db.flush()
    for prod in db.query(Producto).all():
        total = prod.precio_costo * prod.stock_actual
        db.add(CompraItem(compra_id=compra.id, producto_id=prod.id, cantidad=prod.stock_actual,
                          precio_unitario=prod.precio_costo, subtotal=total))
        compra.subtotal += total
    compra.total = compra.subtotal
    db.commit()

    # Marcar demo como etiquetados
    for prod in db.query(Producto).all():
        prod.precio_etiqueta = prod.precio_venta
    db.commit()

    return len(DEMO_PRODUCTOS)
