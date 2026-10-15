"""Correcciones de la pestaña de usuarios y de licencias.

Tres cosas que el dueño encontró usando el sistema y que se cayeron en silencio:

  - Editar un usuario sin escribir una clave nueva devolvía 422 y la vista
    mostraba "no se pudo guardar" sin motivo: el form manda `password: ""` y el
    backend exigía 4 caracteres.
  - El toggle activar/desactivar ignoraba lo que pedía la vista y simplemente
    negaba el estado actual, así que dos clicks rápidos dejaban al usuario como
    estaba.
  - El botón "Desactivar" de licencias llamaba a `PATCH /api/licencia/{id}/toggle`,
    que no existía: el `catch` tragaba el 404, la tabla mostraba "Inactiva" y en
    la base seguía activa.

Además del toggle de licencias se protege lo más fácil de romper: que no se
pueda apagar la única licencia de esta máquina, porque el login arranca pidiendo
licencia válida y quedaría todo el mundo afuera sin nadie para reactivarla.
"""

import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.auth.security import hash_password, verificar_password
from app.database import Base as _Base
from app.models import Licencia, Usuario
from app.routers import licencia as router_licencia
from app.routers import usuarios as router_usuarios
from app.services import licencia_service

RAIZ = Path(__file__).resolve().parent.parent
VISTA_USUARIOS = RAIZ / "frontend" / "src" / "views" / "UsuariosView.vue"
VISTA_LICENCIAS = RAIZ / "frontend" / "src" / "views" / "LicenciasView.vue"
VISTA_PROVEEDORES = RAIZ / "frontend" / "src" / "views" / "ProveedoresView.vue"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        sufijo = uuid.uuid4().hex[:8]
        session.add(Usuario(
            username=f"admin_{sufijo}", nombre="Administrador",
            password_hash=hash_password("secret1"), rol="admin", activo=True,
        ))
        session.add(Usuario(
            username=f"cajero_{sufijo}", nombre="Cajero",
            password_hash=hash_password("secret1"), rol="cajero", activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _admin(db):
    return db.query(Usuario).filter(Usuario.rol == "admin").first()


def _cajero(db):
    return db.query(Usuario).filter(Usuario.rol == "cajero").first()


class TestEdicionDeUsuario:
    def test_dejar_la_clave_vacia_no_falla(self, db):
        """El form manda `password: ""` cuando no se toca el campo."""
        u = _cajero(db)
        antes = u.password_hash

        resp = router_usuarios.actualizar(
            u.id, router_usuarios.UsuarioUpdate(nombre="Otro nombre", password=""),
            db, _admin(db),
        )

        assert resp.data["nombre"] == "Otro nombre"
        assert u.password_hash == antes, "una clave vacía no debió tocar la clave"

    def test_un_espacio_en_blanco_tampoco_cambia_la_clave(self, db):
        u = _cajero(db)
        antes = u.password_hash

        router_usuarios.actualizar(
            u.id, router_usuarios.UsuarioUpdate(password="   "), db, _admin(db),
        )

        assert u.password_hash == antes

    def test_con_clave_nueva_se_cambia(self, db):
        u = _cajero(db)

        router_usuarios.actualizar(
            u.id, router_usuarios.UsuarioUpdate(password="nueva1"), db, _admin(db),
        )

        assert u.password_hash != "secret1"
        assert verificar_password("nueva1", u.password_hash)

    def test_con_clave_muy_corta_el_backend_aun_rechaza(self, db):
        # En la request esto lo convierte FastAPI en un 422; acá se ve que el
        # modelo sigue exigiendo los 4 caracteres.
        with pytest.raises(ValidationError):
            router_usuarios.UsuarioUpdate(password="abc")


class TestToggleDeUsuario:
    def test_respeta_el_estado_que_pide_la_vista(self, db):
        u = _cajero(db)

        router_usuarios.alternar_activo(
            u.id, router_usuarios.ActivoRequest(activo=False), db, _admin(db),
        )
        # El "es False" es contra el objeto que trae SQLAlchemy. En SQLite un
        # booleano se guarda como 0/1 y a veces vuelve como int: se compara
        # contra 0 para no depender de eso.
        assert not u.activo

        # Un segundo click con el mismo estado no debe "negar" y reactivarlo.
        router_usuarios.alternar_activo(
            u.id, router_usuarios.ActivoRequest(activo=False), db, _admin(db),
        )
        assert not u.activo

        router_usuarios.alternar_activo(
            u.id, router_usuarios.ActivoRequest(activo=True), db, _admin(db),
        )
        assert bool(u.activo) is True

    def test_sin_pedido_de_estado_invierte_el_actual(self, db):
        u = _cajero(db)

        router_usuarios.alternar_activo(u.id, None, db, _admin(db))

        assert not u.activo

    def test_no_se_puede_desactivar_a_un_admin(self, db):
        admin = _admin(db)

        with pytest.raises(HTTPException) as exc:
            router_usuarios.alternar_activo(
                admin.id, router_usuarios.ActivoRequest(activo=False), db, admin,
            )

        assert exc.value.status_code == 400
        assert admin.activo is True

    def test_no_se_puede_desactivar_a_uno_mismo(self, db):
        cajero = _cajero(db)

        # Aunque el rol no lo dejara llegar, el helper no deja que nadie se
        # desactive a sí mismo: quedaría sin forma de volver a entrar.
        with pytest.raises(HTTPException) as exc:
            router_usuarios.alternar_activo(
                cajero.id, router_usuarios.ActivoRequest(activo=False), db, cajero,
            )

        assert exc.value.status_code == 400
        assert "propio" in exc.value.detail
        assert cajero.activo is True


class TestToggleDeLicencia:
    @pytest.fixture(autouse=True)
    def maquina_fija(self, monkeypatch):
        """El id de máquina real corre un WMI de PowerShell con timeout de 3s."""
        monkeypatch.setattr(licencia_service, "obtener_machine_id", lambda: "m-test")

    def _licencia(self, db, activa=True, machine_id="m-test", n=0):
        lic = Licencia(
            clave=f"APX-TST-{n}-{uuid.uuid4().hex[:6].upper()}",
            cliente="Comercio", machine_id=machine_id, plan="pro",
            fecha_inicio=datetime.now(timezone.utc),
            fecha_expiracion=datetime.now(timezone.utc) + timedelta(days=30),
            activa=activa,
        )
        db.add(lic)
        db.commit()
        db.refresh(lic)
        return lic

    def test_desactiva_y_vuelve_a_activar(self, db):
        lic = self._licencia(db, n=1)
        # Hay otra activa: apagar esta no deja al sistema sin licencia.
        self._licencia(db, n=2)

        resp = router_licencia.alternar_activa(
            lic.id, router_licencia.ActivaRequest(activa=False), db, _admin(db),
        )

        assert resp.data["activa"] is False
        assert lic.activa is False

        resp = router_licencia.alternar_activa(lic.id, None, db, _admin(db))
        assert resp.data["activa"] is True

    def test_no_se_puede_apagar_la_unica_de_esta_maquina(self, db):
        lic = self._licencia(db, n=1)

        with pytest.raises(HTTPException) as exc:
            router_licencia.alternar_activa(
                lic.id, router_licencia.ActivaRequest(activa=False), db, _admin(db),
            )

        assert exc.value.status_code == 400
        # Sigue activa: el backend la dejó tranquila.
        assert bool(lic.activa) is True

    def test_se_puede_apagar_la_ultima_si_esta_vencida(self, db):
        """Una licencia vencida ya no deja entrar a nadie: apagarla no empeora nada."""
        lic = self._licencia(db, n=1)
        lic.fecha_expiracion = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()

        router_licencia.alternar_activa(
            lic.id, router_licencia.ActivaRequest(activa=False), db, _admin(db),
        )

        assert lic.activa is False

    def test_se_puede_apagar_la_licencia_de_otra_maquina(self, db):
        """El candado protege a esta máquina, no a las licencias de otros clientes."""
        lic = self._licencia(db, n=1, machine_id="otra-maquina")

        router_licencia.alternar_activa(
            lic.id, router_licencia.ActivaRequest(activa=False), db, _admin(db),
        )

        assert lic.activa is False


def test_el_frontend_no_manda_la_clave_vacia():
    """Guardia del fix: si vuelve a mandar `password: ""`, la edición vuelve a fallar."""
    texto = VISTA_USUARIOS.read_text(encoding="utf-8")

    assert "if (form.password) payload.password" in texto
    assert "{ activo: !user.active }" in texto, "el toggle debe mandar el estado pedido"


def test_el_frontend_usa_el_toggle_de_licencias_real():
    texto = VISTA_LICENCIAS.read_text(encoding="utf-8")

    assert "/api/licencia/${lic.id}/toggle" in texto
    assert "{ activa: false }" in texto
    assert "catch { /* fallback */ }" not in texto, "el error ya no se traga"


def test_la_vista_de_proveedores_abre_el_historial_de_compras():
    """Lo que se le compró a un proveedor vive en GET /api/compras?proveedor_id=."""
    texto = VISTA_PROVEEDORES.read_text(encoding="utf-8")

    assert "openComprasModal(row)" in texto, "falta la acción de ver compras"
    assert "proveedor_id: supplier.id" in texto, "no se piden las compras de ese proveedor"
    assert "comprasConNotas" in texto, "no se muestran los comentarios del proveedor"
