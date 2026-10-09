"""Tests de fechas para etiquetas de precios.

El rango `desde`–`hasta` llega como dates (medianoche). El servicio usaba
`between(desde, hasta)` contra columnas DateTime: en SQLite la comparación es
string, así que un producto cuyo precio cambió el mismo día "hasta" (casi
siempre "hoy", el caso de uso real) tenía `updated_at = '2026-10-09 15:00:00'`
> `'2026-10-09'` y quedaba excluido. Ahora el bound superior es el día
siguiente (exclusivo).
"""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.producto import Producto
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.schemas.etiquetas import EtiquetasFiltros
from app.services.etiquetas_service import obtener_productos_para_etiquetar


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _producto(db, codigo, *, created_at, updated_at, precio_venta=100.0, precio_etiqueta=None):
    producto = Producto(
        codigo_barras=codigo, nombre=f"Prod {codigo}",
        precio_venta=precio_venta, precio_etiqueta=precio_etiqueta,
        activo=True, created_at=created_at, updated_at=updated_at,
    )
    db.add(producto)
    db.commit()
    return producto


def _consultar(db, desde, hasta, **kw):
    filtros = EtiquetasFiltros(desde=desde, hasta=hasta, **kw)
    return obtener_productos_para_etiquetar(db, filtros)


class TestRangoFechas:
    def test_incluye_precio_cambiado_el_mismo_dia_hasta(self, db):
        """Un precio cambiado hoy a las 15:00 tiene que entrar con hasta=hoy."""
        _producto(db, "7790000000001",
                  created_at=datetime(2026, 1, 1, 10, 0),
                  updated_at=datetime(2026, 10, 9, 15, 30),
                  precio_etiqueta=90.0, precio_venta=100.0)
        result = _consultar(db, date(2026, 10, 9), date(2026, 10, 9))
        assert [p.codigo_barras for p in result] == ["7790000000001"]

    def test_incluye_producto_creado_el_dia_hasta(self, db):
        _producto(db, "7790000000002",
                  created_at=datetime(2026, 10, 9, 8, 15),
                  updated_at=datetime(2026, 10, 9, 8, 15))
        result = _consultar(db, date(2026, 10, 1), date(2026, 10, 9))
        assert [p.codigo_barras for p in result] == ["7790000000002"]

    def test_excluye_producto_anterior_al_desde(self, db):
        _producto(db, "7790000000003",
                  created_at=datetime(2026, 9, 1, 10, 0),
                  updated_at=datetime(2026, 9, 20, 10, 0),
                  precio_etiqueta=None)
        result = _consultar(db, date(2026, 10, 1), date(2026, 10, 9))
        assert result == []

    def test_excluye_precio_ya_impreso_sin_cambios(self, db):
        """precio_etiqueta == precio_venta: ya está etiquetado, no vuelve a salir."""
        _producto(db, "7790000000004",
                  created_at=datetime(2026, 1, 1, 10, 0),
                  updated_at=datetime(2026, 10, 9, 12, 0),
                  precio_etiqueta=100.0, precio_venta=100.0)
        result = _consultar(db, date(2026, 10, 9), date(2026, 10, 9))
        assert result == []

    def test_solo_nuevos_ignora_cambios_de_precio(self, db):
        _producto(db, "7790000000005",
                  created_at=datetime(2026, 1, 1, 10, 0),
                  updated_at=datetime(2026, 10, 9, 15, 0),
                  precio_etiqueta=90.0, precio_venta=100.0)
        result = _consultar(db, date(2026, 10, 9), date(2026, 10, 9),
                            incluir_cambios_precio=False, incluir_nuevos=True)
        assert result == []

    def test_excluye_inactivos_y_sin_precio(self, db):
        _producto(db, "7790000000006",
                  created_at=datetime(2026, 10, 9, 10, 0),
                  updated_at=datetime(2026, 10, 9, 10, 0))
        inactivo = _producto(db, "7790000000007",
                             created_at=datetime(2026, 10, 9, 10, 0),
                             updated_at=datetime(2026, 10, 9, 10, 0))
        inactivo.activo = False
        sin_precio = _producto(db, "7790000000008",
                               created_at=datetime(2026, 10, 9, 10, 0),
                               updated_at=datetime(2026, 10, 9, 10, 0))
        sin_precio.precio_venta = None
        db.commit()
        result = _consultar(db, date(2026, 10, 9), date(2026, 10, 9))
        assert [p.codigo_barras for p in result] == ["7790000000006"]
