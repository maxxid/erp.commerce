"""Tests del analisis de precios: historial de compras y costos por proveedor.

Lo critico aca es que las compras anuladas NO podem contar como historial, ni
como "el precio mas bajo que conseguiste".
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.producto import Producto, producto_proveedor
from app.models.proveedor import Proveedor
from app.models.compra import Compra, CompraItem
from app.models.usuario import Usuario
from app.services import analisis_precios_service as ap


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def producto(db):
    p = Producto(codigo_barras="7790001234567", nombre="Café Molido 1kg", marca="Nescafé",
                 precio_venta=30000.0, fuente="manual", stock_actual=0)
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _compra(db, producto, proveedor, precio, dias_atras=0, estado="recibida", cantidad=10.0):
    usuario = db.query(Usuario).first()
    if usuario is None:
        usuario = Usuario(username="test", password_hash="x", nombre="Test", rol="admin")
        db.add(usuario)
        db.commit()
    c = Compra(
        numero=f"C-{estado}-{dias_atras}-{precio}",
        proveedor_id=proveedor.id,
        usuario_id=usuario.id,
        sucursal_id=1,
        fecha=datetime(2026, 1, 1) - timedelta(days=dias_atras),
        subtotal=precio * cantidad,
        total=precio * cantidad,
        estado=estado,
    )
    db.add(c)
    db.commit()
    item = CompraItem(compra_id=c.id, producto_id=producto.id, cantidad=cantidad,
                      cantidad_recibida=cantidad, precio_unitario=precio,
                      subtotal=precio * cantidad)
    db.add(item)
    db.commit()
    return c


@pytest.fixture
def proveedores(db):
    a = Proveedor(nombre="Distribuidora Norte")
    b = Proveedor(nombre="Mayorista Sur")
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    db.refresh(b)
    return a, b


def _vincular(db, producto, proveedor, costo, principal=False, plazo=None, activo=1):
    db.execute(
        producto_proveedor.insert().values(
            producto_id=producto.id, proveedor_id=proveedor.id,
            costo=costo, es_principal=1 if principal else 0,
            plazo_entrega_dias=plazo, activo=activo,
        )
    )
    db.commit()


class TestHistorial:
    def test_sin_compras_devuelve_lista_vacia(self, db, producto):
        r = ap.analizar_precios(db, producto)
        assert r["historial"] == []
        assert r["ultimo_costo"] is None
        assert r["mejor_historico"] is None
        assert r["tiene_historico"] is False

    def test_ordena_de_mas_reciente_a_mas_antigua(self, db, producto, proveedores):
        norte, sur = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30)
        _compra(db, producto, sur, 2000.0, dias_atras=10)
        _compra(db, producto, norte, 3000.0, dias_atras=60)

        h = ap.analizar_precios(db, producto)["historial"]
        assert [x["precio_unitario"] for x in h] == [2000.0, 1000.0, 3000.0]

    def test_excluye_compras_anuladas(self, db, producto, proveedores):
        norte, sur = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30, estado="recibida")
        _compra(db, producto, sur, 50.0, dias_atras=5, estado="anulada")

        r = ap.analizar_precios(db, producto)
        assert len(r["historial"]) == 1
        assert r["historial"][0]["precio_unitario"] == 1000.0

    def test_una_anulada_no_puede_ser_el_mejor_precio(self, db, producto, proveedores):
        norte, sur = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30, estado="recibida")
        _compra(db, producto, sur, 50.0, dias_atras=5, estado="anulada")

        r = ap.analizar_precios(db, producto)
        assert r["mejor_historico"]["precio_unitario"] == 1000.0
        assert r["mejor_historico"]["proveedor_nombre"] == "Distribuidora Norte"

    def test_excluye_compras_pendientes(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30, estado="recibida")
        _compra(db, producto, norte, 10.0, dias_atras=1, estado="pendiente")
        assert len(ap.analizar_precios(db, producto)["historial"]) == 1

    def test_incluye_parciales(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=2, estado="parcial")
        assert len(ap.analizar_precios(db, producto)["historial"]) == 1

    def test_ultimo_costo_es_el_mas_reciente(self, db, producto, proveedores):
        norte, sur = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30)
        _compra(db, producto, sur, 2500.0, dias_atras=3)

        r = ap.analizar_precios(db, producto)
        assert r["ultimo_costo"]["precio_unitario"] == 2500.0
        assert r["ultimo_costo"]["proveedor_nombre"] == "Mayorista Sur"

    def test_mejor_historico_guarda_proveedor_y_fecha(self, db, producto, proveedores):
        norte, sur = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=30)
        _compra(db, producto, sur, 700.0, dias_atras=20)

        mejor = ap.analizar_precios(db, producto)["mejor_historico"]
        assert mejor["precio_unitario"] == 700.0
        assert mejor["proveedor_nombre"] == "Mayorista Sur"
        assert mejor["fecha"].startswith("2025-12-12")


class TestProveedores:
    def test_lista_costos_con_ultimo_pagado(self, db, producto, proveedores):
        norte, sur = proveedores
        _vincular(db, producto, norte, 1100.0, principal=True, plazo=3)
        _vincular(db, producto, sur, 950.0, plazo=7)
        _compra(db, producto, norte, 1200.0, dias_atras=15)

        r = ap.analizar_precios(db, producto)
        por_id = {p["proveedor_id"]: p for p in r["proveedores"]}

        assert por_id[norte.id]["costo_actual"] == 1100.0
        assert por_id[norte.id]["es_principal"] is True
        assert por_id[norte.id]["plazo_entrega_dias"] == 3
        assert por_id[norte.id]["ultimo_precio_pagado"] == 1200.0
        assert por_id[norte.id]["ultima_fecha_pago"] is not None

        assert por_id[sur.id]["costo_actual"] == 950.0
        assert por_id[sur.id]["ultimo_precio_pagado"] is None

    def test_principal_primero(self, db, producto, proveedores):
        norte, sur = proveedores
        _vincular(db, producto, norte, 1100.0)
        _vincular(db, producto, sur, 950.0, principal=True)
        assert ap.analizar_precios(db, producto)["proveedores"][0]["nombre"] == "Mayorista Sur"

    def test_excluye_vinculos_inactivos(self, db, producto, proveedores):
        norte, sur = proveedores
        _vincular(db, producto, norte, 1100.0)
        _vincular(db, producto, sur, 950.0, activo=0)
        r = ap.analizar_precios(db, producto)
        assert len(r["proveedores"]) == 1
        assert r["proveedores"][0]["proveedor_id"] == norte.id

    def test_mejor_oferta_es_el_costo_mas_bajo(self, db, producto, proveedores):
        norte, sur = proveedores
        _vincular(db, producto, norte, 1100.0)
        _vincular(db, producto, sur, 950.0)
        assert ap.analizar_precios(db, producto)["mejor_oferta_proveedor"] == 950.0

    def test_sin_costos_devuelve_none(self, db, producto, proveedores):
        norte, _ = proveedores
        _vincular(db, producto, norte, None)
        assert ap.analizar_precios(db, producto)["mejor_oferta_proveedor"] is None

    def test_ultimo_pagado_ignora_anuladas(self, db, producto, proveedores):
        norte, sur = proveedores
        _vincular(db, producto, norte, 1100.0)
        _vincular(db, producto, sur, 950.0)
        _compra(db, producto, sur, 10.0, dias_atras=2, estado="anulada")

        por_id = {p["proveedor_id"]: p for p in ap.analizar_precios(db, producto)["proveedores"]}
        assert por_id[sur.id]["ultimo_precio_pagado"] is None


ONLINE = [
    {"fuente": "vea", "precio": 1500.0, "nombre": "Café", "marca": "Nescafé", "imagen_url": "", "url": "u"},
    {"fuente": "carrefour", "precio": 1200.0, "nombre": "Café", "marca": "Nescafé", "imagen_url": "", "url": "u"},
]


class TestAnalisis:
    def test_elige_el_online_mas_barato(self, db, producto):
        r = ap.analizar_precios(db, producto, ONLINE)
        assert r["online"]["fuente"] == "carrefour"
        assert r["online"]["precio"] == 1200.0

    def test_ignora_online_sin_precio(self, db, producto):
        r = ap.analizar_precios(db, producto, [{"fuente": "vea", "precio": None}])
        assert r["online"] is None

    def test_sin_online_no_calcula_ahorro(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 1000.0, dias_atras=5)
        r = ap.analizar_precios(db, producto)
        assert r["ahorro_vs_ultimo_costo"] is None
        assert r["ahorro_vs_mejor_historico"] is None

    def test_ahorro_positivo_cuando_online_es_mas_barato(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 2000.0, dias_atras=5)
        a = ap.analizar_precios(db, producto, ONLINE)["ahorro_vs_ultimo_costo"]
        assert a["conviene_online"] is True
        assert a["diferencia"] == 800.0
        assert a["porcentaje"] == 40.0

    def test_ahorro_negativo_cuando_online_es_mas_caro(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 900.0, dias_atras=5)
        a = ap.analizar_precios(db, producto, ONLINE)["ahorro_vs_ultimo_costo"]
        assert a["conviene_online"] is False
        assert a["diferencia"] == -300.0

    def test_ahorro_ignora_precios_iguales(self, db, producto, proveedores):
        norte, _ = proveedores
        _compra(db, producto, norte, 1200.0, dias_atras=5)
        assert ap.analizar_precios(db, producto, ONLINE)["ahorro_vs_ultimo_costo"] is None

    def test_margen_actual(self, db, producto):
        m = ap.analizar_precios(db, producto, ONLINE)["margen_actual"]
        assert m["precio_costo"] == 1200.0
        assert m["precio_venta"] == 30000.0
        assert m["utilidad"] == 28800.0
        assert m["positivo"] is True

    def test_margen_negativo_si_el_producto_no_iguala(self, db, producto):
        producto.precio_venta = 1000.0
        db.commit()
        m = ap.analisis_margen = ap.analizar_precios(db, producto, ONLINE)["margen_actual"]
        assert m["positivo"] is False

    def test_margen_none_sin_precio_venta(self, db, producto):
        producto.precio_venta = None
        db.commit()
        assert ap.analizar_precios(db, producto, ONLINE)["margen_actual"] is None

    def test_margen_none_sin_online(self, db, producto):
        assert ap.analizar_precios(db, producto)["margen_actual"] is None

    def test_incluye_datos_del_producto(self, db, producto):
        r = ap.analizar_precios(db, producto)["producto"]
        assert r["codigo_barras"] == "7790001234567"
        assert r["nombre"] == "Café Molido 1kg"
        assert r["precio_venta"] == 30000.0
