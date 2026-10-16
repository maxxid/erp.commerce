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
import json
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


def _cuerpo_de_funcion(texto, nombre, siguiente):
    """Lo que hay entre una función y la siguiente, para no adivinar con índices."""
    inicio = texto.index(f"async function {nombre}(")
    fin = texto.index(f"async function {siguiente}(", inicio)
    return texto[inicio:fin]


class TestContenido:
    def test_trae_las_tres_listas_con_una_sola_fecha(self, db, user):
        _producto(db, "7790001")

        snap = catalogo_local.snapshot_local(db)

        assert set(snap) == {"version", "generado", "productos", "categorias", "ofertas", "totales"}
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


class TestVersion:
    """~100 bytes para no bajar 0,41 MB cada vez que se abre el POS."""

    def test_es_una_respuesta_chiquita(self, db, user):
        _producto(db, "7790001")
        _categoria(db, "Bebidas sin alcohol")
        _categoria(db, "Alfajores y golosinas")

        v = catalogo_local.version_local(db)

        assert set(v) == {"productos", "categorias", "ofertas", "stock"}
        # Un catálogo de verdad pesa ~400.000 bytes: si la versión no es órdenes
        # de magnitud menor, deja de servir para no bajar el catálogo.
        assert len(json.dumps(v)) < 1200

    def test_un_renombre_de_categoria_se_detecta(self, db, user):
        """`Categoria` no tiene `updated_at`: si no se mirara el nombre, la
        versión diría "no cambió nada" con las categorías recién renombradas."""
        cat = _categoria(db, "Bebidas")
        v0 = catalogo_local.version_local(db)

        cat.nombre = "Bebidas y jugos"
        db.commit()

        assert catalogo_local.version_local(db) != v0

    def test_cambia_si_se_agrega_un_producto(self, db, user):
        v0 = catalogo_local.version_local(db)

        _producto(db, "7790001")

        assert catalogo_local.version_local(db) != v0

    def test_el_stock_de_los_lotes_cambia_la_version(self, db, user):
        p = _producto(db, "7790001")

        v0 = catalogo_local.version_local(db)
        _lote(db, p, 10)
        v1 = catalogo_local.version_local(db)

        assert v0 != v1
        assert v1["stock"]["unidades"] == 10

    def test_un_movimiento_que_no_toca_el_producto_tambien_se_detecta(self, db, user):
        """Lo que le pasa al POS si la versión mirara solo los productos.

        Una venta mueve un lote sin tocar `productos.updated_at`. Si ese fuera
        el único indicador, la versión diría "no cambió nada" y el POS se
        quedaría mostrando un stock que ya no existe —que es justo el error
        feo, porque no se nota hasta que alguien se queda sin mercadería.
        """
        p = _producto(db, "7790001")
        _lote(db, p, 10)
        lote = db.query(Lote).one()
        v0 = catalogo_local.version_local(db)

        # Se fuerza el caso en que ni el producto ni `lotes.updated_at` cambian
        # (SQL crudo, sin `onupdate`): sólo se mueven las unidades.
        marca = lote.updated_at
        lote.cantidad_actual = 4
        db.flush()
        lote.updated_at = marca
        db.commit()

        assert catalogo_local.version_local(db) != v0

    def test_un_cambio_entre_la_version_y_el_listado_no_queda_como_al_dia(self, db, monkeypatch):
        """La versión se calcula ANTES de armar el snapshot.

        Si se calculara después, una venta que llegara mientras se arma el
        snapshot quedaría registrada como "ya está al día", y ese cambio no se
        volvería a bajar nunca: el navegador se quedaría para siempre con el
        catálogo anterior a la venta.
        """
        from app.services import producto_service

        original = producto_service.listar_productos

        def listar_con_un_cambio_de_mas(sess, **kwargs):
            _producto(sess, "7798888")
            return original(sess, **kwargs)

        monkeypatch.setattr(producto_service, "listar_productos", listar_con_un_cambio_de_mas)

        snapshot = catalogo_local.snapshot_local(db)

        assert snapshot["version"] != catalogo_local.version_local(db), (
            "la versión guardada quedó por delante del listado: el cambio que "
            "ocurrió mientras se armaba el snapshot no se volvería a bajar nunca"
        )

    def test_el_snapshot_lleva_la_misma_version_que_el_endpoint(self, db, user):
        """Si los dos dijeran cosas distintas, el navegador nunca confirmaría
        que su catálogo está al día y bajaría el completo en cada apertura."""
        _producto(db, "7790001")

        snapshot = catalogo_local.snapshot_local(db)

        assert snapshot["version"] == catalogo_local.version_local(db)

    def test_esta_registrado_y_pide_token(self):
        from app.main import app

        rutas = app.openapi()["paths"]
        assert "/api/catalogo/version" in rutas
        assert "get" in rutas["/api/catalogo/version"]

        deps = inspect.signature(catalogo.version_del_catalogo_local).parameters
        assert deps["user"].default.dependency is get_current_user


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

        assert "if (!completo || !Array.isArray(completo.productos))" in texto
        assert "sinRed.value = true" in texto

    def test_saca_el_aviso_cuando_vuelve_a_llegar_el_catalogo(self):
        texto = self._store()

        assert "sinRed.value = false" in texto

    def test_antes_de_bajar_pregunta_si_cambio(self):
        """Es el punto de la Fase D: refrescar cuesta ~100 bytes, no 0,41 MB."""
        texto = self._store()

        assert "api.get('/api/catalogo/version')" in texto
        assert "JSON.stringify(version) === JSON.stringify(snapshot.version)" in texto

    def test_si_no_pudo_confirmar_que_no_cambio_baja_igual(self):
        """Ante la duda se refresca: lo que no se hace es quedarse con datos
        viejos por ahorrar unos bytes."""
        texto = self._store()

        assert "si la versión no se pudo confirmar se baja igual" in texto

    def test_baja_el_catalogo_en_un_solo_pedido(self):
        """Eran tres requests por apertura; el snapshot ya trae las tres listas."""
        texto = self._store()
        fetch = _cuerpo_de_funcion(texto, "fetchAll", "refreshProductos")

        assert "api.get('/api/catalogo/local')" in fetch
        assert "/api/productos?" not in fetch, (
            "fetchAll volvió a pedir las listas por separado"
        )

    def test_sin_senal_no_se_ni_siquiera_se_intenta(self):
        """Un fetch que va a fallar deja la pantalla esperando y gasta batería."""
        texto = self._store()

        assert "if (typeof navigator !== 'undefined' && !navigator.onLine)" in texto

    def test_el_indicador_muestra_de_cuándo_es_el_catálogo(self):
        """El dato que importa sin red es la antigüedad de lo que se cobra."""
        texto = INDICADOR.read_text(encoding="utf-8")

        assert "productosStore" in texto
        assert "antiguedadCatalogo" in texto
        assert "haceCuanto" in texto
        assert "de hace" in texto
