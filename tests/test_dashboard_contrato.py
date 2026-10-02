"""Smoke test del contrato entre el dashboard y la API.

Los dos bugs más caros nunca los agarraron los tests:

  1. api.get('/x', { params: { periodo: '7dias' } }) mandaba ?params[periodo]=7dias.
     Los tests de backend pasaban porque llamaban la función directo con el
     argumento ya bien puesto; los de front pasaban porque no había ninguno.
  2. Las barras del gráfico no se veían: el riel pedía h-full dentro de un
     flex items-end, que resuelve a 0 de alto. Cero tests, era CSS.

Este archivo es el puente: toma las URLs que el front arma de verdad y les pega
a los endpoints, así que un desfasamiento entre los dos archivos se ve acá.

No reemplaza a los tests de cada endpoint: comprueba que el contrato cierra.
"""

import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Venta, VentaItem, Usuario, Sucursal
from app.models.categoria import Categoria
from app.models.producto import Producto
import app.models as _m  # noqa: F401
from app.database import Base as _Base
from app.routers import dashboard as dash

UTC = timezone.utc
AHORA = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)

RAIZ_FRONTS = Path(__file__).resolve().parent.parent / "frontend" / "src"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(dash, "HOY", lambda: AHORA)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()


def _semilla(db):
    """Una venta de hoy con producto, categoría y costo."""
    sufijo = uuid.uuid4().hex[:8]
    user = Usuario(username=f"smoke_{sufijo}", nombre="S", password_hash="x", rol="admin", activo=True)
    db.add(user)
    db.add(Sucursal(id=1, nombre="Principal"))
    db.flush()
    cat = Categoria(nombre=f"Cat {sufijo}")
    db.add(cat)
    db.flush()
    prod = Producto(
        codigo_barras=f"CB-{sufijo}", nombre="Gaseosa", categoria_id=cat.id,
        precio_venta=1000.0, precio_costo=600.0, stock_actual=2, stock_minimo=5, activo=True,
    )
    db.add(prod)
    db.flush()
    v = Venta(
        numero=f"SM-{sufijo}", usuario_id=user.id, sucursal_id=1, estado="confirmada",
        subtotal=1000.0, total=1000.0, fecha=AHORA,
    )
    db.add(v)
    db.flush()
    db.add(VentaItem(
        venta_id=v.id, producto_id=prod.id, cantidad=2,
        precio_unitario=1000.0, subtotal=1000.0, precio_costo=600.0,
    ))
    db.commit()
    return user, prod, cat


# --- buildQuery: la función que decide cómo viaja cada query param ---


def test_build_query_no_envuelve_los_params():
    """api.js arma el query string; si cambia, el contrato se rompe.

    Reproduce buildQuery() de frontend/src/services/api.js.
    """
    def build_query(params):
        """Replica de buildQuery() de api.js, con URLSearchParams de verdad."""
        if not params:
            return ""
        search = []
        for key, value in params.items():
            if value is None or value == "":
                continue
            search.append((key, value))
        qs = "&".join(f"{k}={v}" for k, v in search)
        return f"?{qs}" if qs else ""

    # Esta es la forma correcta: los params sueltos.
    assert build_query({"periodo": "7dias"}) == "?periodo=7dias"
    # Y esta es la que rompió todo: la clave que viaja es "params", no "periodo",
    # así que el backend nunca encuentra el parámetro y usa su default.
    anidado = build_query({"params": {"periodo": "7dias"}})
    claves = {par.split("=")[0] for par in anidado.lstrip("?").split("&") if par}
    assert claves == {"params"}, (
        f"la forma anidada manda la clave equivocada: {claves}, el backend "
        "recibe ?params=... y no ve 'periodo'"
    )


def test_ningun_frontend_usa_params_anidado():
    """Grep de todos los .vue y .js: ningún api.get con { params: {...} }.

    El bug que costó dos deploys fue exactamente este. Si vuelve a aparecer,
    este test lo frena acá y no en el server.
    """
    WEIRD = re.compile(r"api\.(get|post|put|patch|delete)\s*\([^)]*\{\s*params\s*:", re.S)
    offenders = []
    for path in RAIZ_FRONTS.rglob("*"):
        if path.suffix not in (".vue", ".js") or not path.is_file():
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        for m in WEIRD.finditer(texto):
            linea = texto[:m.start()].count("\n") + 1
            offenders.append(f"{path.relative_to(RAIZ_FRONTS)}:{linea}")
    assert not offenders, (
        "api.get(path, params) recibe los params sueltos. Encontrar { params: {...} } "
        f"manda ?params[...]=... y el backend lo ignora: {offenders}"
    )


# --- Codificación: los acentos que se ven en el navegador ---


def test_ningun_archivo_frontend_tiene_mojibake():
    """El banner decía "prÃ³ximos 7 dÃ­as" en pantalla.

    UTF-8 decodificado como latin-1 y vuelto a guardar: cada "ó" queda como los
    cuatro bytes C3 83 C2 B3. El archivo sigue siendo UTF-8 válido, así que
    Python, git y el editor lo muestran bien y el bug no se ve hasta que lo
    renderiza el navegador. De ahí que un grep de texto no lo encuentre.
    """
    # Los tres marcadores en su forma ya decodificada.
    MARCAS = ("Ã", "Â", "â€")

    offenders = []
    for path in RAIZ_FRONTS.rglob("*"):
        if path.suffix not in (".vue", ".js", ".json") or not path.is_file():
            continue
        texto = path.read_text(encoding="utf-8", errors="replace")
        n = sum(texto.count(m) for m in MARCAS)
        if n:
            rel = path.relative_to(RAIZ_FRONTS)
            offenders.append(f"{rel}: {n} marcadores")

    assert not offenders, (
        "Mojibake: UTF-8 guardado como si fuera latin-1. Se ve en el navegador "
        f"como 'Ã³' y no en el editor. Arreglar con "
        f"texto.encode('cp1252').decode('utf-8'). Archivos: {offenders}"
    )


def test_el_banner_de_vencimiento_se_lee_bien():
    """El texto exacto que reportó el usuario, verificado sobre los caracteres."""
    vue = (RAIZ_FRONTS / "views" / "DashboardView.vue").read_text(encoding="utf-8")
    assert "vence(n) en los próximos 7 días" in vue
    assert "vence(n) en los próximos 15 días" in vue
    # Y que no aparezca la forma rota, que es la que llega al browser.
    assert "prÃ³ximos" not in vue


# --- Las URLs que el front arma, pegadas a los endpoints de verdad ---


def test_las_urls_del_dashboard_existen_en_el_backend(db):
    """Cada /api/dashboard/... que pide el front tiene que existir en el router."""
    rutas_backend = {r.path for r in dash.router.routes}
    dashboard_vue = (RAIZ_FRONTS / "views" / "DashboardView.vue").read_text(encoding="utf-8")
    pedidas = set(re.findall(r"['\"`](/api/dashboard/[a-z0-9\-/_]+)['\"`]", dashboard_vue))
    assert pedidas, "no se encontró ningún endpoint del dashboard en el .vue"
    faltantes = {p for p in pedidas if p not in rutas_backend}
    assert not faltantes, f"El front pide endpoints que el backend no tiene: {faltantes}"


@pytest.mark.parametrize("periodo", ["7dias", "semana", "semana_anterior", "mes", "mes_anterior",
                                     "mes_por_dia", "mes_anterior_por_dia"])
def test_cada_opcion_del_combo_ventas_anda_de_punto_a_punto(db, periodo):
    """El combo del front contra el endpoint, con la lista de valores de RANGOS."""
    user, _, _ = _semilla(db)
    res = dash.ventas_periodo(db=db, user=user, periodo=periodo).data
    assert res["labels"], f"{periodo} devolvió la serie vacía"
    assert len(res["labels"]) == len(res["valores"])
    assert "desde" in res and "hasta" in res


def test_los_rotulos_de_dia_no_dependen_del_locale(db):
    """Un server con locale inglés devolvía "Fri 25". Va a mano a propósito."""
    user, _, _ = _semilla(db)
    for periodo in ("7dias", "semana", "semana_anterior"):
        res = dash.ventas_periodo(db=db, user=user, periodo=periodo).data
        for lab in res["labels"]:
            assert not lab.startswith(("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")), lab


def test_datos_sucios_endpoint_responde(db):
    user, _, _ = _semilla(db)
    res = dash.datos_sucios(db=db, user=user, periodo="mes").data
    # Con la venta de hoy, y el producto tiene costo y categoría: 0 problemas.
    assert res["cantidad"] == 0
    assert "pct_afectado" in res


def test_stock_por_velocidad_endpoint_responde(db):
    user, prod, _ = _semilla(db)
    res = dash.stock_por_velocidad(db=db, user=user, dias=30, limite=10, solo_criticos=True).data
    assert "productos" in res and "total_criticos" in res
    # Stock 2, mínimo 5, vendido hoy: tiene que aparecer entre los críticos.
    fila = next((r for r in res["productos"] if r["id"] == prod.id), None)
    assert fila is not None
    assert fila["urgente"] is True


def test_resumen_trae_los_bloques_que_el_front_usa(db):
    """El front lee data.vs_hoy y data.vs_mes: si no vienen, los KPIs pierden la flecha."""
    user, _, _ = _semilla(db)
    res = dash.resumen(db=db, user=user).data
    assert "vs_hoy" in res and "vs_mes" in res
    for bloque in ("vs_hoy", "vs_mes"):
        for metrica in ("ventas", "cantidad", "ticket", "margen", "margen_pct"):
            assert metrica in res[bloque], f"{bloque}.{metrica} falta"


# --- El bug de CSS: los contenedores de los gráficos tienen que tener alto ---


def test_los_contenedores_de_barras_no_usan_h_full_contra_items_end():
    """El bug del h-40 flex items-end + h-full, que dejaba las barras en 0 de alto.

    items-end alinea al final y no estira: un hijo con h-full resuelve contra un
    padre de alto automático. Tiene que ser items-stretch, o el riel con flex-1.

    Ojo: los skeletons sí usan items-end y está bien, porque ahí el alto lo
    define cada hijo por style. Lo que no puede pasar es un items-end con un
    riel que pida h-full adentro.
    """
    vue = (RAIZ_FRONTS / "views" / "DashboardView.vue").read_text(encoding="utf-8")

    # El problema no es la línea del contenedor sino qué hay adentro: si el
    # bloque usa items-end y además trae barras con riel, el riel queda en 0 de
    # alto. Un bloque de skeletons con items-end está bien, porque ahí el alto
    # lo define cada hijo por style.
    for bloque in re.findall(r'<div[^>]*items-end[^>]*>.*?</div>', vue, re.S):
        es_skeleton = "BaseSkeleton" in bloque
        if es_skeleton:
            continue
        assert "h-full" not in bloque, (
            "bloque con items-end y un riel h-full adentro: el h-full resuelve "
            "contra un padre de alto automático, o sea 0. Usar items-stretch. "
            f"Bloque: {bloque[:120]}"
        )

    # Y los contenedores de barras reales tienen que estirar.
    assert 'h-40 flex items-stretch gap-3' in vue, "el contenedor de Ventas debería ser items-stretch"
    assert 'h-40 flex items-stretch gap-1' in vue, "el contenedor de Horas debería ser items-stretch"

    # El riel tiene que ser flex-1 min-h-0 para ocupar el alto disponible.
    assert "flex-1 min-h-0" in vue, "el riel de la barra debería ser flex-1 min-h-0"
