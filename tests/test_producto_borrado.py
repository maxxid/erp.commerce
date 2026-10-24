"""Un producto borrado no puede retener el código de barras (Fase H, 24/10/2026).

**El bug que reportó el dueño**: quería cargar el `7790895000997` y

- no lo encontraba en el buscador de productos
- tampoco en el POS
- al crearlo le respondía "ya existe"
- el lookup le completaba el formulario con "origen: demo" sin que ese producto
  apareciera en ninguna lista

Causa: al arrancar con la base vacía se sembraron 4 productos de demo con
`fuente="demo"` (uno era el `7790895000997`, "Coca Cola 2.25L"). Al "eliminar"
un producto sólo se pone `activo = false`: la fila sigue ahí **con su código de
barras, que es UNIQUE**. El listado, el catálogo del POS y `/api/productos` no
lo muestran, pero `obtener_por_barcode` sí lo devolvía — producto invisible que
bloqueaba el alta y confundía el lookup.

Acá se cubre que:
- el alta **pase** cuando el código lo tiene un borrado (que pierde el código
  y conserva su historial: no se pierde ninguna compra, lote ni venta)
- el alta siga frenando si el código lo tiene un producto **activo**, y que el
  mensaje diga cuál es el producto
- el lookup saltee los borrados (se acabó el "origen: demo")
- la lista se pueda abrir con los borrados (es lo que sostiene el switch de la
  grilla de Productos)
- los datos de demo no se carguen solos en una base nueva (`SEED_DEMO`)
"""

import os

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.usuario import Usuario, Sucursal
from app.routers import productos as productos_router
from app.schemas.producto import ProductoCreate, ProductoLookupRequest
from app.services import demo_service, producto_service

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COMPRAS_SRC = os.path.join(RAIZ, "app", "routers", "compras.py")
MAIN_SRC = os.path.join(RAIZ, "app", "main.py")

CODIGO = "7790895000997"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(conn, _recurso):
        conn.execute("PRAGMA foreign_keys=ON")

    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def admin(db):
    user = Usuario(username="dueño", password_hash="x", nombre="Dueño", rol="admin")
    db.add(user)
    db.commit()
    return user


def _crear(db, codigo=CODIGO, nombre="Coca Cola 2.25L"):
    data = ProductoCreate(codigo_barras=codigo, nombre=nombre, precio_venta=2500).model_dump()
    return producto_service.crear_producto(db, data)


def _borrar(db, producto):
    producto_service.actualizar_producto(db, producto, {"activo": False})


def test_un_producto_borrado_no_bloquea_el_alta_de_otro_con_el_mismo_codigo(db, admin):
    viejo = _crear(db)
    _borrar(db, viejo)

    nuevo = _crear(db, nombre="Coca Cola 2.25L real")

    assert nuevo.id != viejo.id
    assert nuevo.codigo_barras == CODIGO, "El producto nuevo tiene que quedarse con el código real"
    assert nuevo.activo is True

    db.refresh(viejo)
    assert viejo.activo is False, "El borrado sigue borrado"
    assert viejo.codigo_barras == f"{CODIGO}-borrado-{viejo.id}", (
        "Pierde el código pero deja rastro de cuál tenía: sigue siendo único y no rompe el UNIQUE"
    )


def test_el_alta_sigue_frenando_si_el_codigo_lo_tiene_un_activo(db, admin):
    _crear(db)  # activo

    with pytest.raises(HTTPException) as exc:
        productos_router.crear(
            ProductoCreate(codigo_barras=CODIGO, nombre="Otra gaseosa", precio_venta=100),
            db=db, user=admin,
        )

    assert exc.value.status_code == 400
    assert "Coca Cola 2.25L" in exc.value.detail, "El mensaje tiene que decir cuál es el que lo tiene"


def test_el_lookup_no_devuelve_un_producto_borrado(db, admin, monkeypatch):
    viejo = _crear(db)
    _borrar(db, viejo)

    # Ni el catálogo central ni las fuentes externas: el punto es que tampoco
    # vuelva el borrado de la base local.
    monkeypatch.setattr(productos_router.catalogo_service, "buscar_en_catalogo", lambda code: None)
    monkeypatch.setattr(productos_router.lk, "lookup_producto", lambda code, fuente=None: None)

    with pytest.raises(HTTPException) as exc:
        productos_router.lookup(ProductoLookupRequest(barcode=CODIGO), db=db, user=admin)

    assert exc.value.status_code == 404, "El borrado tiene que saltearse y seguir buscando afuera"


def test_la_lista_se_puede_abrir_con_los_borrados(db):
    viejo = _crear(db)
    _borrar(db, viejo)

    activos, total_activos = producto_service.listar_productos(db)
    assert total_activos == 0 and activos == []

    todos, total_todos = producto_service.listar_productos(db, solo_activos=False)
    assert total_todos == 1 and todos[0].id == viejo.id


def test_la_compra_no_se_pega_a_un_producto_borrado(db):
    # El alta de mercadería miraba el código sin filtrar: la compra terminaba
    # sumando stock a un producto que nadie ve.
    with open(COMPRAS_SRC, encoding="utf-8") as f:
        src = f.read()

    assert "Producto.codigo_barras == codigo, Producto.activo == True" in src


def test_los_datos_demo_no_se_cargan_solos(db, monkeypatch):
    monkeypatch.setattr(demo_service.settings, "SEED_DEMO", False)

    assert demo_service.sembrar_si_corresponde(db) == 0
    assert db.query(Producto).count() == 0, "Una base nueva de un negocio real arranca vacía"


def test_con_seed_demo_si_se_cargan(db, monkeypatch):
    # Lo que main.py arma antes del bloque demo en una instalación nueva.
    db.add(Sucursal(nombre="Principal"))
    db.add(Usuario(username="admin", password_hash="x", nombre="Admin", rol="admin"))
    db.add_all([Categoria(nombre="Almacén"), Categoria(nombre="Bebidas")])
    db.commit()

    monkeypatch.setattr(demo_service.settings, "SEED_DEMO", True)

    assert demo_service.sembrar_si_corresponde(db) == 4
    assert demo_service.sembrar_si_corresponde(db) == 0, "Con productos ya cargados no se vuelve a sembrar"


def test_el_arranque_usa_el_servicio_de_demo_y_no_une_lista_hardcodeada():
    with open(MAIN_SRC, encoding="utf-8") as f:
        src = f.read()

    assert "sembrar_si_corresponde(db)" in src
    assert "7790895000997" not in src, "Los productos de demo no pueden seguir viviendo en main.py"
