"""Egresos que no salen de ninguna caja.

El dueño paga cosas con plata suya: un pago particular, la paga patronal, un
giro desde su cuenta. Ese dinero nunca estuvo en el cajón ni en las cuentas del
negocio. Si se registra como un egreso más, el sistema lo resta del esperado y
el cajero cierra la caja con una diferencia que no se explica: la plata nunca
fue de la caja.

Por eso el movimiento lleva un flag (`afecta_caja`). Sigue apareciendo en el
historial y se puede auditar, pero no baja el esperado de ningún medio. Lo que
se prueba acá es que ningún cálculo de saldos se lo trate como egreso de verdad,
ni que el flag se pierda en el camino entre el form y la base.
"""

import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario, Sucursal
import app.models as _m  # noqa: F401
from app.database import Base as _Base
from app.services import caja_service as cs

RAIZ = Path(__file__).resolve().parent.parent
VISTA_CAJA = RAIZ / "frontend" / "src" / "views" / "CajaView.vue"
ROUTER_CAJA = RAIZ / "app" / "routers" / "caja.py"


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
            username=f"ext_{sufijo}", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _usuario(db):
    return db.query(Usuario).first().id


def _abrir(db, monto=20000.0):
    return cs.abrir_caja(db, monto, _usuario(db), saldos_cuentas={})


def _vender(db, monto):
    return cs.registrar_ingreso(
        db, monto, "Venta", _usuario(db), referencia_tipo="venta", medio_pago="efectivo",
    )


def _egreso(db, monto, afecta_caja=True):
    return cs.registrar_egreso(
        db, monto, "Pago", _usuario(db), medio_pago="efectivo", afecta_caja=afecta_caja,
    )


class TestSaldos:
    def test_el_pago_particular_no_baja_el_esperado(self, db):
        _abrir(db, 20000)
        _vender(db, 10000)
        _egreso(db, 5000, afecta_caja=False)

        saldos = cs.obtener_saldo_por_medio(db)

        assert saldos["efectivo"]["egresos"] == 0
        assert saldos["efectivo"]["esperado"] == 30000

    def test_el_egreso_comun_sigue_restando(self, db):
        """Si el filtro se aplicara a todos los egresos, la caja cerraría con
        plata de más y la diferencia aparecería recién al contar el cajón."""
        _abrir(db, 20000)
        _vender(db, 10000)
        _egreso(db, 5000, afecta_caja=True)

        saldos = cs.obtener_saldo_por_medio(db)

        assert saldos["efectivo"]["egresos"] == 5000
        assert saldos["efectivo"]["esperado"] == 25000

    def test_los_dos_tipos_de_egreso_conviven_en_la_misma_sesion(self, db):
        _abrir(db, 20000)
        _vender(db, 10000)
        _egreso(db, 5000, afecta_caja=False)
        _egreso(db, 3000, afecta_caja=True)

        saldos = cs.obtener_saldo_por_medio(db)

        assert saldos["efectivo"]["egresos"] == 3000
        assert saldos["efectivo"]["esperado"] == 27000

    def test_el_resumen_del_dia_no_lo_suma(self, db):
        _abrir(db, 20000)
        _vender(db, 10000)
        _egreso(db, 5000, afecta_caja=False)
        _egreso(db, 3000, afecta_caja=True)

        resumen = cs.obtener_resumen_por_medio_pago(db)

        assert resumen["total_egresos"] == 3000
        assert resumen["saldo_efectivo"] == 27000

    def test_el_detalle_del_medio_no_lo_muestra(self, db):
        """El detalle por medio es lo que el cajero mira para explicar cada
        peso del esperado: un renglón ahí que no mueve el saldo solo genera la
        pregunta de por qué el total no coincide con la suma."""
        _abrir(db, 20000)
        externo = _egreso(db, 5000, afecta_caja=False)
        _egreso(db, 3000, afecta_caja=True)

        detalle = cs.obtener_detalle_medio_sesion(db, "efectivo")

        assert detalle["egresos"] == 3000
        assert externo.id not in [f["id"] for f in detalle["movimientos"]]


class TestHistorial:
    def test_el_pago_particular_sigue_visible(self, db):
        """No restar no es no registrar: la plata tiene que poder rastrearse."""
        _abrir(db, 20000)
        externo = _egreso(db, 5000, afecta_caja=False)

        movs, total = cs.listar_movimientos(db)

        assert total >= 2
        fila = next(m for m in movs if m.id == externo.id)
        assert fila.afecta_caja is False


def test_el_form_de_egreso_manda_la_marca():
    """Sin esto el flag vive solo en la base: el form lo pinta pero nunca lo
    manda, y todo egreso sigue restando."""
    texto = VISTA_CAJA.read_text(encoding="utf-8")

    assert "body.afecta_caja" in texto, "el form de egreso no manda la marca al backend"
    assert "m.afecta_caja === false" in texto, "la tabla no marca el egreso externo"
    assert "OPCIONES_AFECTA_CAJA" in texto, "no se puede elegir si sale de una caja"


def test_el_endpoint_recibe_y_guarda_la_marca():
    texto = ROUTER_CAJA.read_text(encoding="utf-8")

    assert "afecta_caja: bool = Field(" in texto, "el request del egreso no acepta la marca"
    assert "afecta_caja=data.afecta_caja" in texto, "el router no manda la marca al servicio"
    assert '"afecta_caja": data.afecta_caja' in texto, "la auditoría no guarda si salió de caja"
