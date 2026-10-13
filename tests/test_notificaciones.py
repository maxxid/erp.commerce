"""Notificaciones de la campana: generación, dedup y lectura.

El aviso se calcula del estado real del sistema y se guarda una vez por
clave (tipo + fecha). Dos modos se eligen en Ajustes: la lectura puede ser
por usuario o global, y el stock bajo puede llegar agregado o uno por
producto.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.compra import Compra, CompraItem
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.routers import notificaciones as router
from app.services import config_service, notificaciones_service, stock_service

import itertools

_barras = itertools.count(1)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    u = Usuario(username="admin", password_hash="x", nombre="Admin", rol="admin")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def user2(db):
    u = Usuario(username="cajero", password_hash="x", nombre="Cajero", rol="cajero")
    db.add(u)
    db.commit()
    return u


def producto(db, nombre, stock, minimo, costo=None, venta=None):
    p = Producto(
        codigo_barras=f"7790000{next(_barras):06d}",
        nombre=nombre,
        stock_actual=stock,
        stock_minimo=minimo,
        precio_costo=costo,
        precio_venta=venta,
    )
    db.add(p)
    db.commit()
    return p


def compra_de(db, p, proveedor, precio):
    prov = Proveedor(nombre=proveedor, cuit="30-00000000-0")
    db.add(prov)
    db.commit()
    compra = Compra(numero=f"C{next(_barras):06d}", proveedor_id=prov.id, usuario_id=1)
    db.add(compra)
    db.commit()
    db.add(CompraItem(compra_id=compra.id, producto_id=p.id, cantidad=10,
                      cantidad_recibida=10, precio_unitario=precio, subtotal=precio * 10))
    db.commit()
    return prov


def aviso_de(avisos, tipo):
    return next(a for a in avisos if a["tipo"] == tipo)


class TestGeneracion:
    def test_stock_bajo_lleva_proveedor_y_precios(self, db, user):
        p = producto(db, "Gaseosa", stock=2, minimo=8, venta=2500)
        compra_de(db, p, "Carrefour", 1500)

        assert notificaciones_service.generar(db) == 1
        aviso = aviso_de(notificaciones_service.listar(db, user)["avisos"], "stock_bajo")
        assert aviso["mensaje"] == "1 producto(s) bajo stock mínimo"
        fila = aviso["data"]["productos"][0]
        assert fila["proveedor"] == "Carrefour"
        assert notificaciones_service.mensaje_bajo(fila) == \
            "Stock 2 / mínimo 8 — Proveedor: Carrefour — compra $1,500.00 — venta $2,500.00"

    def test_sin_compra_usa_el_costo_del_producto(self, db, user):
        producto(db, "Alfajor", stock=0, minimo=3, costo=800, venta=1200)

        notificaciones_service.generar(db)
        fila = aviso_de(notificaciones_service.listar(db, user)["avisos"], "stock_bajo")["data"]["productos"][0]
        assert fila["proveedor"] is None
        assert fila["precio_compra"] == 800
        assert notificaciones_service.mensaje_bajo(fila) == \
            "Stock 0 / mínimo 3 — compra $800.00 — venta $1,200.00"

    def test_dos_veces_no_duplica(self, db, user):
        producto(db, "Gaseosa", stock=2, minimo=8)
        assert notificaciones_service.generar(db) == 1
        assert notificaciones_service.generar(db) == 0

    def test_granularidad_por_producto(self, db, user):
        config_service.set_config(db, "avisos_granularidad", "producto")
        producto(db, "Gaseosa", stock=2, minimo=8)
        producto(db, "Alfajor", stock=1, minimo=4)

        assert notificaciones_service.generar(db) == 2
        avisos = notificaciones_service.listar(db, user)["avisos"]
        assert {a["titulo"] for a in avisos} == {"Gaseosa", "Alfajor"}

    def test_producto_sano_no_genera_aviso(self, db, user):
        producto(db, "Sano", stock=50, minimo=8)
        assert notificaciones_service.generar(db) == 0


class TestLectura:
    def test_modo_usuario_no_le_borra_el_aviso_al_otro(self, db, user, user2):
        producto(db, "Gaseosa", stock=2, minimo=8)
        notificaciones_service.generar(db)

        data = notificaciones_service.listar(db, user)
        assert data["no_leidas"] == 1
        notificaciones_service.marcar_leida(db, data["avisos"][0]["id"], user)

        assert notificaciones_service.listar(db, user)["no_leidas"] == 0
        assert notificaciones_service.listar(db, user2)["no_leidas"] == 1

    def test_modo_global_le_sirve_a_todos(self, db, user, user2):
        config_service.set_config(db, "avisos_lectura", "global")
        producto(db, "Gaseosa", stock=2, minimo=8)
        notificaciones_service.generar(db)

        notificaciones_service.marcar_todas(db, user)
        assert notificaciones_service.listar(db, user2)["no_leidas"] == 0

    def test_marcar_todas(self, db, user):
        producto(db, "Gaseosa", stock=2, minimo=8)
        producto(db, "Alfajor", stock=0, minimo=4)
        notificaciones_service.generar(db)
        total = len(notificaciones_service.listar(db, user)["avisos"])

        marcadas = notificaciones_service.marcar_todas(db, user)
        assert marcadas == total
        assert notificaciones_service.listar(db, user)["no_leidas"] == 0


class TestRutas:
    def test_listar_genera_y_devuelve(self, db, user):
        producto(db, "Gaseosa", stock=2, minimo=8)
        resp = router.listar_notificaciones(db=db, user=user)
        assert resp.data["no_leidas"] == 1
        assert resp.data["modo_lectura"] == "usuario"

    def test_marcar_leida_desconocida_da_404(self, db, user):
        with pytest.raises(Exception) as ei:
            router.marcar_leida(9999, db=db, user=user)
        assert ei.value.status_code == 404

    def test_las_rutas_estan_registradas(self):
        rutas = {r.path for r in router.router.routes}
        assert "/api/notificaciones" in rutas
        assert "/api/notificaciones/leer-todas" in rutas
        assert "/api/notificaciones/{notificacion_id}/leer" in rutas
