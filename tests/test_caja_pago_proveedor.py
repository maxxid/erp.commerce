"""Tests del pago a proveedor durante el cierre de caja.

El pago a proveedor es un egreso más de la sesión, pero tiene dos ids que
guardar: el proveedor y la sesión de cierre al que pertenece. Como
`referencia_id` es uno solo, la sesión va en su propia columna
(`sesion_cierre_id`). Eso hace fácil equivocarse en el resto del servicio, así
que lo que se prueba acá es sobre todo que el pago:

  - baje el esperado del medio del que salió el dinero,
  - aparezca en el arqueo junto a las extracciones, con su tipo,
  - no ensucie el saldo de la sesión abierta si pertenece a una ya cerrada,
  - se pueda anular y que eso revierta el esperado del cierre.

El caso que más importa es el del pago a una sesión ya cerrada: si el filtro de
los movimientos de sesión no mira `sesion_cierre_id`, el pago no entra en el
arqueo de esa sesión y el cierre queda con un total que no cuadra.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Usuario, Sucursal
from app.models.proveedor import Proveedor
import app.models as _m  # noqa: F401
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
            username=f"pp_{sufijo}", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.add(Proveedor(nombre=f"Distribuidora {sufijo}", activo=True))
        session.commit()
        yield session
    finally:
        session.close()


def _usuario(db):
    return db.query(Usuario).first().id


def _proveedor(db):
    return db.query(Proveedor).first()


def _abrir(db, monto=20000.0, hace_dias=0, saldos_cuentas=None):
    apertura = cs.abrir_caja(db, monto, _usuario(db), saldos_cuentas=saldos_cuentas or {})
    if hace_dias:
        apertura.created_at = datetime.now(UTC) - timedelta(days=hace_dias)
        db.commit()
    return apertura


def _vender(db, monto, medio="efectivo"):
    return cs.registrar_ingreso(
        db, monto, "Venta", _usuario(db), referencia_tipo="venta", medio_pago=medio,
    )


def _fila(arqueo, medio="efectivo"):
    return next(f for f in arqueo["por_medio"] if f["medio_pago"] == medio)


class TestPagoProveedorSesionAbierta:
    def test_baja_el_esperado_del_efectivo(self, db):
        _abrir(db)
        _vender(db, 10000.0)
        # Esperado: 20000 apertura + 10000 venta.
        _pagar(db, monto=4000.0, nombre="Lacteos del Sur")

        saldos = cs.obtener_saldo_por_medio(db)
        assert saldos["efectivo"]["egresos"] == 4000.0
        assert saldos["efectivo"]["esperado"] == 26000.0

    def test_se_registra_como_pago_y_no_como_extraccion(self, db):
        _abrir(db)
        mov = _pagar(db, monto=4000.0, nombre="Lacteos del Sur")

        assert mov.tipo == "egreso"
        assert mov.referencia_tipo == "pago_proveedor"
        assert mov.referencia_id == _proveedor(db).id
        # Sin cierre asignado: pertenece a la sesión abierta.
        assert mov.sesion_cierre_id is None
        # El nombre del proveedor queda copiado en la descripción, para que el
        # arqueo se lea sin joins.
        assert "Lacteos del Sur" in mov.descripcion

    def test_desde_que_cuenta_sale_el_dinero(self, db):
        _abrir(db, saldos_cuentas={"smartpoint": 10000.0})
        _vender(db, 5000.0, "smartpoint")
        cs.registrar_pago_proveedor(
            db, 1500.0, _usuario(db),
            proveedor_nombre="Lacteos del Sur",
            medio_pago="smartpoint",
        )

        saldos = cs.obtener_saldo_por_medio(db)
        assert saldos["smartpoint"]["egresos"] == 1500.0
        assert saldos["smartpoint"]["esperado"] == 13500.0
        # El pago salió de la cuenta, no del cajón.
        assert saldos["efectivo"]["esperado"] == 20000.0


class TestPagoProveedorSesionCerrada:
    def test_aparece_en_el_arqueo_de_la_sesion_cerrada(self, db):
        """El caso que rompe si el filtro de sesión no mira sesion_cierre_id."""
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        assert cs.cerrar_sesion_anterior_automaticamente(db) is True
        cierre_id = _ultimo_cierre(db).id

        cs.registrar_pago_proveedor(
            db, 3000.0, _usuario(db),
            proveedor_id=_proveedor(db).id,
            proveedor_nombre="Lacteos del Sur",
            cierre_id=cierre_id,
        )

        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        # El pago tiene que estar en la lista, con su tipo y su id de proveedor.
        pagos = [r for r in arqueo["retiros"] if r["tipo"] == "pago_proveedor"]
        assert len(pagos) == 1
        assert pagos[0]["monto"] == 3000.0
        assert pagos[0]["proveedor_id"] == _proveedor(db).id
        # Y tiene que haber bajado el esperado de esa sesión.
        assert _fila(arqueo)["esperado"] == 27000.0

    def test_no_grava_el_saldo_de_la_caja_nueva(self, db):
        """La caja ya se abrió con lo que quedó de ayer: el pago de ayer no
        puede descontarse de hoy otra vez."""
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = _ultimo_cierre(db).id

        # Hoy se abre una caja nueva con el efectivo que quedó.
        _abrir(db, monto=27000.0)
        cs.registrar_pago_proveedor(
            db, 3000.0, _usuario(db), proveedor_nombre="Lacteos del Sur",
            cierre_id=cierre_id,
        )

        saldos = cs.obtener_saldo_por_medio(db)
        assert saldos["efectivo"]["egresos"] == 0.0
        assert saldos["efectivo"]["esperado"] == 27000.0

    def test_recalcula_el_total_del_cierre(self, db):
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = _ultimo_cierre(db)
        total_antes = cierre.monto_esperado

        cs.registrar_pago_proveedor(
            db, 3000.0, _usuario(db), proveedor_nombre="Lacteos del Sur",
            cierre_id=cierre.id,
        )
        db.refresh(cierre)
        assert cierre.monto_esperado == total_antes - 3000.0

    def test_convive_con_una_extraccion_en_la_misma_lista(self, db):
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = _ultimo_cierre(db).id

        cs.registrar_retiro_cierre(db, 2000.0, "a la caja fuerte", _usuario(db), cierre_id=cierre_id)
        cs.registrar_pago_proveedor(
            db, 3000.0, _usuario(db),
            proveedor_id=_proveedor(db).id,
            proveedor_nombre="Lacteos del Sur",
            cierre_id=cierre_id,
        )
        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        tipos = sorted(r["tipo"] for r in arqueo["retiros"])
        assert tipos == ["pago_proveedor", "retiro_cierre"]
        # Los dos son egresos del efectivo: 10000 de venta - 5000.
        assert _fila(arqueo)["esperado"] == 25000.0
        assert arqueo["total_retiros"] == 5000.0

    def test_no_se_puede_tocar_una_sesion_ya_conciliada(self, db):
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = _ultimo_cierre(db).id
        cs.confirmar_cierre(db, cierre_id, 30000.0, _usuario(db))

        with pytest.raises(ValueError, match="conciliado"):
            cs.registrar_pago_proveedor(
                db, 3000.0, _usuario(db), proveedor_nombre="Lacteos", cierre_id=cierre_id,
            )

    def test_el_arqueo_de_un_medio_no_aparece_como_egreso(self, db):
        """Un cierre_parcial también apunta al cierre, pero no es plata que sale.

        Comparte referencia_id con los egresos de cierre, así que la lista de
        egresos del arqueo no puede armarse solo por ese id.
        """
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre_id = _ultimo_cierre(db).id
        cs.cerrar_metodo_sesion(db, cierre_id, "efectivo", 30000.0, _usuario(db))

        arqueo = cs.obtener_arqueo_sesion(db, cierre_id)
        assert arqueo["total_retiros"] == 0.0
        assert arqueo["retiros"] == []


class TestAnularPagoProveedor:
    def test_anular_revierte_el_esperado_del_cierre(self, db):
        _abrir(db, hace_dias=1)
        _vender(db, 10000.0)
        cs.cerrar_sesion_anterior_automaticamente(db)
        cierre = _ultimo_cierre(db)

        mov = cs.registrar_pago_proveedor(
            db, 3000.0, _usuario(db), proveedor_nombre="Lacteos", cierre_id=cierre.id,
        )
        db.refresh(cierre)
        esperado_con_pago = cierre.monto_esperado

        cs.eliminar_pago_proveedor(db, mov.id)
        db.refresh(cierre)
        assert cierre.monto_esperado == esperado_con_pago + 3000.0
        arqueo = cs.obtener_arqueo_sesion(db, cierre.id)
        assert [r for r in arqueo["retiros"] if r["tipo"] == "pago_proveedor"] == []

    def test_no_deja_borrar_una_extraccion_por_esta_via(self, db):
        _abrir(db)
        retiro = cs.registrar_retiro_cierre(db, 2000.0, "a la caja fuerte", _usuario(db))
        with pytest.raises(ValueError, match="no existe"):
            cs.eliminar_pago_proveedor(db, retiro.id)


class TestValidaciones:
    def test_exige_proveedor_o_nombre(self, db):
        _abrir(db)
        with pytest.raises(ValueError, match="proveedor"):
            cs.registrar_pago_proveedor(db, 1000.0, _usuario(db))

    def test_rechaza_monto_cero(self, db):
        _abrir(db)
        with pytest.raises(ValueError, match="mayor a 0"):
            cs.registrar_pago_proveedor(db, 0, _usuario(db), proveedor_nombre="X")

    def test_rechaza_medio_de_pago_invalido(self, db):
        _abrir(db)
        with pytest.raises(ValueError, match="inválido"):
            cs.registrar_pago_proveedor(
                db, 1000.0, _usuario(db), proveedor_nombre="X", medio_pago="bitcoin",
            )

    def test_exige_caja_abienda_sin_cierre_id(self, db):
        with pytest.raises(ValueError, match="caja abierta"):
            cs.registrar_pago_proveedor(db, 1000.0, _usuario(db), proveedor_nombre="X")


# --- helpers ---


def _pagar(db, monto, nombre):
    return cs.registrar_pago_proveedor(
        db, monto, _usuario(db),
        proveedor_id=_proveedor(db).id,
        proveedor_nombre=nombre,
    )


def _ultimo_cierre(db):
    from app.models.movimiento_caja import MovimientoCaja
    return (
        db.query(MovimientoCaja)
        .filter(MovimientoCaja.tipo == "cierre", MovimientoCaja.medio_pago == None)
        .order_by(MovimientoCaja.id.desc())
        .first()
    )
