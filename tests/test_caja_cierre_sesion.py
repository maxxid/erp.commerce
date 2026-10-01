"""Tests del cierre de una sesión que el sistema cerró sola.

Cuando cambia el día, `cerrar_sesion_anterior_automaticamente()` registra el
cierre total de la jornada anterior con el monto que calculó el sistema. Ese
cierre no se podía completar: `cerrar_metodo()` y todo egreso exigen la caja
abierta, y el arqueo se calculaba "desde la última apertura", así que una sesión
ya cerrada no tenía saldos. El operador se quedaba con la opción de confirmar un
número suelto, sin arquear el cajón ni registrar la plata que se lleva.

Ahora el arqueo se calcula acotado a la sesión (entre su apertura y su cierre), así
que se puede completar aunque ya haya una caja nueva abierta, y la extracción de
dinero del cierre queda como egreso de esa sesión.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario, Sucursal
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
            username=f"caja_{sufijo}", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _abrir_jornada(db, monto_inicial=20000.0, saldos_cuentas=None, hace_dias=0):
    """Abre una caja y, opcionalmente, la deja con la fecha de otro día."""
    apertura = cs.abrir_caja(
        db, monto_inicial, db.query(Usuario).first().id,
        monto_retiro=0.0, saldos_cuentas=saldos_cuentas or {},
    )
    if hace_dias:
        apertura.created_at = datetime.now(UTC) - timedelta(days=hace_dias)
        db.commit()
    return apertura


def _vender(db, monto, medio):
    return cs.registrar_ingreso(
        db, monto, f"Venta {medio}", db.query(Usuario).first().id,
        referencia_tipo="venta", medio_pago=medio,
    )


def _fila(arqueo, medio):
    return next(f for f in arqueo["por_medio"] if f["medio_pago"] == medio)


class TestAutoCierre:
    def test_registra_el_cierre_de_la_jornada_anterior(self, db):
        _abrir_jornada(db, hace_dias=1)
        _vender(db, 10000.0, "efectivo")

        assert cs.cerrar_sesion_anterior_automaticamente(db) is True
        assert cs.caja_abierta(db) is False

        ultimo = cs.obtener_ultimo_cierre(db)
        assert ultimo["fue_automatico"] is True
        assert ultimo["monto"] == 30000.0

    def test_guarda_el_efectivo_del_cajon_para_la_apertura_siguiente(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, saldos_cuentas={"smartpoint": 5000.0}, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        _vender(db, 2000.0, "smartpoint")

        cs.cerrar_sesion_anterior_automaticamente(db)

        ultimo = cs.obtener_ultimo_cierre(db)
        # El total del cierre mezcla todas las cuentas, pero el cajón es solo el efectivo
        assert ultimo["monto"] == 37000.0
        assert ultimo["saldo_efectivo"] == 30000.0

    def test_el_cierre_auto_arranca_una_jornada_nueva(self, db):
        _abrir_jornada(db, hace_dias=1)
        cs.cerrar_sesion_anterior_automaticamente(db)

        cs.abrir_caja(db, 0.0, db.query(Usuario).first().id)
        assert cs.caja_abierta(db) is True


class TestArqueoDeSesionCerrada:
    def test_arquea_la_sesion_por_su_propio_arqueo(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, saldos_cuentas={"smartpoint": 5000.0}, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        _vender(db, 3000.0, "debito")
        _vender(db, 2000.0, "smartpoint")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = cs.obtener_ultimo_cierre(db) and db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first().id

        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)

        assert _fila(arqueo, "efectivo")["esperado"] == 30000.0
        assert _fila(arqueo, "debito")["esperado"] == 3000.0
        assert _fila(arqueo, "smartpoint")["esperado"] == 7000.0
        assert _fila(arqueo, "smartpoint")["es_cuenta_digital"] is True
        assert arqueo["saldo_esperado"] == 40000.0
        assert arqueo["saldo_efectivo_esperado"] == 30000.0
        assert arqueo["fue_automatico"] is True
        assert arqueo["confirmado"] is False

    def test_el_arqueo_no_toma_lo_que_paso_en_la_caja_nueva(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first().id

        # Se abre la caja de hoy y se vende
        cs.abrir_caja(db, 5000.0, db.query(Usuario).first().id)
        _vender(db, 77777.0, "efectivo")

        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        assert _fila(arqueo, "efectivo")["esperado"] == 30000.0
        # Y el saldo de la sesión abierta sigue siendo el de hoy
        assert cs.obtener_saldo_por_medio(db)["efectivo"]["esperado"] == 82777.0

    def test_rechaza_un_id_que_no_es_cierre_total(self, db):
        _abrir_jornada(db, hace_dias=1)
        venta_ingreso = _vender(db, 100.0, "efectivo")
        with pytest.raises(ValueError):
            cs.obtener_arqueo_sesion(db, venta_ingreso.id)


class TestExtraccionAlCerrar:
    def test_la_extraccion_descuenta_el_esperado_del_cajon(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()

        cs.registrar_retiro_cierre(db, 25000.0, "Retiro del dueño", db.query(Usuario).first().id, cierre_id=cierre.id)

        arqueo = cs.obtener_arqueo_sesion(db, cierre.id)
        assert _fila(arqueo, "efectivo")["esperado"] == 5000.0
        assert arqueo["total_retiros"] == 25000.0
        assert len(arqueo["retiros"]) == 1
        # El cierre deja de esperar 30000: ahora espera 5000, los que quedan en el cajón
        assert cierre.monto_esperado == 5000.0
        assert cierre.saldo_efectivo == 5000.0

    def test_queda_como_egreso_de_la_sesion(self, db):
        _abrir_jornada(db, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()

        cs.registrar_retiro_cierre(db, 8000.0, "Retiro del dueño", db.query(Usuario).first().id, cierre_id=cierre.id)

        egreso = db.query(_m.MovimientoCaja).filter(
            _m.MovimientoCaja.referencia_tipo == "retiro_cierre"
        ).one()
        assert egreso.tipo == "egreso"
        assert egreso.medio_pago == "efectivo"
        assert egreso.referencia_id == cierre.id
        assert "Retiro del dueño" in egreso.descripcion

    def test_borrar_la_extraccion_devuelve_el_esperado(self, db):
        _abrir_jornada(db, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()

        retiro = cs.registrar_retiro_cierre(db, 25000.0, "", db.query(Usuario).first().id, cierre_id=cierre.id)
        cs.eliminar_retiro_cierre(db, retiro.id)

        assert _fila(cs.obtener_arqueo_sesion(db, cierre.id), "efectivo")["esperado"] == 30000.0
        assert cierre.monto_esperado == 30000.0

    def test_no_acepta_montos_no_positivos(self, db):
        _abrir_jornada(db, hace_dias=1)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()

        with pytest.raises(ValueError):
            cs.registrar_retiro_cierre(db, 0.0, "", db.query(Usuario).first().id, cierre_id=cierre.id)

    def test_rechaza_un_medio_inexistente(self, db):
        _abrir_jornada(db, hace_dias=1)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()

        with pytest.raises(ValueError):
            cs.registrar_retiro_cierre(db, 100.0, "", db.query(Usuario).first().id,
                                       cierre_id=cierre.id, medio_pago="bitcoin")

    def test_sin_cierre_id_exige_la_caja_abierta(self, db):
        _abrir_jornada(db, hace_dias=1)
        cs.cerrar_sesion_anterior_automaticamente(db)

        with pytest.raises(ValueError):
            cs.registrar_retiro_cierre(db, 100.0, "", db.query(Usuario).first().id)


class TestArqueoPorMedioDeSesionCerrada:
    def _sesion_auto(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        _vender(db, 3000.0, "debito")
        cs.cerrar_sesion_anterior_automaticamente(db)
        return db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first().id

    def test_arquea_el_cajon_sin_caja_abierta(self, db):
        cierre_id = self._sesion_auto(db)
        assert cs.caja_abierta(db) is False

        mov, esperado, diferencia = cs.cerrar_metodo_sesion(
            db, cierre_id, "efectivo", 29500.0, db.query(Usuario).first().id,
        )

        assert esperado == 30000.0
        assert diferencia == -500.0
        assert mov.tipo == "cierre_parcial"
        assert mov.referencia_id == cierre_id

        fila = _fila(cs.obtener_arqueo_sesion(db, cierre_id), "efectivo")
        assert fila["cerrado"] is True
        assert fila["monto_real"] == 29500.0
        assert fila["diferencia"] == -500.0

    def test_rearquear_el_mismo_medio_corrige_en_vez_de_duplicar(self, db):
        cierre_id = self._sesion_auto(db)
        user_id = db.query(Usuario).first().id
        cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", 30000.0, user_id)

        mov, esperado, diferencia = cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", 29800.0, user_id)

        assert diferencia == -200.0
        parciales = db.query(_m.MovimientoCaja).filter(
            _m.MovimientoCaja.tipo == "cierre_parcial",
            _m.MovimientoCaja.medio_pago == "efectivo",
        ).all()
        assert len(parciales) == 1
        assert mov.monto == 29800.0

    def test_las_cuentas_digitales_se_cuadran_por_separado(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, saldos_cuentas={"mercadopago_qr": 12000.0}, hace_dias=1)
        _vender(db, 5000.0, "mercadopago_qr")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first().id
        user_id = db.query(Usuario).first().id

        cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", 20000.0, user_id)
        _, esperado_mp, dif_mp = cs.cerrar_metodo_sesion(db, cierre_id, "mercadopago_qr", 17000.0, user_id)

        # Que el cajón cuadre no compensa la diferencia de la cuenta
        assert esperado_mp == 17000.0
        assert dif_mp == 0.0

    def test_rechaza_un_medio_que_no_esta_en_el_arqueo(self, db):
        cierre_id = self._sesion_auto(db)
        with pytest.raises(ValueError):
            cs.cerrar_metodo_sesion(db, cierre_id, "smartpoint", 100.0, db.query(Usuario).first().id)

    def test_rechaza_monto_negativo(self, db):
        cierre_id = self._sesion_auto(db)
        with pytest.raises(ValueError):
            cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", -1.0, db.query(Usuario).first().id)


class TestSesionConciliadaNoSeToca:
    def _conciliada(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()
        cs.confirmar_cierre(db, cierre.id, 30000.0, db.query(Usuario).first().id)
        return cierre.id

    def test_el_arqueo_se_igual_sin_que_lo_bloquee(self, db):
        cierre_id = self._conciliada(db)
        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        assert arqueo["confirmado"] is True
        assert _fila(arqueo, "efectivo")["esperado"] == 30000.0

    def test_no_se_puede_arquear_otro_medio(self, db):
        cierre_id = self._conciliada(db)
        with pytest.raises(ValueError):
            cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", 30000.0, db.query(Usuario).first().id)

    def test_no_se_puede_registrar_una_extraccion(self, db):
        cierre_id = self._conciliada(db)
        with pytest.raises(ValueError):
            cs.registrar_retiro_cierre(db, 500.0, "", db.query(Usuario).first().id, cierre_id=cierre_id)


class TestConciliacionCompleta:
    """El recorrido que hace el operador: extraer, contar y conciliar la sesión de ayer."""

    def _sesion_de_ayer(self, db):
        _abrir_jornada(db, monto_inicial=20000.0, saldos_cuentas={"smartpoint": 5000.0}, hace_dias=1)
        _vender(db, 10000.0, "efectivo")
        _vender(db, 4000.0, "smartpoint")
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = db.query(
            _m.MovimientoCaja
        ).filter(_m.MovimientoCaja.tipo == "cierre").order_by(_m.MovimientoCaja.id.desc()).first()
        # Hoy ya se abrió una caja nueva y se vendió
        cs.abrir_caja(db, 5000.0, db.query(Usuario).first().id)
        _vender(db, 2000.0, "efectivo")
        return cierre

    def test_extraer_contar_y_conciliar_no_toca_la_caja_de_hoy(self, db):
        cierre = self._sesion_de_ayer(db)
        user_id = db.query(Usuario).first().id

        cs.registrar_retiro_cierre(db, 25000.0, "Retiro del dueño", user_id, cierre_id=cierre.id)
        cs.cerrar_metodo_sesion(db, cierre.id, "efectivo", 5000.0, user_id)
        cs.cerrar_metodo_sesion(db, cierre.id, "smartpoint", 9000.0, user_id)
        cs.confirmar_cierre(db, cierre.id, 14000.0, user_id, "Todo contado")

        assert cierre.monto_confirmado == 14000.0
        assert cierre.monto_esperado == 14000.0
        # La caja de hoy sigue con su propio saldo, sin nada de la sesión de ayer
        assert cs.caja_abierta(db) is True
        assert cs.obtener_saldo_por_medio(db)["efectivo"]["esperado"] == 7000.0

    def test_los_medios_pendientes_marcan_lo_que_falta_contar(self, db):
        cierre = self._sesion_de_ayer(db)
        user_id = db.query(Usuario).first().id

        assert set(cs.obtener_arqueo_sesion(db, cierre.id)["medios_pendientes"]) == {"efectivo", "smartpoint"}

        cs.cerrar_metodo_sesion(db, cierre.id, "smartpoint", 9000.0, user_id)
        assert cs.obtener_arqueo_sesion(db, cierre.id)["medios_pendientes"] == ["efectivo"]

    def test_la_extraccion_de_la_caja_abierta_va_al_resumen(self, db):
        _abrir_jornada(db, monto_inicial=20000.0)
        _vender(db, 10000.0, "efectivo")

        cs.registrar_retiro_cierre(db, 15000.0, "Fondo del día siguiente", db.query(Usuario).first().id)

        resumen = cs.obtener_resumen_por_medio_pago(db)
        assert resumen["total_retiros"] == 15000.0
        assert len(resumen["retiros"]) == 1
        assert resumen["saldo_efectivo"] == 15000.0

