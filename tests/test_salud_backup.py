"""Respaldos que se hacen, se abren y avisan (dueño: "hacemos las notificaciones").

**El problema real**: el sistema ya tenía respaldos automáticos + subida a R2,
pero `BACKUP_INTERVAL_MIN` estaba en 0, o sea **apagado**: en el servidor sólo
había dos archivos, manuales, del 28/6 y del 9/10. Un respaldo que no se hace
no existe, y uno que no se puede abrir tampoco — las dos cosas se descubren
justo el día que menos sobra.

Acá se cubre que:
- el respaldo automático esté **prendido por defecto** (cada 15 minutos);
- el chequeo avise si no hay respaldo fresco (< 24 h), si el .gz no abre
  (integrity_check adentro) y si R2 está configurado pero no sube;
- el aviso **no se repita** cada vuelta (guarda de 12 h por tipo);
- haya un resumen diario "todo bien", que es la única manera de saber que el
  canal de avisos anda — si nadie recibe ese mensaje, nadie va a recibir la
  alerta de una caída tampoco;
- sin Telegram configurado no se rompa nada (el chequeo corre y queda en el log).
"""

import gzip
import os
import shutil
import sqlite3
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.config import settings
from app.database import Base as _Base
import app.models  # noqa: F401  registra todos los modelos en Base
from app.models.configuracion import Configuracion
from app.services import backup_service, config_service
from app.services import salud_service as ss

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MAIN_PY = os.path.join(RAIZ, "app", "main.py")
AJUSTES = os.path.join(RAIZ, "frontend", "src", "views", "AjustesView.vue")

TZ_AR = timezone(timedelta(hours=-3))


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


def _base_chiquita(ruta: str):
    conn = sqlite3.connect(ruta)
    conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, x TEXT)")
    conn.execute("INSERT INTO t (x) VALUES ('hola')")
    conn.commit()
    conn.close()


def _respaldo(nombre: str, hace_h: float = 0, basura: bool = False):
    """Escribe un .gz válido, o un archivo con el mismo nombre pero basura
    adentro (que es lo que pasa cuando una descarga queda a medias)."""
    os.makedirs(backup_service.BACKUP_DIR, exist_ok=True)
    origen = os.path.join(backup_service.BACKUP_DIR, "base.db")
    _base_chiquita(origen)
    destino = os.path.join(backup_service.BACKUP_DIR, nombre)
    if basura:
        with open(destino, "wb") as dst:
            dst.write(b"esto no es una base de datos")
    else:
        with open(origen, "rb") as src, gzip.open(destino, "wb") as dst:
            shutil.copyfileobj(src, dst)
    os.remove(origen)
    if hace_h:
        viejo = (datetime.now(timezone.utc) - timedelta(hours=hace_h)).timestamp()
        os.utime(destino, (viejo, viejo))
    return destino


def _telegram(monkeypatch, db, enviados):
    config_service.set_config(db, "telegram_bot_token", "123:test", "token de prueba")
    config_service.set_config(db, "telegram_chat_id", "-1001", "chat de prueba")

    def _falso_envio(token, chat_id, texto):
        enviados.append(texto)
        return True, "Mensaje enviado"

    monkeypatch.setattr(ss.avisos_service, "enviar_a_telegram", _falso_envio)


def test_el_respaldo_automatico_esta_prendido_por_defecto():
    assert settings.BACKUP_INTERVAL_MIN == 15, (
        "Si vuelve a 0, el servidor deja de respaldar y nadie se entera"
    )


def test_sin_respaldos_lo_avisa(db, backups_dir):
    fallos = ss.problemas_de_respaldo(db, datetime.now(timezone.utc))
    assert "No hay ningún respaldo local." in fallos


def test_respaldos_frescos_y_sanos_no_avisan(db, backups_dir):
    _respaldo("erp_comercio_20261023_210000.db.gz")

    assert ss.problemas_de_respaldo(db, datetime.now(timezone.utc)) == []


def test_respaldos_viejos_lo_avisan(db, backups_dir):
    _respaldo("erp_comercio_20261021_210000.db.gz", hace_h=30)

    fallos = ss.problemas_de_respaldo(db, datetime.now(timezone.utc))

    assert any("30 h" in f for f in fallos), fallos


def test_respaldos_corruptos_lo_avisan(db, backups_dir):
    # Un .gz que se descarga a medias: el archivo existe y parece recién
    # hecho, pero no sirve para nada.
    _respaldo("erp_comercio_20261023_210000.db.gz", basura=True)

    fallos = ss.problemas_de_respaldo(db, datetime.now(timezone.utc))

    assert any("dañada" in f for f in fallos), fallos


def test_r2_configurado_sin_respaldos_lo_avisan(db, backups_dir, monkeypatch):
    _respaldo("erp_comercio_20261023_210000.db.gz")
    monkeypatch.setattr(backup_service, "_get_r2_config", lambda s: {"bucket": "b"})
    monkeypatch.setattr(backup_service, "listar_backups_r2", lambda s: [])

    fallos = ss.problemas_de_respaldo(db, datetime.now(timezone.utc))

    assert any("nube (R2)" in f for f in fallos), fallos


def test_el_aviso_no_se_repite_cada_vuelta(db, backups_dir, monkeypatch):
    _respaldo("erp_comercio_20261021_210000.db.gz", hace_h=30)
    enviados = []
    _telegram(monkeypatch, db, enviados)
    monkeypatch.setattr(ss, "SessionLocal", lambda: db)

    ss.chequear_salud()
    ss.chequear_salud()

    assert len(enviados) == 1, "La guarda de 12 h tendría que frenar el segundo aviso"
    assert "respaldos" in enviados[0]


def test_el_resumen_diario_es_una_vez_por_dia(db, backups_dir, monkeypatch):
    _respaldo("erp_comercio_20261023_210000.db.gz")
    enviados = []
    _telegram(monkeypatch, db, enviados)
    monkeypatch.setattr(ss, "SessionLocal", lambda: db)

    mañana = datetime.now(timezone.utc).astimezone(TZ_AR).replace(hour=10, minute=0)
    ss.chequear_salud(ahora=mañana.astimezone(timezone.utc))
    assert enviados == [], "Antes de la hora del resumen no se manda nada"

    tarde = datetime.now(timezone.utc).astimezone(TZ_AR).replace(hour=21, minute=5)
    ss.chequear_salud(ahora=tarde.astimezone(timezone.utc))
    ss.chequear_salud(ahora=tarde.astimezone(timezone.utc))

    assert len(enviados) == 1, "El 'todo bien' del día tiene que salir una sola vez"
    assert "todo bien" in enviados[0]
    assert "Último respaldo" in enviados[0]


def test_se_puede_apagar_el_resumen_diario(db, backups_dir, monkeypatch):
    _respaldo("erp_comercio_20261023_210000.db.gz")
    enviados = []
    _telegram(monkeypatch, db, enviados)
    monkeypatch.setattr(ss, "SessionLocal", lambda: db)
    config_service.set_config(db, "alerta_resumen_diario", "false", "prueba")

    tarde = datetime.now(timezone.utc).astimezone(TZ_AR).replace(hour=21, minute=5)
    ss.chequear_salud(ahora=tarde.astimezone(timezone.utc))

    assert enviados == []


def test_sin_telegram_no_se_rompe_nada(db, backups_dir, monkeypatch):
    monkeypatch.setattr(ss, "SessionLocal", lambda: db)

    ss.chequear_salud()  # sin respaldos y sin token: no manda nada y no lanza


def test_el_servicio_arranca_el_chequeo_y_las_ui_saben_de_el():
    with open(MAIN_PY, encoding="utf-8") as f:
        main_src = f.read()
    assert "_start_salud_scheduler()" in main_src
    assert "chequear_salud" in main_src

    with open(AJUSTES, encoding="utf-8") as f:
        ajustes = f.read()
    assert "alerta_resumen_diario" in ajustes
