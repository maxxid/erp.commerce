"""Tests del historial de caja (`GET /api/caja/reportes`).

El endpoint agrupa los movimientos en sesiones (apertura -> ingresos/egresos ->
cierre) para la tabla del Historial de Caja. Iteraba en orden DESC pero la
agrupación asume orden cronológico: cada cierre se le asignaba a la apertura
siguiente, los movimientos de la sesión quedaban huérfanos (sesion_actual en
None) y el historial mostraba, por ejemplo, una apertura de $0 con un cierre de
$156.000 que no le correspondía y todos los ingresos en $0.

Además:
- Las sesiones sin cierre quedaban eternamente "Abierta" aunque el sistema ya
  permitiera abrir una nueva caja: ahora una apertura posterior las marca
  "sin_cierre".
- Los totales solo se calculaban al cerrar: las sesiones abiertas o sin
  cierre mostraban ingresos y egresos en $0.
- El filtro de fechas comparaba created_at (UTC) contra medianoche local
  naive: una sesión de las 22:00 AR caía al día siguiente.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario, Sucursal
from app.models.movimiento_caja import MovimientoCaja
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.routers.caja import reportes_caja
from app.services import caja_service as cs
from app.services import config_service

UTC = timezone.utc


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        sufijo = uuid.uuid4().hex[:8]
        session.add(Sucursal(id=1, nombre="Principal"))
        session.flush()
        session.add(Usuario(
            username=f"hist_{sufijo}", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _uid(db):
    return db.query(Usuario).first().id


def _abrir(db, monto_inicial=20000.0):
    return cs.abrir_caja(db, monto_inicial, _uid(db), monto_retiro=0.0)


def _vender(db, monto, medio="efectivo"):
    return cs.registrar_ingreso(
        db, monto, f"Venta {medio}", _uid(db),
        referencia_tipo="venta", medio_pago=medio,
    )


def _cerrar(db):
    cierre, _ = cs.cerrar_todo(db, _uid(db))
    return cierre


def _sesiones(db, fecha_inicio=None, fecha_fin=None):
    resp = reportes_caja(fecha_inicio=fecha_inicio, fecha_fin=fecha_fin, db=db, user=None)
    return resp.data["sesiones"]


def _por_apertura(sesiones, apertura_id):
    return next(s for s in sesiones if s["apertura_id"] == apertura_id)


class TestAgrupacionPorSesiones:
    def test_cada_cierre_cierra_su_propia_sesion(self, db):
        # Regresión del bug DESC: el cierre de la sesión 1 no puede terminarle
        # a la sesión 2, y los ingresos de la sesión 1 no pueden perderse.
        ap1 = _abrir(db, 10000.0)
        _vender(db, 5000.0, "efectivo")
        _vender(db, 2000.0, "debito")
        cierre1 = _cerrar(db)
        ap2 = _abrir(db, 17000.0)
        _vender(db, 3000.0, "efectivo")

        sesiones = _sesiones(db)

        assert len(sesiones) == 2
        s1 = _por_apertura(sesiones, ap1.id)
        assert s1["estado"] == "cerrada"
        assert s1["cierre_id"] == cierre1.id
        assert s1["cierre_monto"] == 17000.0
        assert s1["total_ingresos"] == 7000.0
        assert s1["total_egresos"] == 0.0
        assert s1["saldo_final"] == 17000.0

        s2 = _por_apertura(sesiones, ap2.id)
        assert s2["estado"] == "abierta"
        assert "cierre_id" not in s2
        assert s2["total_ingresos"] == 3000.0

    def test_los_ingresos_no_se_duplican_ni_se_pierden(self, db):
        ap1 = _abrir(db, 10000.0)
        _vender(db, 5000.0)
        _cerrar(db)
        ap2 = _abrir(db, 15000.0)
        _vender(db, 4000.0)
        _vender(db, 1000.0)

        sesiones = _sesiones(db)

        assert _por_apertura(sesiones, ap1.id)["total_ingresos"] == 5000.0
        assert _por_apertura(sesiones, ap2.id)["total_ingresos"] == 5000.0

    def test_egresos_quedan_en_su_sesion(self, db):
        ap = _abrir(db, 20000.0)
        _vender(db, 5000.0)
        cs.registrar_egreso(db, 3000.0, "Retiro", _uid(db))

        sesion = _por_apertura(_sesiones(db), ap.id)

        assert sesion["total_egresos"] == 3000.0
        assert sesion["saldo_final"] == 22000.0

    def test_el_orden_es_de_mas_reciente_a_mas_antiguo(self, db):
        ap1 = _abrir(db, 10000.0)
        _cerrar(db)
        ap2 = _abrir(db, 10000.0)
        _cerrar(db)

        sesiones = _sesiones(db)

        assert [s["apertura_id"] for s in sesiones] == [ap2.id, ap1.id]


class TestSesionesSinCierre:
    def test_una_apertura_posterior_marca_sin_cierre(self, db):
        # La caja de ayer se olvidó de cerrar (el auto-cierre está desactivado,
        # como en el server): hoy se puede abrir de nuevo, pero la sesión vieja
        # no queda "Abierta", quedó sin cierre registrado.
        config_service.set_config(db, "caja_cierre_automatico", "false")
        ap1 = _abrir(db, 10000.0)
        _vender(db, 5000.0)
        ap1.created_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
        ap2 = _abrir(db, 15000.0)

        sesiones = _sesiones(db)

        s1 = _por_apertura(sesiones, ap1.id)
        assert s1["estado"] == "sin_cierre"
        assert "cierre_id" not in s1
        assert _por_apertura(sesiones, ap2.id)["estado"] == "abierta"

    def test_calcula_totales_aunque_no_haya_cierre(self, db):
        ap = _abrir(db, 20000.0)
        _vender(db, 7000.0, "efectivo")
        _vender(db, 2000.0, "debito")
        cs.registrar_egreso(db, 1000.0, "Retiro", _uid(db))

        sesion = _por_apertura(_sesiones(db), ap.id)

        assert sesion["estado"] == "abierta"
        assert sesion["total_ingresos"] == 9000.0
        assert sesion["total_egresos"] == 1000.0
        assert sesion["saldo_final"] == 28000.0


class TestFiltroDeFechas:
    def test_une_la_sesion_nocturna_al_dia_local(self, db):
        # Una sesión abierta a las 23:00 AR es 02:00 UTC del día siguiente:
        # tiene que aparecer en el día local, no en el UTC.
        ap = _abrir(db, 10000.0)
        ap.created_at = datetime(2026, 3, 10, 2, 0, 0)  # 09/03 23:00 AR
        db.commit()

        sesiones = _sesiones(db, fecha_inicio="2026-03-09", fecha_fin="2026-03-09")

        assert [s["apertura_id"] for s in sesiones] == [ap.id]

    def test_excluye_la_noche_anterior(self, db):
        # Dos sesiones, una por noche: filtrar el día 09/03 no puede traer la
        # sesión abierta a las 23:00 del 08/03 (09/03 02:00 UTC).
        ap1 = _abrir(db, 10000.0)
        cierre1 = _cerrar(db)
        ap2 = _abrir(db, 10000.0)
        # 08/03 23:00 AR = 09/03 02:00 UTC → pertenece al día local 08/03
        ap1.created_at = datetime(2026, 3, 9, 2, 0, 0)
        cierre1.created_at = datetime(2026, 3, 9, 4, 0, 0)
        # 09/03 23:00 AR = 10/03 02:00 UTC → pertenece al día local 09/03
        ap2.created_at = datetime(2026, 3, 10, 2, 0, 0)
        db.commit()

        sesiones = _sesiones(db, fecha_inicio="2026-03-09", fecha_fin="2026-03-09")

        assert [s["apertura_id"] for s in sesiones] == [ap2.id]

    def test_sin_filtros_devuelve_todo(self, db):
        _abrir(db, 10000.0)
        _cerrar(db)
        _abrir(db, 10000.0)

        assert len(_sesiones(db)) == 2


class TestCierreAutomaticoEnHistorial:
    def test_el_cierre_automatico_cierra_la_sesion_anterior(self, db):
        config_service.set_config(db, "caja_cierre_automatico", "true")
        ap1 = _abrir(db, 20000.0)
        _vender(db, 10000.0)
        ap1.created_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
        ap2 = _abrir(db, 30000.0)

        sesiones = _sesiones(db)

        s1 = _por_apertura(sesiones, ap1.id)
        assert s1["estado"] == "cerrada"
        assert s1["fue_automatico"] is True
        assert s1["cierre_monto"] == 30000.0
        assert _por_apertura(sesiones, ap2.id)["estado"] == "abierta"
