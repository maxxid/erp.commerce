"""Tests del detalle de un medio de pago dentro de una sesión de caja.

El arqueo del cierre muestra un esperado por medio ("efectivo: $30.000") y el
operador necesita ver de qué se compone: apertura, ventas y egresos de esa
sesión. El detalle sale del mismo rango de movimientos con el que se calcula el
arqueo, así que sus totales tienen que coincidir con la fila que se está mirando
— y con la sesión correcta: pedir el detalle de la sesión de ayer no puede
devolver lo que se vendió hoy.
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
from app.services import caja_service as cs

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
            username=f"detalle_{sufijo}", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _uid(db):
    return db.query(Usuario).first().id


def _abrir(db, monto_inicial=20000.0, saldos_cuentas=None, hace_dias=0):
    apertura = cs.abrir_caja(
        db, monto_inicial, _uid(db),
        monto_retiro=0.0, saldos_cuentas=saldos_cuentas or {},
    )
    if hace_dias:
        apertura.created_at = datetime.now(UTC) - timedelta(days=hace_dias)
        db.commit()
    return apertura


def _vender(db, monto, medio, referencia_id=None):
    return cs.registrar_ingreso(
        db, monto, f"Venta {medio}", _uid(db),
        referencia_tipo="venta", referencia_id=referencia_id, medio_pago=medio,
    )


def _ultimo_cierre_id(db):
    cierre = (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.tipo == "cierre", MovimientoCaja.medio_pago.is_(None))
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
    return cierre.id


def _fila_arqueo(db, medio):
    resumen = cs.obtener_resumen_por_medio_pago(db)
    return next(f for f in resumen["por_medio"] if f["medio_pago"] == medio)


class TestSesionAbierta:
    def test_desglosa_apertura_y_ventas_con_los_totales_del_arqueo(self, db):
        _abrir(db, monto_inicial=20000.0)
        _vender(db, 10000.0, "efectivo")
        _vender(db, 5000.0, "debito")

        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo")

        assert detalle["apertura"] == 20000.0
        assert detalle["ingresos"] == 10000.0
        assert detalle["egresos"] == 0.0
        assert detalle["esperado"] == 30000.0

        assert [f["tipo"] for f in detalle["movimientos"]] == ["ingreso", "apertura"]
        assert [f["monto"] for f in detalle["movimientos"]] == [10000.0, 20000.0]

        fila = _fila_arqueo(db, "efectivo")
        assert detalle["apertura"] == fila["apertura"]
        assert detalle["ingresos"] == fila["ingresos"]
        assert detalle["esperado"] == fila["esperado"]

    def test_el_efectivo_no_se_leakkea_al_detalle_de_otro_medio(self, db):
        _abrir(db, monto_inicial=20000.0)
        _vender(db, 5000.0, "debito")

        detalle = cs.obtener_detalle_medio_sesion(db, "debito")

        assert detalle["apertura"] == 0.0
        assert detalle["ingresos"] == 5000.0
        assert all(f["tipo"] != "apertura" for f in detalle["movimientos"])
        assert [f["monto"] for f in detalle["movimientos"]] == [5000.0]

    def test_cuenta_digital_incluye_su_propia_apertura(self, db):
        _abrir(db, saldos_cuentas={"smartpoint": 5000.0})
        _vender(db, 2000.0, "smartpoint")

        detalle = cs.obtener_detalle_medio_sesion(db, "smartpoint")

        assert detalle["apertura"] == 5000.0
        assert detalle["ingresos"] == 2000.0
        assert detalle["esperado"] == 7000.0
        assert [f["tipo"] for f in detalle["movimientos"]] == ["ingreso", "apertura"]

    def test_el_egreso_de_la_sesion_baja_el_esperado(self, db):
        _abrir(db, monto_inicial=20000.0)
        cs.registrar_egreso(db, 1000.0, "Compra de insumos", _uid(db), medio_pago="efectivo")

        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo")

        assert detalle["egresos"] == 1000.0
        assert detalle["esperado"] == 19000.0
        assert [f["tipo"] for f in detalle["movimientos"]] == ["egreso", "apertura"]

    def test_un_egreso_de_otra_sesion_no_entra(self, db):
        _abrir(db, monto_inicial=20000.0)
        cs.registrar_egreso(
            db, 5000.0, "Extracción de la sesión anterior", _uid(db),
            referencia_tipo="retiro_cierre", referencia_id=999, medio_pago="efectivo",
        )

        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo")

        assert detalle["egresos"] == 0.0
        assert detalle["esperado"] == 20000.0
        assert all(f["tipo"] != "egreso" for f in detalle["movimientos"])

    def test_los_cierres_parciales_no_mueven_saldo_ni_aparecen(self, db):
        _abrir(db, monto_inicial=20000.0)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_metodo(db, "efectivo", 30000.0, _uid(db), comentario="conteo previo")

        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo")

        assert detalle["esperado"] == 30000.0
        assert [f["tipo"] for f in detalle["movimientos"]] == ["ingreso", "apertura"]

    def test_sin_caja_abierta_es_un_error(self, db):
        with pytest.raises(ValueError):
            cs.obtener_detalle_medio_sesion(db, "efectivo")


class TestSesionCerrada:
    def test_con_cierre_id_usa_los_movimientos_de_esa_sesion(self, db):
        _abrir(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        assert cs.cerrar_sesion_anterior_automaticamente(db) is True
        cierre_id = _ultimo_cierre_id(db)

        _abrir(db, monto_inicial=30000.0)
        _vender(db, 7000.0, "efectivo")

        cerrada = cs.obtener_detalle_medio_sesion(db, "efectivo", cierre_id=cierre_id)
        assert cerrada["apertura"] == 20000.0
        assert cerrada["ingresos"] == 10000.0
        assert cerrada["esperado"] == 30000.0
        assert [f["monto"] for f in cerrada["movimientos"]] == [10000.0, 20000.0]

        abierta = cs.obtener_detalle_medio_sesion(db, "efectivo")
        assert abierta["apertura"] == 30000.0
        assert abierta["ingresos"] == 7000.0
        assert abierta["esperado"] == 37000.0

    def test_los_totales_coinciden_con_el_arqueo_de_la_sesion(self, db):
        _abrir(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        assert cs.cerrar_sesion_anterior_automaticamente(db) is True
        cierre_id = _ultimo_cierre_id(db)

        _abrir(db, monto_inicial=30000.0)
        _vender(db, 500.0, "efectivo")

        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        fila = next(f for f in arqueo["por_medio"] if f["medio_pago"] == "efectivo")
        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo", cierre_id=cierre_id)

        assert detalle["apertura"] == fila["apertura"]
        assert detalle["ingresos"] == fila["ingresos"]
        assert detalle["egresos"] == fila["egresos"]
        assert detalle["esperado"] == fila["esperado"]

    def test_un_cierre_inexistente_es_un_error(self, db):
        _abrir(db)
        with pytest.raises(ValueError):
            cs.obtener_detalle_medio_sesion(db, "efectivo", cierre_id=99999)
