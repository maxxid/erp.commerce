"""Tests de la configuración de IA (Ajustes > Inteligencia Artificial).

Lo crítico acá es que la API key sea write-only y que ningún campo no enviado
se pise con None al guardar.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.services import config_service
from app.services.ia import registro


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_guardar_cambia_solo_lo_que_se_envia(db):
    registro.guardar(db, {"provider": "openai"})
    registro.guardar(db, {"modelo": "gpt-4o-mini"})

    cfg = registro.configuracion(db)
    assert cfg["provider"] == "openai"
    assert cfg["modelo"] == "gpt-4o-mini"
    assert cfg["base_url"] == "https://api.openai.com/v1"  # la del proveedor


def test_guardar_habilitada_falsa_no_queda_como_ausente(db):
    registro.guardar(db, {"habilitada": False, "api_key": "sk_temporal_1234567890"})
    assert registro.configuracion(db)["habilitada"] is False

    registro.guardar(db, {"habilitada": True})
    assert registro.configuracion(db)["habilitada"] is True


def test_api_key_ausente_no_toque_la_guardada(db):
    registro.guardar(db, {"api_key": "sk_cliente_1234567890"})
    registro.guardar(db, {"provider": "groq", "modelo": "llama-3.3-70b-versatile"})

    cfg = registro.configuracion(db)
    assert cfg["api_key_enmascarada"] == "sk_c••••7890"
    assert cfg["api_key_origen"] == "cliente"


def test_api_key_vacia_la_borra(db):
    registro.guardar(db, {"api_key": "sk_cliente_1234567890"})
    registro.guardar(db, {"api_key": ""})

    cfg = registro.configuracion(db)
    assert cfg["api_key_enmascarada"] == ""
    assert cfg["api_key_origen"] == "ninguna"
    assert config_service.get_config(db, registro.CLAVE_API_KEY) in (None, "")


def test_api_key_nunca_vuelve_cruda(db):
    registro.guardar(db, {"api_key": "gsk_super_secreta_xyz_9999"})
    assert "gsk_super_secreta_xyz_9999" not in str(registro.configuracion(db))
    assert registro.configuracion(db)["api_key_enmascarada"] == "gsk_••••9999"


def test_provider_desconocido_tira_error(db):
    with pytest.raises(ValueError, match="Proveedor desconocido"):
        registro.guardar(db, {"provider": "chatgpt-fake"})


def test_provider_vacio_no_lo_guarda(db):
    registro.guardar(db, {"provider": "openai"})
    registro.guardar(db, {"provider": ""})
    assert registro.configuracion(db)["provider"] == "openai"


def test_provider_se_normaliza_a_minusculas(db):
    registro.guardar(db, {"provider": "OpenAI"})
    assert registro.configuracion(db)["provider"] == "openai"


def test_limite_cero_se_guarda_y_no_cae_en_default(db):
    registro.guardar(db, {"limite_mes": 0})
    assert registro.configuracion(db)["limite_mes"] == 0


def test_limite_none_lo_vacia(db):
    registro.guardar(db, {"limite_mes": 50})
    registro.guardar(db, {"limite_mes": None})
    assert config_service.get_config(db, registro.CLAVE_LIMITE_MES) in (None, "")
    assert registro.configuracion(db)["limite_mes"] == registro.LIMITE_MES_DEFECTO


def test_snapshot_informa_origen_de_la_key(db, monkeypatch):
    monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "")
    assert registro.configuracion(db)["api_key_origen"] == "ninguna"
    registro.guardar(db, {"api_key": "gsk_interna_1234567890"})
    assert registro.configuracion(db)["api_key_origen"] == "cliente"

    monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_default_1234567890")
    registro.guardar(db, {"api_key": ""})
    cfg = registro.configuracion(db)
    assert cfg["api_key_origen"] == "interna"
    assert cfg["api_key_enmascarada"] == "gsk_••••7890"


def test_probar_con_ia_deshabilitada_no_tira(db):
    resultado = registro.probar(db)
    assert resultado["ok"] is False
    assert "deshabilitada" in resultado["detalle"] or "API key" in resultado["detalle"]


def test_snapshot_de_proveedores(db):
    cfg = registro.configuracion(db)
    ids = {p["id"] for p in cfg["proveedores"]}
    assert ids == set(registro.PROVEEDORES)
    for p in cfg["proveedores"]:
        assert set(p) == {"id", "nombre", "base_url", "modelo"}


class TestRutasRegistradas:
    """El frontend necesita que existan; cubre errores de registro del router."""

    @staticmethod
    def _rutas():
        # FastAPI 0.141 anida los include_router en _IncludedRouter.
        from fastapi.routing import APIRoute
        from app.main import app

        def caminar(rutas):
            encontradas = []
            for ruta in rutas:
                if type(ruta).__name__ == "_IncludedRouter":
                    encontradas += caminar(ruta.original_router.routes)
                elif isinstance(ruta, APIRoute):
                    encontradas.append(ruta)
            return encontradas

        return caminar(app.routes)

    def _ruta(self, path, metodo):
        for ruta in self._rutas():
            if ruta.path == path and metodo in ruta.methods:
                return ruta
        raise AssertionError(f"No existe {metodo} {path}")

    def test_config_get_y_put(self):
        assert self._ruta("/api/ia/config", "GET") is not None
        assert self._ruta("/api/ia/config", "PUT") is not None

    def test_probar_es_post(self):
        assert self._ruta("/api/ia/probar", "POST") is not None

    def test_probar_gatea_por_plan(self):
        """`requiere_feature("ia")` tiene que estar enganchado en la ruta."""
        ruta = self._ruta("/api/ia/probar", "POST")
        nombres = [d.name for d in ruta.dependant.dependencies]
        assert "_plan" in nombres

    def test_config_put_es_admin(self):
        ruta = self._ruta("/api/ia/config", "PUT")
        nombres = [d.name for d in ruta.dependant.dependencies]
        assert "user" in nombres
