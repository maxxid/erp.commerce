"""Corregir el medio de pago de una venta ya cobrada (decisión del dueño 20/10).

**El problema**: la cliente dijo que pagaba con SmartPoint, no pudo y terminó
en transferencia; el cajero ya había registrado la venta porque había más
gente esperando, y no había manera de corregirla. Sólo se hace la parte A
(cambiar el medio de pago). Lo otro —cambiar los ítems, el caso de la lata de
agua tónica comprada como gaseosa— queda planificado en PENDIENTES.

Lo que hay que cuidar acá: cambiar `Venta.medio_pago` y nada más deja la venta
diciendo una cosa y el arqueo de caja mostrando otra. Por eso la corrección
tiene que mover los ingresos que esa venta dejó en caja, y dejar la bandera
(`ventas.modificada_en`) más el evento de auditoría en "pendientes".

También quedan cubiertos dos bugs que aparecieron al tocar la pantalla de
ventas: los botones miraban `estado === 'Completada'` (el backend devuelve
`confirmada`, así que **ninguno** se rendereaba) y "Anular" no le pegaba al
backend: sólo cambiaba el estado en memoria y avisaba "Venta anulada".
"""

import pathlib
import re
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.models import Cliente, Sucursal, Usuario
from app.models.auditoria import Auditoria
from app.models.movimiento_caja import MovimientoCaja
from app.models.venta import Venta
from app.routers.ventas import CambiarMedioPago, cambiar_medio_pago
from app.services import caja_service as cs
from app.services import venta_service as vs

RAIZ = pathlib.Path(__file__).resolve().parents[1]
VENTAS_VIEW = RAIZ / "frontend" / "src" / "views" / "VentasView.vue"


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


def _abrir_caja(db):
    """La corrección exige caja abierta, así que casi todos los tests abren."""
    return cs.abrir_caja(db, 50000.0, _usuario(db).id)


def _venta(db, total=1000.0, medio="smartpoint", estado="confirmada",
           cliente_id=None, creada_hace_dias=0):
    venta = Venta(
        numero=f"V{db.query(Venta).count() + 1:05d}",
        usuario_id=_usuario(db).id,
        sucursal_id=1,
        cliente_id=cliente_id,
        subtotal=total,
        total=total,
        medio_pago=medio,
        estado=estado,
        fecha=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc) - timedelta(days=creada_hace_dias),
    )
    db.add(venta)
    db.commit()
    db.refresh(venta)
    return venta


def _ingreso(db, venta, medio, monto):
    """El ingreso que `confirmar_venta` deja en caja por esa venta."""
    mov = cs.registrar_ingreso(
        db, monto, f"Venta {venta.numero}", _usuario(db).id,
        referencia_tipo="venta", referencia_id=venta.id,
        sucursal_id=1, medio_pago=medio,
    )
    return mov


def _ingresos_de(db, venta):
    return (
        db.query(MovimientoCaja)
        .filter(
            MovimientoCaja.tipo == "ingreso",
            MovimientoCaja.referencia_tipo == "venta",
            MovimientoCaja.referencia_id == venta.id,
        )
        .order_by(MovimientoCaja.id)
        .all()
    )


class TestLaCajaSeAnotaEnElMedioNuevo:
    def test_el_ingreso_de_la_venta_se_mueve_al_medio_nuevo(self, db):
        _abrir_caja(db)
        venta = _venta(db, total=1000.0, medio="smartpoint")
        _ingreso(db, venta, "smartpoint", 1000.0)

        vs.cambiar_medio_pago(db, venta, "transferencia", _usuario(db).id)

        movimientos = _ingresos_de(db, venta)
        assert len(movimientos) == 1
        assert movimientos[0].medio_pago == "transferencia", (
            "si sólo se cambia Venta.medio_pago, el arqueo sigue mostrando "
            "la plata en el medio viejo"
        )
        assert movimientos[0].monto == 1000.0
        assert venta.medio_pago == "transferencia"

    def test_en_una_venta_mixta_solo_se_mueve_el_renglon_que_no_es_efectivo(self, db):
        _abrir_caja(db)
        venta = _venta(db, total=10000.0, medio="smartpoint")
        # El cajero cobró 3000 en efectivo y 7000 con SmartPoint.
        _ingreso(db, venta, "efectivo", 3000.0)
        _ingreso(db, venta, "smartpoint", 7000.0)

        vs.cambiar_medio_pago(db, venta, "transferencia", _usuario(db).id)

        por_medio = {m.medio_pago: m.monto for m in _ingresos_de(db, venta)}
        assert por_medio == {"efectivo": 3000.0, "transferencia": 7000.0}, (
            "los 3000 están en el cajón: no se mueven con el medio que se corrige"
        )

    def test_deja_la_bandera_de_venta_corregida(self, db):
        _abrir_caja(db)
        venta = _venta(db, medio="smartpoint")
        _ingreso(db, venta, "smartpoint", venta.total)
        assert venta.modificada_en is None

        vs.cambiar_medio_pago(db, venta, "efectivo", _usuario(db).id)

        assert venta.modificada_en is not None, (
            "es la bandera que se ve en la lista de ventas"
        )

    def test_no_se_puede_repetir_el_mismo_medio(self, db):
        _abrir_caja(db)
        venta = _venta(db, medio="transferencia")
        _ingreso(db, venta, "transferencia", venta.total)

        with pytest.raises(ValueError, match="ya tiene"):
            vs.cambiar_medio_pago(db, venta, "transferencia", _usuario(db).id)


class TestCuentaCorriente:
    def test_salir_de_cta_corriente_baja_la_deuda_y_pone_el_ingreso(self, db):
        _abrir_caja(db)
        cliente = Cliente(nombre="Kiosco de la esquina", saldo_cta_corriente=1000.0)
        db.add(cliente)
        db.commit()
        # La venta fue a cuenta corriente: nunca dejó ingreso en caja.
        venta = _venta(db, total=1000.0, medio="cta_corriente", cliente_id=cliente.id)

        vs.cambiar_medio_pago(db, venta, "transferencia", _usuario(db).id)

        db.refresh(cliente)
        assert cliente.saldo_cta_corriente == 0.0
        movimientos = _ingresos_de(db, venta)
        assert [(m.medio_pago, m.monto) for m in movimientos] == [("transferencia", 1000.0)]

    def test_pasar_a_cta_ctriente_quita_el_ingreso_y_suma_deuda(self, db):
        _abrir_caja(db)
        cliente = Cliente(nombre="Kiosco de la esquina")
        db.add(cliente)
        db.commit()
        venta = _venta(db, total=750.0, medio="efectivo", cliente_id=cliente.id)
        _ingreso(db, venta, "efectivo", 750.0)

        vs.cambiar_medio_pago(db, venta, "cta_corriente", _usuario(db).id)

        db.refresh(cliente)
        assert _ingresos_de(db, venta) == [], "la plata no entró: no puede quedar ingreso"
        assert cliente.saldo_cta_corriente == 750.0

    def test_no_pasa_a_cta_ctriente_si_la_venta_no_tiene_cliente(self, db):
        _abrir_caja(db)
        venta = _venta(db, medio="efectivo")
        _ingreso(db, venta, "efectivo", venta.total)

        with pytest.raises(ValueError, match="no tiene cliente"):
            vs.cambiar_medio_pago(db, venta, "cta_corriente", _usuario(db).id)

        assert _ingresos_de(db, venta), "falló antes de tocar nada: la caja queda igual"


class TestLoQueNoSePuedeCorregir:
    def test_sin_caja_abierta_no_deja_corregir(self, db):
        venta = _venta(db, medio="smartpoint")
        _ingreso(db, venta, "smartpoint", venta.total)

        with pytest.raises(ValueError, match="caja está cerrada"):
            vs.cambiar_medio_pago(db, venta, "efectivo", _usuario(db).id)

        assert _ingresos_de(db, venta)[0].medio_pago == "smartpoint"

    def test_no_corriges_ventas_de_otra_jornada(self, db):
        _abrir_caja(db)
        # Ventas de ayer: sus ingresos informan el arqueo de ese día cerrado.
        venta = _venta(db, medio="smartpoint", creada_hace_dias=1)
        mov = _ingreso(db, venta, "smartpoint", venta.total)
        mov.created_at = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

        with pytest.raises(ValueError, match="otra jornada"):
            vs.cambiar_medio_pago(db, venta, "efectivo", _usuario(db).id)

        assert _ingresos_de(db, venta)[0].medio_pago == "smartpoint"

    def test_no_corriges_una_venta_que_no_esta_cobrada(self, db):
        _abrir_caja(db)
        pendiente = _venta(db, medio="efectivo", estado="pendiente")
        anulada = _venta(db, medio="efectivo", estado="anulada")

        for venta in (pendiente, anulada):
            with pytest.raises(ValueError, match="cobradas"):
                vs.cambiar_medio_pago(db, venta, "transferencia", _usuario(db).id)
        assert venta.modificada_en is None

    def test_un_medio_que_no_existe_no_pasa(self, db):
        _abrir_caja(db)
        venta = _venta(db, medio="efectivo")
        _ingreso(db, venta, "efectivo", venta.total)

        with pytest.raises(ValueError, match="inválido"):
            vs.cambiar_medio_pago(db, venta, "cheque", _usuario(db).id)


class TestQuedaMarcadoParaRevision:
    def test_el_endpoint_deja_un_evento_pendiente_en_auditoria(self, db):
        _abrir_caja(db)
        venta = _venta(db, total=2400.0, medio="smartpoint")
        _ingreso(db, venta, "smartpoint", venta.total)

        respuesta = cambiar_medio_pago(
            venta.id, CambiarMedioPago(medio_pago="transferencia"), db, _usuario(db)
        )

        assert respuesta.data["medio_pago"] == "transferencia"
        assert respuesta.data["modificada_en"]
        assert "marcada para revisión" in respuesta.message

        evento = db.query(Auditoria).filter(Auditoria.tipo == "medio_pago_corregido").one()
        assert evento.venta_id == venta.id, "acá sí va el id de la venta: es FK a ventas.id"
        assert evento.venta_numero == venta.numero
        assert evento.estado == "sospechoso", (
            "sin eso no aparece en 'Pendientes' de Auditoría, que es donde la "
            "ve el administrador"
        )
        detalle = evento.detalle
        assert "smartpoint" in detalle and "transferencia" in detalle

    def test_un_medio_invalido_responde_con_error_y_no_deja_evento(self, db):
        _abrir_caja(db)
        venta = _venta(db, medio="smartpoint")
        _ingreso(db, venta, "smartpoint", venta.total)

        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            cambiar_medio_pago(
                venta.id, CambiarMedioPago(medio_pago="cheque"), db, _usuario(db)
            )

        assert exc.value.status_code == 400
        assert db.query(Auditoria).count() == 0


class TestLaPantallaDeVentas:
    """Dos bugs que aparecieron al agregar el botón de corregir."""

    def _texto(self):
        return VENTAS_VIEW.read_text(encoding="utf-8")

    def test_los_botones_miran_el_estado_que_de_verdad_devuelve_el_backend(self):
        texto = self._texto()

        assert "row.estado === 'Completada'" not in texto, (
            "el backend devuelve estado='confirmada': con 'Completada' no se "
            "rendereaba ni Anular, ni Facturar, ni Emitir, ni Editar — el dueño "
            "veía la lista y no había manera de tocar una venta"
        )
        assert "row.estado === 'confirmada'" in texto

    def test_anular_le_pega_al_backend(self):
        texto = self._texto()
        bloque = re.search(r"async function executeAnular\(\) \{.*?\n\}", texto, re.S)
        assert bloque, "desapareció executeAnular"
        cuerpo = bloque.group(0)

        assert "api.put" in cuerpo and "/anular" in cuerpo, (
            "antes sólo hacía `sale.estado = 'Anulada'` y avisaba 'Venta "
            "anulada': no anulaba nada (ni stock ni caja) y el filtro de la "
            "lista tampoco reconocía 'Anulada'"
        )
        assert "'Anulada'" not in cuerpo

    def test_el_boton_de_corregir_medio_esta_en_la_lista(self):
        texto = self._texto()

        assert "abrirCorreccion" in texto and "medio-pago" in texto
        assert "modificada_en" in texto, "falta la bandera en la lista"
