"""Permisos: la matriz única por rol y los permisos especiales por persona.

El problema que resuelve esto no era "faltaba una pantalla de permisos": era
que la lista de "quién puede qué" estaba escrita a mano en tres sitios
distintos (los `require_role` de cada router, los `meta.roles` del router del
frontend y el `allowed()` del sidebar) y ya habían divergido. Un repositor veía
"Cargar Mercadería" y el backend le devolvía 403 al confirmar; el cajero abría
la pantalla de Caja y los reportes de caja lo rechazaban.

Ahora hay una sola tabla en `app/auth/permisos.py`. De ahí salen
`GET /api/permisos`, la matriz en modo lectura de la pestaña de Usuarios, y los
permisos especiales que `require_role(..., permiso=...)` chequea.

Un permiso especial es un "pase suelto": se le da a una persona puntual sin
cambiarle el rol. El dueño (rol admin) siempre tiene todo, sin necesitar
ningún checkbox, para que no exista forma de que se quede afuera de su propio
sistema por un detalle de carga.
"""

import json
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.auth import permisos as mapa
from app.auth.dependencies import require_role
from app.auth.security import hash_password
from app.database import Base as _Base
from app.models import Usuario
from app.routers import permisos as router_permisos

RAIZ = Path(__file__).resolve().parent.parent
VISTA_USUARIOS = RAIZ / "frontend" / "src" / "views" / "UsuariosView.vue"
SIDEBAR = RAIZ / "frontend" / "src" / "components" / "layout" / "TheSidebar.vue"
BOTTOM_NAV = RAIZ / "frontend" / "src" / "components" / "layout" / "TheBottomNav.vue"


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _usuario(db, rol="cajero", permisos=None, username=None):
    sufijo = username or f"perm_{rol}"
    u = Usuario(
        username=sufijo, nombre="Persona", password_hash=hash_password("secret1"),
        rol=rol, permisos=json.dumps(permisos or []),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


class TestLecturaDePermisos:
    def test_el_dueño_tiene_todo_sin_ningun_permiso_cargado(self, db):
        u = _usuario(db, rol="admin", permisos=[])

        assert mapa.tiene_permiso(u, "ver_reportes")
        assert mapa.tiene_permiso(u, "cualquier_cosa")

    def test_un_rol_sin_permiso_solo_tiene_lo_que_toca_su_rol(self, db):
        u = _usuario(db, rol="cajero", permisos=[])

        assert not mapa.tiene_permiso(u, "ver_reportes")
        assert not mapa.tiene_permiso(u, "anular_ventas")

    def test_el_permiso_suelto_abre_la_puerta(self, db):
        u = _usuario(db, rol="cajero", permisos=["ver_reportes"])

        assert mapa.tiene_permiso(u, "ver_reportes")
        assert not mapa.tiene_permiso(u, "gestionar_clientes"), "un permiso no abre otra puerta"

    def test_se_ignora_json_roto_en_lugar_de_romper(self, db):
        """Si la celda quedó mal cargada, esa persona no tiene permisos."""
        u = _usuario(db, rol="cajero")
        u.permisos = "esto no es json"
        db.commit()

        assert mapa.permisos_de(u) == []
        assert not mapa.tiene_permiso(u, "ver_reportes")

    def test_se_ignoran_permisos_que_ya_no_existen(self, db):
        """Un permiso viejo en la base no debe colgar de nada ni tirar error."""
        u = _usuario(db, rol="cajero", permisos=["ver_reportes", "permiso_borrado"])

        assert mapa.permisos_de(u) == ["ver_reportes"]

    def test_permisos_de_normaliza_y_ordena(self, db):
        u = _usuario(db, rol="cajero")
        u.permisos = json.dumps(["ver_caja", "ver_reportes", "ver_reportes"])
        db.commit()

        assert mapa.permisos_de(u) == ["ver_caja", "ver_reportes"]

    def test_sin_usuario_no_tiene_nada(self):
        assert not mapa.tiene_permiso(None, "ver_reportes")


class TestValidacion:
    def test_acepta_las_claves_conocidas(self):
        assert mapa.validar_permisos(["ver_caja", "ver_reportes"]) == ["ver_caja", "ver_reportes"]

    def test_las_duplicadas_quedan_en_una(self):
        assert mapa.validar_permisos(["ver_caja", "ver_caja"]) == ["ver_caja"]

    def test_las_vacias_quedan_en_lista(self):
        assert mapa.validar_permisos([]) == []
        assert mapa.validar_permisos(None) == []

    def test_un_permiso_inventado_da_400_con_su_nombre(self):
        with pytest.raises(HTTPException) as exc:
            mapa.validar_permisos(["ver_reportes", "hacer_lo_que_quiera"])

        assert exc.value.status_code == 400
        assert "hacer_lo_que_quiera" in exc.value.detail


class TestRequireRoleConPermiso:
    def test_el_rol_permitido_pasa(self, db):
        u = _usuario(db, rol="encargado")
        assert _chequear(u, permiso="ver_reportes") is u

    def test_quien_tiene_el_permiso_pasa_aunque_su_rol_no(self, db):
        u = _usuario(db, rol="cajero", permisos=["ver_reportes"])
        assert _chequear(u, permiso="ver_reportes") is u

    def test_sin_rol_ni_permiso_da_403_que_nombrar_lo_que_falta(self, db):
        u = _usuario(db, rol="repositor", permisos=[])

        with pytest.raises(HTTPException) as exc:
            _chequear(u, roles=("admin", "encargado"), permiso="ver_reportes")

        assert exc.value.status_code == 403
        assert "encargado" in exc.value.detail
        assert "ver_reportes" in exc.value.detail

    def test_sin_permiso_el_error_no_lo_menciona(self, db):
        u = _usuario(db, rol="repositor")

        with pytest.raises(HTTPException) as exc:
            _chequear(u, roles=("admin",))

        assert "permiso" not in exc.value.detail

    def test_el_dueño_pasa_por_sobre_cualquier_restriccion(self, db):
        u = _usuario(db, rol="admin")
        assert _chequear(u, roles=("cajero",), permiso="nada") is u


def _chequear(user, roles=("admin", "encargado"), permiso=None):
    """Llama al checker que FastAPI construye con require_role."""
    checker = require_role(*roles, permiso=permiso)
    return checker(user=user)


class TestEndpointDeMatriz:
    def test_solo_el_dueño_la_ve(self, db):
        """El candado vive en el `Depends(require_role("admin"))` del endpoint,
        que al llamar la función directamente no se ejecuta: se prueba aparte."""
        cajero = _usuario(db, rol="cajero")

        with pytest.raises(HTTPException) as exc:
            require_role("admin")(user=cajero)

        assert exc.value.status_code == 403
        assert require_role("admin")(user=_usuario(db, rol="admin"))

    def test_devuelve_las_areas_las_acciones_y_los_permisos(self, db):
        resp = router_permisos.ver_matriz(user=_usuario(db, rol="admin"))

        assert {r["clave"] for r in resp.data["roles"]} == set(mapa.ROLES)
        assert {p["clave"] for p in resp.data["permisos_especiales"]} == mapa.claves_permisos()
        assert resp.data["matriz"], "la matriz no vino vacía"
        assert any(a["area"] == "Ventas" for a in resp.data["matriz"])

    def test_toda_accion_menciona_solo_roles_que_existen(self):
        claves_rol = set(mapa.ROLES)
        for area in mapa.MATRIZ:
            for accion in area["acciones"]:
                assert set(accion["roles"]) <= claves_rol, (
                    f"{area['area']} → {accion['accion']} cita un rol inventado"
                )

    def test_toda_accion_que_marca_permiso_lo_refiere_a_uno_real(self):
        for area in mapa.MATRIZ:
            for accion in area["acciones"]:
                if accion.get("permiso"):
                    assert accion["permiso"] in mapa.claves_permisos(), (
                        f"{area['area']} → {accion['accion']} apunta a un permiso inexistente"
                    )


class TestLosPermisosEstanConectados:
    """Si un permiso existe pero ningún endpoint lo chequea, el checkbox es
    mentira: se ve cargado en la ficha y no abre nada."""

    ARCHIVOS = {
        "ver_reportes": RAIZ / "app" / "routers" / "reportes.py",
        "gestionar_clientes": RAIZ / "app" / "routers" / "clientes.py",
        "ver_caja": RAIZ / "app" / "routers" / "caja.py",
        "anular_ventas": RAIZ / "app" / "routers" / "ventas.py",
    }

    @pytest.mark.parametrize("clave", sorted(mapa.claves_permisos()))
    def test_permiso_aparece_en_algun_endpoint(self, clave):
        texto = self.ARCHIVOS[clave].read_text(encoding="utf-8")

        assert f'permiso="{clave}"' in texto, (
            f"el permiso '{clave}' existe en la matriz pero ningún endpoint lo usa"
        )

    def test_require_role_sabe_aceptar_permisos(self):
        dependencias = (RAIZ / "app" / "auth" / "dependencies.py").read_text(encoding="utf-8")

        assert "permiso: Optional[str] = None" in dependencias
        assert "tiene_permiso(user, permiso)" in dependencias

    def test_el_modelo_guarda_los_permisos(self):
        modelo = (RAIZ / "app" / "models" / "usuario.py").read_text(encoding="utf-8")

        assert 'permisos = Column(Text, nullable=False, default="[]")' in modelo

    def test_existe_la_migracion_de_la_columna(self):
        """Sin esto, arrancar contra la base vieja revienta al leer la columna."""
        principal = (RAIZ / "app" / "main.py").read_text(encoding="utf-8")

        assert 'ALTER TABLE usuarios ADD COLUMN permisos TEXT' in principal


class TestElFrontendUsaLaMatriz:
    def test_la_vista_la_pide_al_backend_y_no_la_copia(self):
        texto = VISTA_USUARIOS.read_text(encoding="utf-8")

        assert "api.get('/api/permisos')" in texto
        assert "form.permisos" in texto, "no se guardan los permisos especiales"
        assert "ver_reportes" not in texto, (
            "las claves de permiso están escritas a mano en la vista: se van a "
            "desincronizar del backend"
        )

    def test_el_menú_no_asume_que_uno_sin_datos_es_admin(self):
        """Antes el fallback era 'admin' y se veía todo el menú de administración."""
        for archivo in (SIDEBAR, BOTTOM_NAV):
            texto = archivo.read_text(encoding="utf-8")

            assert "|| 'admin'" not in texto, f"{archivo.name} trata a un rol desconocido como admin"
            assert "|| 'repositor'" in texto
