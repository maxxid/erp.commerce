""""Últimas transacciones" del POS: sólo las del día (dueño, Prueba 3).

**El pedido**: en la pantalla del POS, el panel "Últimas transacciones" mostraba
las 5 últimas ventas confirmadas de cualquier día. El dueño mandó: "últimas
transacciones, sólo las del día".

Cuidado con el corrimiento horario: la base guarda `Venta.fecha` en UTC naive
sin zona y el negocio vive en Argentina (UTC-3). Un "hoy" argentino son dos
días UTC distintos (00:00-03:00 AR = 03:00-06:00 UTC). Filtrando con la fecha
UTC tal cual, el panel dejaba afuera la madrugada de hoy y metía la noche
anterior (21-24 AR del día anterior = 00-03 UTC de hoy).

Acá se cubre que:
- el router acepte `fecha_desde`/`fecha_hasta` como **día argentino** y devuelva
  sólo ese día;
- no se cuelen las ventas de la noche anterior ni quede fuera la madrugada;
- `fecha_hasta` incluya el último día pedido;
- una fecha mal escrita no termine en error 500;
- el POS mande el filtro (si no, el panel vuelve a mostrar cualquier día).
"""

import pathlib
import re
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.models import Sucursal, Usuario
from app.models.venta import Venta
from app.routers import ventas as router_ventas

RAIZ = pathlib.Path(__file__).resolve().parents[1]
POS_VIEW = RAIZ / "frontend" / "src" / "views" / "POSView.vue"

TZ_AR = timezone(timedelta(hours=-3))


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(conn, _recurso):
        conn.execute("PRAGMA foreign_keys=ON")

    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(Sucursal(id=1, nombre="Principal"))
        session.flush()
        session.add(Usuario(
            username="caja_turno", nombre="Cajero", password_hash="x",
            rol="cajero", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _usuario(db):
    return db.query(Usuario).first()


def _hoy_ar() -> str:
    """Día argentino de hoy en YYYY-MM-DD: exactamente lo que manda el POS."""
    return datetime.now(TZ_AR).strftime("%Y-%m-%d")


def _venta(db, fecha_utc: datetime) -> Venta:
    """Venta confirmada con una fecha exacta (naive UTC, como la guarda SQLite)."""
    venta = Venta(
        numero=f"V{db.query(Venta).count() + 1:05d}",
        usuario_id=_usuario(db).id,
        sucursal_id=1,
        subtotal=100.0,
        total=100.0,
        medio_pago="efectivo",
        estado="confirmada",
        fecha=fecha_utc,
        created_at=fecha_utc,
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)
    return venta


def _listar(db, **filtros):
    """Llama al router directo (sin TestClient): los Query() por defecto sólo
    los resuelve FastAPI, así que hay que pasar todos los filtros a mano."""
    params = dict(
        estado=None, cliente_id=None,
        fecha_desde=None, fecha_hasta=None,
        page=1, page_size=50,
    )
    params.update(filtros)
    return router_ventas.listar(db=db, user=_usuario(db), **params)


def test_filtra_solo_las_ventas_de_hoy(db):
    del_dia = _venta(db, datetime.now(timezone.utc))
    de_anteayer = _venta(db, datetime.now(timezone.utc) - timedelta(days=2))

    resp = _listar(db, fecha_desde=_hoy_ar())

    ids = [v["id"] for v in resp.data]
    assert ids == [del_dia.id]
    assert resp.total == 1
    assert de_anteayer.id not in ids


def test_no_se_cuela_la_noche_anterior_ni_falta_la_madrugada(db):
    """El borde argentino: 22:00 AR de ayer es 01:00 UTC de hoy."""
    hoy_ar = datetime.now(TZ_AR).date()
    noche_de_ayer = datetime(hoy_ar.year, hoy_ar.month, hoy_ar.day, 1, 0)   # 01:00 UTC = 22:00 AR de ayer
    madrugada_de_hoy = datetime(hoy_ar.year, hoy_ar.month, hoy_ar.day, 4, 0)  # 04:00 UTC = 01:00 AR de hoy

    ayer = _venta(db, noche_de_ayer)
    recien_abierta = _venta(db, madrugada_de_hoy)

    resp = _listar(db, fecha_desde=hoy_ar.strftime("%Y-%m-%d"))

    ids = [v["id"] for v in resp.data]
    assert ids == [recien_abierta.id]
    assert ayer.id not in ids


def test_fecha_hasta_incluye_ese_dia(db):
    ayer_ar = datetime.now(TZ_AR).date() - timedelta(days=1)
    de_ayer = _venta(
        db,
        datetime(ayer_ar.year, ayer_ar.month, ayer_ar.day, 15, 0),  # 12:00 AR de ayer
    )
    _venta(db, datetime.now(timezone.utc))

    ayer_str = ayer_ar.strftime("%Y-%m-%d")
    resp = _listar(db, fecha_desde=ayer_str, fecha_hasta=ayer_str)

    ids = [v["id"] for v in resp.data]
    assert ids == [de_ayer.id]
    assert resp.total == 1


def test_fecha_mal_escrita_no_devuelve_500(db):
    _venta(db, datetime.now(timezone.utc))

    with pytest.raises(HTTPException) as exc:
        _listar(db, fecha_desde="20-10-2026")

    assert exc.value.status_code == 400
    assert "YYYY-MM-DD" in exc.value.detail


def test_el_pos_pide_las_transacciones_de_hoy():
    src = POS_VIEW.read_text(encoding="utf-8")

    m = re.search(r"api\.get\(\s*[`'\"]([^`'\"]*api/ventas\?[^`'\"]*)[`'\"]\s*\)", src)
    assert m, "No se encontró la petición de ventas del panel Últimas Transacciones"
    url = m.group(1)
    assert "fecha_desde=" in url, "El panel tendría que pedir sólo las ventas de hoy"
    assert "estado=confirmada" in url, "El backend no tiene estado 'completada'"

    # Sin el import, `fechaLocalAR(new Date())` revienta al abrir el POS.
    imp = re.search(r"import \{([^}]*)\} from '@/composables/useUtils'", src)
    assert imp and "fechaLocalAR" in imp.group(1)
