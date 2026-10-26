"""Parametrización multi-cliente (Docker multi-instance).

Lo que se prueba acá es lo que hace que una instancia pueda venderse como
"cliente N" sin tocar código: machine_id fijo, respaldos en un volumen,
licencia que no se auto-renueva, gestión de licencias bloqueada y un admin
inicial con clave propia.
"""

import importlib
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.auth.security import verificar_password
from app.config import settings
from app.database import Base as _Base
from app.models import Licencia, Usuario
from app.routers import licencia as router_licencia
from app.services import licencia_service


def _engine_memoria():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    return engine


@pytest.fixture
def db():
    engine = _engine_memoria()
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _usuario(db, rol="admin"):
    user = Usuario(
        username=f"u{uuid.uuid4().hex[:8]}",
        password_hash="x",
        nombre="Test",
        rol=rol,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestMachineId:
    def test_machine_id_fijado_por_entorno(self, monkeypatch):
        monkeypatch.setattr(settings, "MACHINE_ID", "cliente1")
        assert licencia_service.obtener_machine_id() == "cliente1"

    def test_licencia_secret_maestro_gana_al_jwt(self, monkeypatch):
        exp = datetime.now(timezone.utc) + timedelta(days=30)

        monkeypatch.setattr(settings, "JWT_SECRET", "jwt-del-cliente-1")
        monkeypatch.setattr(settings, "LICENCIA_SECRET", "secreto-maestro")
        clave = licencia_service.generar_clave("Cliente", "cliente1", exp)

        # Otra instancia: distinto JWT_SECRET, mismo secreto maestro.
        monkeypatch.setattr(settings, "JWT_SECRET", "jwt-del-cliente-2")
        assert licencia_service.validar_clave("Cliente", "cliente1", exp, clave)

        # Sin secreto maestro vuelve a firmar con el JWT de la instancia.
        monkeypatch.setattr(settings, "LICENCIA_SECRET", "")
        assert not licencia_service.validar_clave("Cliente", "cliente1", exp, clave)


class TestBackupDir:
    def test_backup_dir_por_entorno(self, monkeypatch, tmp_path):
        from app.services import backup_service

        monkeypatch.setattr(settings, "BACKUP_DIR", str(tmp_path))
        try:
            importlib.reload(backup_service)
            assert backup_service.BACKUP_DIR == str(tmp_path)
        finally:
            monkeypatch.setattr(settings, "BACKUP_DIR", "")
            importlib.reload(backup_service)

    def test_backup_dir_por_defecto_es_la_del_repo(self, monkeypatch):
        from app.services import backup_service

        monkeypatch.setattr(settings, "BACKUP_DIR", "")
        importlib.reload(backup_service)

        esperado = os.path.join(os.path.dirname(os.path.dirname(__file__)), "backups")
        assert backup_service.BACKUP_DIR == esperado


class TestGestionDeLicencias:
    def test_generar_esta_deshabilitado_en_un_cliente(self, db, monkeypatch):
        monkeypatch.setattr(settings, "LICENCIA_GESTION_LOCAL", False)
        data = router_licencia.GenerarRequest(
            cliente="Cliente", machine_id="cliente1", dias=30, plan="trial"
        )

        with pytest.raises(HTTPException) as exc:
            router_licencia.generar(data, db, _usuario(db))

        assert exc.value.status_code == 403

    def test_toggle_esta_deshabilitado_en_un_cliente(self, db, monkeypatch):
        monkeypatch.setattr(settings, "LICENCIA_GESTION_LOCAL", False)
        lic = Licencia(
            clave="APX-TEST-0000-0000-0000",
            cliente="Cliente",
            machine_id="cliente1",
            plan="trial",
            fecha_expiracion=datetime.now(timezone.utc) + timedelta(days=30),
            activa=True,
        )
        db.add(lic)
        db.commit()

        with pytest.raises(HTTPException) as exc:
            router_licencia.alternar_activa(lic.id, None, db, _usuario(db))

        assert exc.value.status_code == 403


class TestSeed:
    def _sesion(self, monkeypatch):
        engine = _engine_memoria()
        Session = sessionmaker(bind=engine)
        monkeypatch.setattr("app.database.SessionLocal", Session)
        return Session

    def test_sin_licencia_auto_no_siembra_demo(self, monkeypatch):
        Session = self._sesion(monkeypatch)
        import app.main as main

        monkeypatch.setattr(main.settings, "LICENCIA_AUTO", False)
        monkeypatch.setattr(main.settings, "ADMIN_PASSWORD_INICIAL", "clave-inicial")

        main._seed_database()

        db = Session()
        try:
            assert db.query(Licencia).count() == 0
            admin = db.query(Usuario).filter(Usuario.username == "admin").first()
            assert admin is not None
            assert verificar_password("clave-inicial", admin.password_hash)
            assert not verificar_password("admin", admin.password_hash)
        finally:
            db.close()

    def test_con_licencia_auto_se_mantiene_el_comportamiento(self, monkeypatch):
        Session = self._sesion(monkeypatch)
        import app.main as main

        monkeypatch.setattr(main.settings, "LICENCIA_AUTO", True)

        main._seed_database()

        db = Session()
        try:
            lic = db.query(Licencia).first()
            assert lic is not None
            assert lic.plan == "pro"
            assert lic.activa is True
        finally:
            db.close()


class TestHealth:
    def test_health_responde_sin_auth(self):
        from app.main import app

        ruta = next(r for r in app.routes if getattr(r, "path", None) == "/health")
        assert ruta.endpoint() == {"status": "ok", "version": settings.APP_VERSION}
