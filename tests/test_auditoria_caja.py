"""`auditoria.venta_id` es clave foránea hacia `ventas.id`, y en la caja le
metían ids de movimientos de caja.

Producción, 20/10/2026 13:20: `DELETE /api/caja/retiro-cierre/672` respondió
500 con `sqlite3.IntegrityError: FOREIGN KEY constraint failed`. La extracción
se había borrado igual — el `commit` del servicio va **antes** de escribir la
auditoría — así que el dueño veía un error sin saber si había salido o no, y si
reintentaba le respondían "La extracción no existe".

El bug no se veía en las otras suites porque sus fixtures crean el engine sin
`PRAGMA foreign_keys=ON`; acá se prende igual que en `app/database.py`.
"""

import json
import pathlib
import re

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.models import Sucursal, Usuario
from app.models.auditoria import Auditoria
from app.models.movimiento_caja import MovimientoCaja
from app.routers.caja import RetiroCierreRequest, borrar_retiro_cierre, retiro_cierre
from app.services import caja_service as cs

ARCHIVO_CAJA = pathlib.Path(__file__).resolve().parents[1] / "app" / "routers" / "caja.py"
LLAMADA = "auditoria_service.registrar("


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
            username="auditoria_caja", nombre="Cajero", password_hash="x",
            rol="admin", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _usuario(db):
    return db.query(Usuario).first()


def _argumentos(texto: str, desde: int) -> list:
    """Argumentos de la llamada que empieza en `desde`, separando sólo las comas
    de nivel cero: las que están adentro de un dict o de otro llamado no cuentan."""
    args, actual, prof = [], "", 0
    for ch in texto[desde + len(LLAMADA):]:
        if ch == "," and prof == 0:
            args.append(actual.strip())
            actual = ""
            continue
        if ch in ")]}" and prof == 0:
            args.append(actual.strip())
            return args
        if ch in "([{":
            prof += 1
        elif ch in ")]}":
            prof -= 1
        actual += ch
    raise AssertionError("la llamada nunca cerró el paréntesis")


class TestVentaIdNoEsUnIdDeCaja:
    def test_borrar_una_extraccion_no_tira_500_por_falta_de_venta(self, db):
        user = _usuario(db)
        cs.abrir_caja(db, 20000.0, user.id)
        mov = cs.registrar_retiro_cierre(db, 5000.0, "cambio de chico", user.id)
        retiro_id = mov.id

        # Antes del arreglo esto terminaba en IntegrityError y el 500 **con la
        # extracción ya borrada**: el cliente no sabía qué había pasado.
        borrar_retiro_cierre(retiro_id, db, user)

        assert db.query(MovimientoCaja).filter(MovimientoCaja.id == retiro_id).first() is None
        evento = db.query(Auditoria).filter(Auditoria.tipo == "borrar_retiro_cierre_caja").one()
        assert evento.venta_id is None, "venta_id solo puede apuntar a ventas.id"
        assert json.loads(evento.detalle)["retiro_id"] == retiro_id

    def test_cargar_una_extraccion_guarda_el_id_en_detalle(self, db):
        user = _usuario(db)
        cs.abrir_caja(db, 20000.0, user.id)

        retiro_cierre(RetiroCierreRequest(monto=1000.0, motivo="cambio"), db, user)

        mov = db.query(MovimientoCaja).filter(
            MovimientoCaja.tipo == "egreso",
            MovimientoCaja.referencia_tipo == "retiro_cierre",
        ).one()
        evento = db.query(Auditoria).filter(Auditoria.tipo == "retiro_cierre_caja").one()
        assert evento.venta_id is None
        assert json.loads(evento.detalle)["movimiento_id"] == mov.id

    def test_en_caja_ninguna_auditoria_le_pasa_un_id_de_movimiento(self):
        texto = ARCHIVO_CAJA.read_text(encoding="utf-8")
        fuera_de_lugar = []

        for m in re.finditer(re.escape(LLAMADA), texto):
            args = _argumentos(texto, m.start())
            venta_id = args[3] if len(args) > 3 else "?"
            if venta_id != "None":
                linea = texto[: m.start()].count("\n") + 1
                fuera_de_lugar.append(f"línea {linea}: {args[2]} → {venta_id}")

        assert not fuera_de_lugar, (
            "venta_id es clave foránea a ventas.id: en la caja solo puede ir "
            "None y el id del movimiento va en detalle, si no el endpoint "
            "responde 500 cuando no existe una venta con ese número → "
            + ", ".join(fuera_de_lugar)
        )
