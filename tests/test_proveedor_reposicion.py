"""Reposición por proveedor: agrupación, último precio y auto-vínculo.

Lo que importa acá:
- Un producto comprado a dos proveedores aparece en los dos grupos.
- Se incluye lo comprado aunque no haya vínculo manual, pero las compras
  anuladas no cuentan.
- Recibir una compra no pisa el costo de lista ni duplica el vínculo.
"""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base
from app.models.compra import Compra, CompraItem
from app.models.producto import Producto, producto_proveedor
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.services import compra_service
from app.services import proveedor_stock_service as rs
from app.services import proveedor_stock_pdf


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
def usuario(db):
    u = Usuario(username="test", password_hash="x", nombre="Test", rol="admin")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def proveedores(db):
    a = Proveedor(nombre="Distribuidora Norte")
    b = Proveedor(nombre="Mayorista Sur")
    db.add_all([a, b])
    db.commit()
    db.refresh(a)
    db.refresh(b)
    return a, b


def _producto(db, nombre="Gaseosa", stock=0, minimo=5, controla=True):
    p = Producto(
        codigo_barras=f"779000{nombre[-3:]}",
        nombre=nombre,
        stock_actual=stock,
        stock_minimo=minimo,
        controla_stock=controla,
        activo=True,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _vincular(db, producto, proveedor, costo=None, principal=0, activo=1):
    db.execute(producto_proveedor.insert().values(
        producto_id=producto.id,
        proveedor_id=proveedor.id,
        costo=costo,
        es_principal=principal,
        activo=activo,
    ))
    db.commit()


def _compra(db, producto, proveedor, precio, dias_atras=0, estado="recibida", cantidad=10.0):
    c = Compra(
        numero=f"C-{estado}-{dias_atras}-{precio}",
        proveedor_id=proveedor.id,
        usuario_id=db.query(Usuario).first().id,
        sucursal_id=1,
        fecha=datetime(2026, 1, 1) - timedelta(days=dias_atras),
        subtotal=precio * cantidad,
        total=precio * cantidad,
        estado=estado,
    )
    db.add(c)
    db.commit()
    db.add(CompraItem(
        compra_id=c.id, producto_id=producto.id, cantidad=cantidad,
        cantidad_recibida=cantidad, precio_unitario=precio,
        subtotal=precio * cantidad,
    ))
    db.commit()
    return c


def _grupo(grupos, proveedor):
    return next(g for g in grupos if g["id"] == proveedor.id)


def test_producto_comprado_a_dos_proveedores_aparece_en_ambos(db, usuario, proveedores):
    a, b = proveedores
    p = _producto(db)
    _vincular(db, p, a, costo=100.0)
    _compra(db, p, b, precio=120.0)

    grupos = rs.grupos_reposicion(db)

    assert len(grupos) == 2
    fila_a = _grupo(grupos, a)["productos"][0]
    fila_b = _grupo(grupos, b)["productos"][0]
    assert fila_a["producto_id"] == p.id
    assert fila_b["producto_id"] == p.id
    assert fila_a["ultimo_precio_pagado"] is None
    assert fila_b["ultimo_precio_pagado"] == 120.0


def test_ultimo_precio_es_el_mas_reciente(db, usuario, proveedores):
    a, _ = proveedores
    p = _producto(db)
    _compra(db, p, a, precio=100.0, dias_atras=5)
    _compra(db, p, a, precio=80.0, dias_atras=1)

    fila = _grupo(rs.grupos_reposicion(db), a)["productos"][0]

    assert fila["ultimo_precio_pagado"] == 80.0
    assert fila["ultima_fecha_pago"].startswith("2025-12-31")


def test_compra_anulada_no_cuenta_ni_vincula(db, usuario, proveedores):
    a, _ = proveedores
    p = _producto(db)
    _compra(db, p, a, precio=99.0, estado="anulada")

    grupos = rs.grupos_reposicion(db)

    assert len(grupos) == 1
    assert grupos[0]["id"] is None
    assert grupos[0]["nombre"] == "Sin proveedor"


def test_producto_sin_proveedor_va_al_grupo_sin_proveedor(db):
    _producto(db)

    grupos = rs.grupos_reposicion(db)

    assert [g["id"] for g in grupos] == [None]
    assert len(grupos[0]["productos"]) == 1


def test_faltante_usa_el_minimo(db):
    p = _producto(db, nombre="Alfajor", stock=2, minimo=10)

    assert rs._faltante(p.stock_actual, p.stock_minimo) == 8.0


def test_faltante_minimo_uno_si_esta_en_cero_sin_minimo(db):
    assert rs._faltante(0, 0) == 1


def test_faltante_con_stock_negativo_cubre_el_deficit(db):
    assert rs._faltante(-2, 0) == 2.0


def test_producto_que_no_controla_stock_queda_fuera(db):
    _producto(db, nombre="Servicio", stock=0, minimo=0, controla=False)
    assert rs.grupos_reposicion(db) == []


def test_asegurar_vinculo_crea_uno_solo_y_no_pisa_costo(db, usuario, proveedores):
    a, b = proveedores
    p = _producto(db)
    _vincular(db, p, a, costo=100.0)

    compra_service._asegurar_vinculo_proveedor(db, p.id, b.id)
    compra_service._asegurar_vinculo_proveedor(db, p.id, b.id)
    db.commit()

    filas = db.execute(
        select(producto_proveedor).where(producto_proveedor.c.producto_id == p.id)
    ).all()
    assert len(filas) == 2
    fila_b = next(f for f in filas if f.proveedor_id == b.id)
    assert fila_b.costo is None
    assert fila_b.es_principal == 0

    fila_a = next(f for f in filas if f.proveedor_id == a.id)
    assert fila_a.costo == 100.0


def test_auto_vinculo_marca_principal_si_es_el_primero(db, usuario, proveedores):
    a, _ = proveedores
    p = _producto(db)

    compra_service._asegurar_vinculo_proveedor(db, p.id, a.id)
    db.commit()

    fila = db.execute(
        select(producto_proveedor).where(producto_proveedor.c.producto_id == p.id)
    ).first()
    assert fila.es_principal == 1


def test_endpoint_proveedores_incluye_ultimo_pago(db, usuario, proveedores):
    from app.routers import productos as prod

    a, _ = proveedores
    p = _producto(db)
    _vincular(db, p, a)
    _compra(db, p, a, precio=123.0)

    data = prod.listar_proveedores_producto(p.id, db=db, user=usuario).data

    assert data[0]["ultimo_precio_pagado"] == 123.0
    assert data[0]["ultima_compra_numero"].startswith("C-")


@pytest.mark.skipif(not proveedor_stock_pdf.REPORTLAB_DISPONIBLE, reason="sin reportlab")
def test_pdf_se_genera(db, usuario, proveedores):
    a, _ = proveedores
    p = _producto(db)
    _vincular(db, p, a, costo=100.0)
    _compra(db, p, a, precio=120.0)
    grupos = rs.grupos_reposicion(db)

    assert proveedor_stock_pdf.generar_stock_proveedores_pdf(grupos).startswith(b"%PDF")
    assert proveedor_stock_pdf.generar_stock_proveedor_pdf(grupos[0]).startswith(b"%PDF")
