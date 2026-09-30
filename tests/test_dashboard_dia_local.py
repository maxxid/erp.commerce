"""Tests del límite de "día" del dashboard.

El mini-dashboard del POS (y el Dashboard completo) usaban medianoche UTC como
inicio del día. En Argentina (UTC-3) eso empezaba el "día" a las 21:00 local,
así que las ventas de la noche desaparecían de "Ventas Hoy" (y al otro lado,
las de las 21:00-00:00 del día anterior aparecían de más). Desde la fix, el día
de negocio es local (UT-3), igual que el cierre de caja.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Venta, Usuario, Sucursal
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.routers import dashboard as dash

UTC = timezone.utc


def _dt(iso_utc):
    return datetime.fromisoformat(iso_utc).replace(tzinfo=UTC)


class TestLimiteDeDiaLocal:
    def test_noche_local_pertenece_al_mismo_dia_de_negocio(self):
        # 22:00 local del 29/09 es 01:00 UTC del 30/09
        ahora = _dt("2026-09-30T01:04:00")
        assert dash._inicio_dia(ahora) == _dt("2026-09-29T03:00:00")

    def test_venta_de_la_noche_cae_en_el_mismo_dia_que_una_de_la_manana(self):
        manana = _dt("2026-09-29T13:00:00")   # 10:00 local
        noche = _dt("2026-09-30T00:30:00")    # 21:30 local (día anterior en UTC)
        assert dash._inicio_dia(noche) == dash._inicio_dia(manana)

    def test_recien_pasada_la_medianoche_local_arranca_otro_dia(self):
        # 00:30 local del 30/09 = 03:30 UTC del 30/09
        ahora = _dt("2026-09-30T03:30:00")
        assert dash._inicio_dia(ahora) == _dt("2026-09-30T03:00:00")

    def test_inicio_mes_y_trimestre_local(self):
        ahora = _dt("2026-09-30T01:04:00")  # 22:04 local del 29/09
        assert dash._inicio_mes(ahora) == _dt("2026-09-01T03:00:00")
        assert dash._inicio_trimestre(ahora) == _dt("2026-07-01T03:00:00")

    def test_helpers_sin_argumento_usan_zona_local(self, monkeypatch):
        monkeypatch.setattr(dash, "HOY", lambda: _dt("2026-09-30T01:04:00"))
        assert dash._inicio_dia() == _dt("2026-09-29T03:00:00")


class TestResumenCuentaLasVentasDeHoyLocal:
    def test_ventas_de_manana_y_noche_cuentan_como_hoy(self, monkeypatch):
        # AHORA real = 01:04 UTC del 30/09 (22:04 local del 29/09)
        ahora = _dt("2026-09-30T01:04:00")
        monkeypatch.setattr(dash, "HOY", lambda: ahora)

        engine = create_engine(
            "sqlite:///:memory:", connect_args={"check_same_thread": False}
        )
        _Base.metadata.create_all(bind=engine)
        db = sessionmaker(bind=engine)()
        try:
            sufijo = uuid.uuid4().hex[:8]
            user = Usuario(
                username=f"dash_tz_{sufijo}", nombre="TZ", password_hash="x",
                rol="admin", activo=True,
            )
            db.add(user)
            db.flush()
            db.add(Sucursal(id=1, nombre="Principal"))
            db.commit()

            ventas = [
                ("HS", 1000.0, _dt("2026-09-29T13:00:00")),  # 10:00 local
                ("HN", 2500.0, _dt("2026-09-30T00:30:00")),  # 21:30 local
                ("AY", 500.0, _dt("2026-09-28T13:00:00")),   # ayer 10:00 local
            ]
            for i, (prefix, total, fecha) in enumerate(ventas):
                db.add(Venta(
                    numero=f"DTZ-{prefix}-{sufijo}-{i}",
                    usuario_id=user.id, sucursal_id=1, estado="confirmada",
                    subtotal=total, total=total, fecha=fecha,
                ))
            db.commit()

            res = dash.resumen(db, user).data
            assert res["ventas_hoy"] == 3500.0, res["ventas_hoy"]
            assert res["cant_ventas_hoy"] == 2, res["cant_ventas_hoy"]
            assert res["ticket_promedio"] == 1750.0, res["ticket_promedio"]
            assert res["ventas_mes"] == 4000.0, res["ventas_mes"]
        finally:
            db.close()