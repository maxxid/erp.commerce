"""Catálogo local: que el POS tenga con qué vender cuando se corta la internet.

Es el nivel 1 del offline. Antes, cuando se iba la conexión, el navegador se
quedaba sin catálogo: el service worker cacheaba `/api/productos` solo si esa
URL exacta se había pedido antes, y **sin fecha**, así que no había forma de
saber si los precios que se estaban cobrando eran los de hoy o de hace dos
meses.

Ahora hay un snapshot (`GET /api/catalogo/local`) que junta productos,
categorías y ofertas en una sola respuesta con un solo `generado`; el store del
catálogo lo guarda en el navegador y lo restaura cuando la red falla; y el aviso
superior muestra la antigüedad de lo que se está usando.

La regla que sostiene todo esto es una sola: **lo que se ve offline tiene que
ser idéntico a lo que se ve online**. Si no lo fuera, el catálogo offline sería
una segunda verdad que eventualmente contradice a la primera — y a diferencia de
un error de precio a la vista, esa contradicción se descubre cobrando mal.
Por eso el snapshot reutiliza los mismos serializadores que los endpoints
normales en vez de armar su propia versión "más liviana" del producto.
"""

import inspect
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.encoders import jsonable_encoder
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.auth.dependencies import get_current_user
from app.auth.security import hash_password
from app.database import Base as _Base
from app.models.categoria import Categoria
from app.models.lote import Lote
from app.models.oferta import Oferta
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.routers import catalogo, categorias as router_categorias
from app.routers import ofertas as router_ofertas, productos as router_productos
from app.schemas.categoria import CategoriaOut
from app.services import catalogo_local

RAIZ = Path(__file__).resolve().parent.parent
STORE_PRODUCTOS = RAIZ / "frontend" / "src" / "stores" / "productos.js"
INDICADOR = RAIZ / "frontend" / "src" / "components" / "layout" / "OfflineIndicator.vue"

# Mismos valores que usan los endpoints normales: el snapshot tiene que devolver
# exactamente lo que vería el POS con red.
LISTAR_PRODUCTOS = dict(
    search=None, categoria_id=None, solo_activos=True, page=1, page_size=100000,
)
LISTAR_OFERTAS = dict(
    producto_id=None, solo_activas=False, page=1, page_size=100000,
)


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
    u = Usuario(
        username="caja1", nombre="Caja", password_hash=hash_password("secret1"),
        rol="cajero", permisos="[]",
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _categoria(db, nombre):
    c = Categoria(nombre=nombre)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _producto(db, codigo, nombre="Algo", activo=True, categoria=None, stock_columna=None):
    p = Producto(
        codigo_barras=codigo, nombre=nombre, precio_venta=100.0,
        categoria_id=categoria.id if categoria else None, activo=activo,
    )
    if stock_columna is not None:
        p.stock_actual = stock_columna
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def _lote(db, producto, cantidad):
    l = Lote(
        producto_id=producto.id, cantidad_inicial=cantidad,
        cantidad_actual=cantidad, activo=True,
    )
    db.add(l)
    db.commit()
    return l


def _por_id(lista):
    """El orden lo decide `updated_at.desc()`; se compara por id para que dos
    consultas idénticas no se caigan en una diferencia de desempate."""
    return sorted(lista, key=lambda p: p["id"])


class TestContenido:
    def test_trae_las_tres_listas_con_una_sola_fecha(self, db, user):
        _producto(db, "7790001")

        snap = catalogo_local.snapshot_local(db)

        assert set(snap) == {"generado", "productos", "categorias", "ofertas", "totales"}
        assert isinstance(snap["productos"], list)
        assert isinstance(snap["categorias"], list)
        assert isinstance(snap["ofertas"], list)

        # Una sola fecha para las tres listas: si cada una tuviera la suya, el
        # "hace cuánto" del aviso sería mentira a medias.
        generado = datetime.fromisoformat(snap["generado"])
        assert generado.tzinfo is not None, "sin zona horaria no se puede comparar con ahora"
        edad = (datetime.now(timezone.utc) - generado).total_seconds()
        assert 0 <= edad < 60

    def test_solo_entran_los_productos_activos(self, db, user):
        _producto(db, "7790001", activo=True)
        _producto(db, "7790002", activo=False)

        snap = catalogo_local.snapshot_local(db)

        assert [p["codigo_barras"] for p in snap["productos"]] == ["7790001"]

    def test_el_stock_sale_de_los_lotes_y_no_de_la_columna(self, db, user):
        """La columna `stock_actual` es un dato editable y se desfasa.

        Si el snapshot la copiara tal cual, el POS offline mostraría stock
        viejo —y a diferencia de un precio desfasado, este no se nota hasta que
        alguien se queda sin mercadería. Los lotes son la fuente de verdad.
        """
        p = _producto(db, "7790001", stock_columna=999)
        _lote(db, p, 7)
        _lote(db, p, 3)

        snap = catalogo_local.snapshot_local(db)

        assert snap["productos"][0]["stock_actual"] == 10

    def test_las_categorias_llevan_cuántos_productos_tienen(self, db, user):
        cat = _categoria(db, "Bebidas")
        _producto(db, "7790001", categoria=cat)
        _producto(db, "7790002", categoria=cat)
        _producto(db, "7790003")

        snap = catalogo_local.snapshot_local(db)

        bebidas = next(c for c in snap["categorias"] if c["nombre"] == "Bebidas")
        assert bebidas["cantidad_productos"] == 2

    def test_las_categorias_no_arrastran_los_productos_enteros(self, db, user):
        """Cada categoría trae sus productos: serializarla entera multiplicaría
        el tamaño del snapshot por el número de categorías."""
        cat = _categoria(db, "Bebidas")
        for i in range(5):
            _producto(db, f"779000{i}", categoria=cat)

        snap = catalogo_local.snapshot_local(db)

        campos_esperados = set(CategoriaOut.model_fields)
        for c in snap["categorias"]:
            assert set(c) == campos_esperados, (
                f"la categoría {c['nombre']} trae campos de más: "
                f"{set(c) - campos_esperados}"
            )

    def test_las_ofertas_llevan_los_campos_que_el_pos_necesita(self, db, user):
        p = _producto(db, "7790001")
        db.add(Oferta(
            producto_id=p.id, tipo="porcentaje", valor=10,
            requiere_cantidad=1, activo=True,
        ))
        db.commit()

        snap = catalogo_local.snapshot_local(db)

        assert len(snap["ofertas"]) == 1
        oferta = snap["ofertas"][0]
        assert oferta["producto_id"] == p.id
        assert oferta["tipo"] == "porcentaje"
        assert oferta["valor"] == 10


class TestOfflineIgualQueOnline:
    """Lo que se cobra sin red tiene que ser lo mismo que se cobra con red."""

    def test_los_productos_son_idénticos_a_los_del_listado_normal(self, db, user):
        _producto(db, "7790001", "Coca 2L")
        _producto(db, "7790002", "Fanta 2L")

        online = jsonable_encoder(
            router_productos.listar(db=db, user=user, **LISTAR_PRODUCTOS).data
        )
        offline = catalogo_local.snapshot_local(db)["productos"]

        assert _por_id(offline) == _por_id(online)

    def test_el_snapshot_no_expone_campos_que_la_lista_normal_no_expone(self, db, user):
        """No es una copia nueva del producto: es la misma salida, con la misma
        visibilidad que ya tenía el endpoint normal."""
        _producto(db, "7790001")

        online = jsonable_encoder(
            router_productos.listar(db=db, user=user, **LISTAR_PRODUCTOS).data
        )
        offline = catalogo_local.snapshot_local(db)["productos"]

        assert set(offline[0]) == set(online[0])

    def test_las_ofertas_son_idénticas_a_las_del_listado_normal(self, db, user):
        p = _producto(db, "7790001")
        db.add(Oferta(
            producto_id=p.id, tipo="2x1", valor=0, requiere_cantidad=2, activo=True,
        ))
        db.commit()

        online = router_ofertas.listar(db=db, user=user, **LISTAR_OFERTAS).data
        offline = catalogo_local.snapshot_local(db)["ofertas"]

        assert offline == online

    def test_las_categorias_son_idénticas_a_las_del_listado_normal(self, db, user):
        cat = _categoria(db, "Bebidas")
        _producto(db, "7790001", categoria=cat)
        _categoria(db, "Snacks")

        online_orm = router_categorias.listar(db=db, user=user).data
        # Es lo mismo que arma FastAPI al serializar con response_model.
        online = [CategoriaOut.model_validate(c).model_dump() for c in online_orm]
        offline = catalogo_local.snapshot_local(db)["categorias"]

        assert offline == online


class TestEndpoint:
    def test_esta_registrado(self):
        from app.main import app

        rutas = app.openapi()["paths"]

        assert "/api/catalogo/local" in rutas
        assert "get" in rutas["/api/catalogo/local"]

    def test_pide_token_igual_que_el_listado_de_productos(self):
        """Es el mismo dato que `/api/productos`: no puede ser una ventana abierta."""
        deps = inspect.signature(catalogo.catalogo_local_para_el_navegador).parameters

        assert deps["user"].default.dependency is get_current_user


class TestElNavegadorLoGuarda:
    """Frontend: el store persiste el snapshot y lo restaura cuando falla."""

    @staticmethod
    def _store():
        return STORE_PRODUCTOS.read_text(encoding="utf-8")

    def test_se_guarda_con_una_clave_de_la_app(self):
        texto = self._store()

        assert "const CLAVE_CATALOGO = 'apex-catalogo-local'" in texto
        assert "localStorage.setItem(CLAVE_CATALOGO" in texto

    def test_no_explota_si_el_navegador_no_deja_guardar(self):
        """Cota llena o pestaña privada: tiene que seguir andando igual."""
        texto = self._store()

        assert "function guardarSnapshot(datos)" in texto
        assert "return false" in texto

    def test_se_restaura_en_cuanto_se_arma_el_store(self):
        """Si no se restaura apenas se arma, el POS arranca con la grilla vacía
        y recién después se entera de que no había red."""
        texto = self._store()

        assert "aplicarSnapshot(leerSnapshot())" in texto

    def test_cae_al_snapshot_cuando_no_llegaron_productos(self):
        texto = self._store()

        assert "if (!Array.isArray(prods))" in texto
        assert "sinRed.value = true" in texto

    def test_saca_el_aviso_cuando_vuelve_a_llegar_el_catalogo(self):
        texto = self._store()

        assert "sinRed.value = false" in texto

    def test_el_indicador_muestra_de_cuándo_es_el_catálogo(self):
        """El dato que importa sin red es la antigüedad de lo que se cobra."""
        texto = INDICADOR.read_text(encoding="utf-8")

        assert "productosStore" in texto
        assert "antiguedadCatalogo" in texto
        assert "haceCuanto" in texto
        assert "de hace" in texto
