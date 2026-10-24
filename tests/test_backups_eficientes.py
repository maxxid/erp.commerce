"""Respaldos livianos para un negocio con internet limitado (dueño, 24/10/2026).

**El pedido**: "no sé si hacer respaldos continuamente me sea eficiente, ya que
yo no necesito el último estado de hace 15 minutos para funcionar, necesito que
al final del día cuando vuelva oracle, las ventas se unan y poder conciliar el
día".

Hay que separar dos cosas que el pedido mezcla:

- **La cola offline** —las ventas del cajero que se suben apenas hay red— es la
  que hace que el día se concilie cuando vuelve el servidor. No depende de los
  respaldos y no cambió: cada venta se sube sola apenas puede.
- **El respaldo** sólo sirve ante una catástrofe (se perdió la máquina entera,
  se corrompió la base). Ahí importa cuánto se pierde.

Y acá se cubre que el gasto real, que es **lo que sale por el hotspot**, esté
dosificado: lo local corre en cada vuelta (archivo rotado, sin red) y la subida
a la nube queda una hora por vez. Subir cada 15 minutos serían ~33 MB por día
(≈ 1 GB por mes) para datos que sólo sirven el día que la máquina no vuelve.

También que el snapshot sea consistente: copiar el archivo de la base a mano
con el POS vendiendo en ese instante puede dejar una copia que no abre.
"""

import glob
import gzip
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.services import backup_service, config_service

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKUP_SVC = os.path.join(RAIZ, "app", "services", "backup_service.py")


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


@pytest.fixture
def backups_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(backup_service, "BACKUP_DIR", str(tmp_path / "backups"))
    return backup_service.BACKUP_DIR


def _base_real(ruta: str):
    conn = sqlite3.connect(ruta)
    conn.execute("CREATE TABLE ventas (id INTEGER PRIMARY KEY, total INTEGER)")
    conn.executemany("INSERT INTO ventas (total) VALUES (?)", [(100,), (250,), (75,)])
    conn.commit()
    conn.close()


def test_los_intervalos_son_15_min_locales_y_1_hora_la_nube():
    assert settings.BACKUP_INTERVAL_MIN == 15, "El respaldo local tiene que seguir cada 15 min"
    assert backup_service.SUBIR_A_R2_CADA_MIN == 60, (
        "La subida a la nube es lo que consume el hotspot: una hora por vez"
    )


def test_cada_vuelta_deja_un_respaldos_local(db, backups_dir, monkeypatch):
    base = os.path.join(os.path.dirname(backups_dir), "base.db")
    _base_real(base)
    subidas = []
    monkeypatch.setattr(backup_service, "_db_path", lambda: base)
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        backup_service, "subir_a_r2", lambda nombre, s: subidas.append(nombre) or True
    )

    backup_service.backup_automatico()

    assert len(glob.glob(os.path.join(backups_dir, "*.db.gz"))) == 1
    assert len(subidas) == 1, "La primera vuelta nunca subió nada: tiene que subir"


def test_la_subida_a_la_nube_es_una_vez_por_hora(db, monkeypatch):
    subidas = []
    monkeypatch.setattr(backup_service, "crear_backup_local", lambda: "respaldo.db.gz")
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        backup_service, "subir_a_r2", lambda nombre, s: subidas.append(nombre) or True
    )

    backup_service.backup_automatico()
    backup_service.backup_automatico()

    assert len(subidas) == 1, "Dos vueltas seguiditas no tienen que subir dos veces"

    # Pasó la hora → vuelve a subir.
    config_service.set_config(
        db, "backup_ultimo_upload_r2",
        (datetime.now(timezone.utc) - timedelta(hours=1, minutes=1)).isoformat(),
        "última subida vieja",
    )
    backup_service.backup_automatico()

    assert len(subidas) == 2
    cuando = datetime.fromisoformat(config_service.get_config(db, "backup_ultimo_upload_r2"))
    assert (datetime.now(timezone.utc) - cuando).total_seconds() < 3600, (
        "La hora se cuenta desde la subida buena, no desde el intento"
    )


def test_si_la_subida_falla_el_siguiente_vuelve_a_intentarlo(db, monkeypatch):
    intentos = []
    monkeypatch.setattr(backup_service, "crear_backup_local", lambda: "respaldo.db.gz")
    monkeypatch.setattr(backup_service, "SessionLocal", lambda: db)
    monkeypatch.setattr(
        backup_service, "subir_a_r2", lambda nombre, s: intentos.append(nombre) or False
    )

    backup_service.backup_automatico()
    backup_service.backup_automatico()

    assert len(intentos) == 2, (
        "Si la subida falló, la marca de hora no se anota y el próximo respaldo reintenta"
    )


def test_el_respaldos_local_es_un_snapshot_intacto(db, backups_dir, tmp_path, monkeypatch):
    base = os.path.join(str(tmp_path), "base.db")
    _base_real(base)
    monkeypatch.setattr(backup_service, "_db_path", lambda: base)

    nombre = backup_service.crear_backup_local()

    with gzip.open(os.path.join(backups_dir, nombre), "rb") as f:
        datos = f.read()
    leido = os.path.join(str(tmp_path), "leido.db")
    with open(leido, "wb") as f:
        f.write(datos)

    conn = sqlite3.connect(leido)
    filas = conn.execute("SELECT count(*), sum(total) FROM ventas").fetchone()
    conn.close()
    assert filas == (3, 425), "El respaldo tendría que tener la base entera, sin cortes"

    assert glob.glob(os.path.join(backups_dir, "*.part")) == [], (
        "No puede quedar el archivo a medias al lado de los respaldos"
    )


def test_el_respaldos_usa_el_snapshot_de_sqlite_y_no_copiar_el_archivo_a_manchas():
    # La diferencia entre las dos maneras es el candado: a mano se copia lo que
    # esté en disco en ese instante, que con el POS escribiendo puede ser la
    # base a mitad de una venta.
    with open(BACKUP_SVC, encoding="utf-8") as f:
        src = f.read()

    assert "origen.backup(destino)" in src, "El snapshot tendría que salir por el backup API de SQLite"
    assert 'sqlite3.connect(_db_path())' in src
