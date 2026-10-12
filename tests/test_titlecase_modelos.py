"""Title Case en el modelo: el protocolo del catálogo se aplica solo.

`Producto` y `Categoria` ya normalizaban en producto_service, pero había caminos
que se salteaban el servicio (seeds, imports, scripts, endpoints nuevos). El
`@validates` vive en el modelo, así que cubre todo lo que escriba en esos campos.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.sector import Sector
from app.services import producto_service


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _producto(**kwargs):
    base = dict(codigo_barras="7790001111111", nombre="coca cola 375ml", precio_venta=1000.0)
    base.update(kwargs)
    return Producto(**base)


def test_nombre_normalizado_en_el_constructor(db):
    p = _producto(nombre="GASEOSA COCA COLA")
    db.add(p)
    db.commit()
    assert p.nombre == "Gaseosa Coca Cola"


def test_marca_y_descripcion_tambien(db):
    p = _producto(marca="HELLMANN'S", descripcion="  salsa   de tomate natural ")
    db.add(p)
    db.commit()
    assert p.marca == "Hellmann's"
    assert p.descripcion == "Salsa de Tomate Natural"


def test_marca_nula_pasa_sin_tocar(db):
    p = _producto(marca=None, descripcion=None)
    db.add(p)
    db.commit()
    assert p.marca is None
    assert p.descripcion is None


def test_set_posterior_tambien_normaliza(db):
    p = _producto()
    db.add(p)
    db.commit()
    p.nombre = "papas congeladas"
    p.marca = "MC CAIN"
    db.commit()
    assert p.nombre == "Papas Congeladas"
    assert p.marca == "Mc Cain"


def test_idempotente(db):
    p = _producto(nombre="Papas Congeladas Mc Cain 400gr")
    db.add(p)
    db.commit()
    primera = p.nombre
    p.nombre = primera
    db.commit()
    assert p.nombre == primera == "Papas Congeladas Mc Cain 400gr"


def test_no_toca_el_codigo_de_barras(db):
    p = _producto(codigo_barras="7791234567890")
    db.add(p)
    db.commit()
    assert p.codigo_barras == "7791234567890"


def test_categoria_normaliza(db):
    c = Categoria(nombre="GOLOSINAS")
    db.add(c)
    db.commit()
    assert c.nombre == "Golosinas"


def test_sector_normaliza(db):
    s = Sector(nombre="golosinas  piso  1", orden=1)
    db.add(s)
    db.commit()
    assert s.nombre == "Golosinas Piso 1"


def test_crear_producto_del_servicio(db):
    p = producto_service.crear_producto(
        db, {"nombre": "yerba mate", "marca": "PLAYADITO", "precio_venta": 3200.0}
    )
    assert p.nombre == "Yerba Mate"
    assert p.marca == "Playadito"


def test_actualizar_producto_del_servicio(db):
    p = producto_service.crear_producto(db, {"nombre": "arroz", "precio_venta": 1800.0})
    producto_service.actualizar_producto(db, p, {"nombre": "ARROZ GALLO ORO", "marca": "gallo"})
    assert p.nombre == "Arroz Gallo Oro"
    assert p.marca == "Gallo"


def test_categoria_unicas_solo_con_la_forma_canonica(db):
    db.add(Categoria(nombre="Golosinas"))
    db.commit()
    db.add(Categoria(nombre="GOLOSINAS"))
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()
