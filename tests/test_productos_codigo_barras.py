"""Tests del codigo de barras de un producto.

`productos.codigo_barras` es NOT NULL y UNIQUE. El modal de edicion de
Productos regeneraba el codigo de los productos cargados a mano (`*MANUAL*` /
`GEN-`) como `GEN-XXXX`, usando como secuencia la cantidad de productos manuales
que se veian en la tabla (que ya venia filtrada y paginada). Ese codigo generado
chocaba con el de otro producto y el guardado terminaba en un
"Internal Server Error" sin explicar nada: el usuario no podia, por ejemplo,
convertir un producto a "sin control de stock".

Ahora el modal no toca el codigo de un producto existente, el backend asigna uno
interno (MAN-) si el campo llega vacio, y una colision de codigo se responde con
un 409 legible en lugar de un 500.
"""

import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario
from app.models.categoria import Categoria
from app.models.producto import Producto
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.routers import productos as productos_router
from app.schemas.producto import ProductoCreate, ProductoUpdate


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        sufijo = uuid.uuid4().hex[:8]
        session.add(Usuario(
            username=f"prod_{sufijo}", nombre="Vendedor", password_hash="x",
            rol="admin", activo=True,
        ))
        session.add(Categoria(nombre="Bebidas"))
        session.commit()
        yield session
    finally:
        session.close()


def _crear(db, codigo, nombre="Producto", **extra):
    categoria_id = db.query(Categoria).first().id
    producto = Producto(
        codigo_barras=codigo, nombre=nombre, categoria_id=categoria_id,
        precio_venta=100.0, controla_stock=True, **extra,
    )
    db.add(producto)
    db.commit()
    return producto


def _editar(db, producto_id, **campos):
    return productos_router.actualizar(
        producto_id, ProductoUpdate(**campos), db, db.query(Usuario).first(),
    )


class TestCodigoBarras:
    def test_crear_sin_codigo_asigna_uno_interno(self, db):
        creado = productos_router.crear(
            ProductoCreate(nombre="Mignon", precio_venta=150.0),
            db, db.query(Usuario).first(),
        )
        assert creado.data.codigo_barras.startswith("MAN-")

    def test_convertir_a_sin_control_de_stock_conserva_el_codigo(self, db):
        """El caso que reporto el usuario: cambiar el control de stock."""
        mignon = _crear(db, "*MANUAL*7791111000011", nombre="Mignon")

        resp = _editar(db, mignon.id, nombre="Mignon", controla_stock=False)

        assert resp.data.controla_stock is False
        assert resp.data.codigo_barras == "*MANUAL*7791111000011"

    def test_codigo_duplicado_responde_409_y_no_500(self, db):
        mignon = _crear(db, "*MANUAL*7791111000011", nombre="Mignon")
        otro = _crear(db, "7791111000099", nombre="Medialunas")

        with pytest.raises(HTTPException) as exc:
            _editar(db, mignon.id, codigo_barras=otro.codigo_barras)

        assert exc.value.status_code == 409
        assert "7791111000099" in exc.value.detail
        # La sesion queda sana: el producto no quedo a medio guardar.
        assert db.get(Producto, mignon.id).codigo_barras == "*MANUAL*7791111000011"

    def test_codigo_vacio_asigna_uno_interno_en_vez_de_guardar_blanco(self, db):
        """La columna es NOT NULL y UNIQUE: dos productos en blanco la rompen."""
        mignon = _crear(db, "*MANUAL*7791111000011", nombre="Mignon")

        resp = _editar(db, mignon.id, codigo_barras="   ")

        assert resp.data.codigo_barras.startswith("MAN-")
        assert resp.data.codigo_barras != ""

    def test_se_pueden_crear_dos_productos_sin_codigo(self, db):
        primero = productos_router.crear(
            ProductoCreate(nombre="Mignon", precio_venta=150.0), db, db.query(Usuario).first(),
        )
        segundo = productos_router.crear(
            ProductoCreate(nombre="Medialunas", precio_venta=200.0), db, db.query(Usuario).first(),
        )
        assert primero.data.codigo_barras != segundo.data.codigo_barras
