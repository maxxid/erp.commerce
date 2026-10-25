"""Réplica en vivo de la Fase G: si se frena, hay que enterarse hoy (25/10/2026).

La Fase G (ver `FASE_G_CONTINUIDAD.md`) consiste en que, si el servidor de
Oracle Cloud se cae, una segunda máquina restaure la base desde la réplica que
Litestream va subiendo a R2 y siga cobrando. Eso sólo funciona si la réplica
**sigue avanzando**: si Litestream se cayó hace dos días, el día de la caída la
secundaria restauraría una foto vieja y se perderían las ventas de esa
semana — el peor momento para enterarse.

Acá se cubre que:
- el chequeo de salud mire la réplica **cuando está prendida** en ese servidor
  (`LITESTREAM_HABILITADO`, que se pone en el unit file) y no la mire si no,
  para que una PC de desarrollo no mande alertas falsas;
- avise si no hay nada en la nube, si está configurada a medias, y si lleva
  más de `MAX_MIN_SIN_REPLICA` quieta (Litestream sube cada pocos segundos
  mientras la base cambia);
- la lista de archivos de la réplica **pagine**, igual que la de respaldos:
  mirar sólo la primera página de S3 fue el bug de alerta falsa del 24/10;
- el resumen diario muestre el estado de la réplica (es la única manera de
  saber que anda cuando todo está bien);
- la base trabaje en **WAL**, que es lo que Litestream necesita para replicar.
"""

import os
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.services import backup_service, config_service, licencia_service
from app.services import salud_service as ss

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PY = os.path.join(RAIZ, "app", "database.py")

TZ_AR = timezone(timedelta(hours=-3))
AHORA = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def _foreign_keys_on(conn, _recurso):
        conn.execute("PRAGMA foreign_keys=ON")

    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _con_replica(monkeypatch, fechas):
    """Finge la nube: R2 configurado y una réplica con esos últimos movimientos.

    `fechas` en UTC; la lista llega ordenada del más nuevo al más viejo, como
    la devuelve `listar_replica_r2`.
    """
    monkeypatch.setattr(settings, "LITESTREAM_HABILITADO", True)
    monkeypatch.setattr(backup_service, "_get_r2_config", lambda s: {"bucket": "b"})
    ordenadas = sorted(fechas, reverse=True)
    monkeypatch.setattr(
        backup_service, "listar_replica_r2",
        lambda s: [{"clave": f"replica/m/archivo{i}", "fecha": f.isoformat()}
                   for i, f in enumerate(ordenadas)],
    )


def test_sin_la_bandera_no_se_chequea_nada(db, monkeypatch):
    """Una máquina sin litestream instalado no tiene por qué quejarse."""
    monkeypatch.setattr(settings, "LITESTREAM_HABILITADO", False)
    monkeypatch.setattr(backup_service, "_get_r2_config",
                        lambda s: pytest.fail("No tendría que mirar la réplica"))

    assert ss.problemas_de_replica(db, AHORA) == []


def test_con_la_bandera_pero_sin_nube_lo_dice(db, monkeypatch):
    monkeypatch.setattr(settings, "LITESTREAM_HABILITADO", True)
    monkeypatch.setattr(backup_service, "_get_r2_config", lambda s: None)

    fallos = ss.problemas_de_replica(db, AHORA)

    assert len(fallos) == 1 and "R2" in fallos[0]


def test_la_replica_esta_viva_no_avisa(db, monkeypatch):
    _con_replica(monkeypatch, [AHORA - timedelta(seconds=8)])

    assert ss.problemas_de_replica(db, AHORA) == []


def test_la_replica_detenida_lo_avisa(db, monkeypatch):
    _con_replica(monkeypatch, [AHORA - timedelta(minutes=ss.MAX_MIN_SIN_REPLICA + 5)])

    fallos = ss.problemas_de_replica(db, AHORA)

    assert len(fallos) == 1 and "sin avanzar" in fallos[0]


def test_la_replica_recien_empezada_con_archivos_viejos_no_juerga(db, monkeypatch):
    """Dentro del margen no se avisa: de noche la base no cambia y lo único
    que garantiza movimiento es el snapshot periódico de Litestream."""
    _con_replica(monkeypatch, [AHORA - timedelta(minutes=ss.MAX_MIN_SIN_REPLICA - 10)])

    assert ss.problemas_de_replica(db, AHORA) == []


def test_la_replica_sin_archivos_lo_avisa(db, monkeypatch):
    _con_replica(monkeypatch, [])

    fallos = ss.problemas_de_replica(db, AHORA)

    assert len(fallos) == 1 and "ningún archivo" in fallos[0]


def test_el_chequeo_de_salud_tambien_mira_la_replica(db, monkeypatch):
    """El hook: un fallo de réplica tiene que terminar en el mismo aviso de
    Telegram que los respaldos, no quedarse callado en un return."""
    enviados = []
    monkeypatch.setattr(ss, "SessionLocal", lambda: db)
    monkeypatch.setattr(ss, "problemas_de_respaldo", lambda s, ahora: [])
    config_service.set_config(db, "telegram_bot_token", "123:test", "token de prueba")
    config_service.set_config(db, "telegram_chat_id", "-1001", "chat de prueba")

    def _falso_envio(token, chat_id, texto):
        enviados.append(texto)
        return True, "ok"

    monkeypatch.setattr(ss.avisos_service, "enviar_a_telegram", _falso_envio)
    _con_replica(monkeypatch, [AHORA - timedelta(minutes=90)])

    ss.chequear_salud(AHORA)

    assert len(enviados) == 1 and "réplica en vivo" in enviados[0]


def test_el_resumen_diario_muestra_la_replica(db, monkeypatch):
    _con_replica(monkeypatch, [AHORA - timedelta(seconds=20)])

    assert "Réplica en vivo" in ss.mensaje_resumen(db, AHORA)

    monkeypatch.setattr(settings, "LITESTREAM_HABILITADO", False)
    assert "Réplica en vivo" not in ss.mensaje_resumen(db, AHORA)


def test_la_lista_de_la_replica_pagina(db, monkeypatch):
    """S3 devuelve de a 1000 objetos por llamada. Con una sola página el
    chequeo se podía comer los archivos nuevos (mismo bug que el de los
    respaldos del 24/10/2026)."""
    class _Cliente:
        def __init__(self):
            self.llamadas = []

        def list_objects_v2(self, **params):
            self.llamadas.append(params)
            viejos = [
                {
                    "Key": f"replica/m/wal/{i}",
                    "LastModified": datetime(2026, 10, 24, tzinfo=timezone.utc) + timedelta(minutes=i),
                }
                for i in range(1000)
            ]
            nuevos = [
                {
                    "Key": f"replica/m/snap/{i}",
                    "LastModified": datetime(2026, 10, 25, 14, tzinfo=timezone.utc) + timedelta(minutes=i),
                }
                for i in range(5)
            ]
            if len(self.llamadas) == 1:
                return {"Contents": viejos, "IsTruncated": True, "NextContinuationToken": "p2"}
            return {"Contents": nuevos, "IsTruncated": False}

    cliente = _Cliente()
    monkeypatch.setattr(backup_service, "_get_r2_config", lambda s: {"bucket": "b"})
    monkeypatch.setattr(backup_service, "_make_r2_client", lambda cfg: cliente)
    monkeypatch.setattr(licencia_service, "obtener_machine_id", lambda: "m")

    lista = backup_service.listar_replica_r2(db)

    assert len(lista) == 1005, "Tendría que traer las dos páginas"
    assert cliente.llamadas[1].get("ContinuationToken") == "p2"
    assert cliente.llamadas[0].get("Prefix") == "replica/m/"
    assert lista[0]["fecha"].startswith("2026-10-25T14:04"), "Lo más nuevo tiene que quedar primero"


def test_la_base_trabaja_en_wal():
    """Litestream sólo puede replicar una base en WAL. Si sacan la línea de
    `app/database.py`, la réplica de la Fase G deja de andar sin que nadie
    lo note hasta el día de la caída."""
    from app.database import engine

    with open(DB_PY, encoding="utf-8") as fh:
        assert "PRAGMA journal_mode=WAL" in fh.read()

    with engine.connect() as conn:
        modo = conn.execute(text("PRAGMA journal_mode")).scalar()
    assert modo == "wal"
