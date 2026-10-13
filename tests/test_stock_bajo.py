"""Stock bajo: un solo criterio para todos los consumidores.

Antes había tres reglas distintas: el Dashboard contaba
`stock_minimo > 0`, el chip de Productos usaba `stock_minimo || 5` y
`/productos/stock-bajo` recalculaba por lotes. Acá queda una sola
definición (stock_service.filtro_bajo) y se testea que el KPI, la lista
de alertas y el endpoint digan lo mismo.
"""

import itertools

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.routers import dashboard as dash
from app.routers import productos as prod
from app.services import stock_service

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


def producto(db, nombre, stock, minimo, controla=True, activo=True):
    p = Producto(
        codigo_barras=f"7790000{next(_barras):06d}",
        nombre=nombre,
        stock_actual=stock,
        stock_minimo=minimo,
        controla_stock=controla,
        activo=activo,
    )
    db.add(p)
    db.commit()
    return p


class TestFiltroBajo:
    def test_entra_el_que_alcanzo_su_minimo(self, db):
        producto(db, "Gaseosa", stock=3, minimo=5)
        assert [p.nombre for p in stock_service.productos_stock_bajo(db)] == ["Gaseosa"]

    def test_en_el_limite_exacto_cuenta(self, db):
        producto(db, "Alfajor", stock=5, minimo=5)
        assert len(stock_service.productos_stock_bajo(db)) == 1

    def test_ultimo_punto_por_encima_no_entra(self, db):
        producto(db, "Alfajor", stock=5.1, minimo=5)
        assert stock_service.productos_stock_bajo(db) == []

    def test_minimo_en_cero_no_es_bajo(self, db):
        # "No definí mínimo" no es "está al límite": era lo que hacía el
        # chip de Productos con su 5 por defecto.
        producto(db, "Sin minimo", stock=0, minimo=0)
        assert stock_service.productos_stock_bajo(db) == []

    def test_no_controla_stock_queda_fuera(self, db):
        producto(db, "Fraccionado", stock=0, minimo=5, controla=False)
        assert stock_service.productos_stock_bajo(db) == []

    def test_inactivo_queda_fuera(self, db):
        producto(db, "Borrado", stock=0, minimo=5, activo=False)
        assert stock_service.productos_stock_bajo(db) == []


class TestFiltroAgotadoYRepo:
    def test_agotado_con_minimo_esta_en_los_dos(self, db):
        producto(db, "Agotado", stock=0, minimo=5)
        assert stock_service.filtro_agotado(db.query(Producto)).count() == 1
        assert stock_service.filtro_reposicion(db.query(Producto)).count() == 1

    def test_agotado_sin_minimo_solo_entra_en_reposicion(self, db):
        producto(db, "Sin minimo", stock=0, minimo=0)
        assert stock_service.filtro_bajo(db.query(Producto)).count() == 0
        assert stock_service.filtro_reposicion(db.query(Producto)).count() == 1

    def test_agotado_sin_control_de_stock_queda_fuera(self, db):
        producto(db, "Fraccionado", stock=0, minimo=0, controla=False)
        assert stock_service.filtro_agotado(db.query(Producto)).count() == 0


class TestEndpointsUsanElMismoCriterio:
    def test_stock_bajo_devuelve_bajo_y_agotados(self, db, user):
        bajo = producto(db, "Bajo", stock=2, minimo=5)
        sin_minimo = producto(db, "Sin minimo", stock=0, minimo=0)
        producto(db, "Sano", stock=20, minimo=5)

        resp = prod.productos_stock_bajo(db=db, user=user)
        assert resp.total == 2
        assert {p.nombre for p in resp.data} == {bajo.nombre, sin_minimo.nombre}

    def test_kpi_y_alertas_cuentan_lo_mismo(self, db, user):
        producto(db, "Bajo", stock=2, minimo=5)
        sin_minimo = producto(db, "Sin minimo", stock=0, minimo=0)
        producto(db, "Sano", stock=20, minimo=5)

        panel = dash.resumen(db=db, user=user).data
        assert panel["stock_bajo"] == 1
        assert [p["nombre"] for p in panel["sin_stock"]] == [sin_minimo.nombre]

        alertas = dash.alertas(db=db, user=user).data["alertas"]
        tipos = {a["tipo"]: a["mensaje"] for a in alertas}
        assert tipos["stock_bajo"] == "1 producto(s) bajo stock mínimo"
        assert tipos["sin_stock"] == "1 producto(s) agotados"
