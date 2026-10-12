"""Tests de la capa de IA: proveedor, reintentos, límites y configuración.

La red está bloqueada por la fixture autouse `sin_red`, así que todo pasa
mockeando `requests.post` al estilo de test_scrapers_fetch.py.
"""

import json

import pytest
import requests
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.services import config_service, ia
from app.services.ia import limites, registro
from app.services.ia.openai_compat import ProveedorOpenAICompat, extraer_json
from app.services.ia.proveedor import (
    ErrorProveedor,
    IADeshabilitada,
    LimiteAgotado,
)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


class FalsaRespuesta:
    def __init__(self, status=200, json_data=None, text="", headers=None):
        self.status_code = status
        self._json = json_data
        self.text = text
        self.headers = headers or {}

    def json(self):
        if self._json is None:
            raise ValueError("sin json")
        return self._json


def cuerpo(texto, modelo="llama-3.3-70b-versatile", uso=None, sin_usage=False):
    data = {
        "model": modelo,
        "choices": [{"message": {"role": "assistant", "content": texto}}],
    }
    if not sin_usage:
        data["usage"] = (
            uso if uso is not None else {"prompt_tokens": 10, "completion_tokens": 5}
        )
    return FalsaRespuesta(status=200, json_data=data)


def instalar_post(monkeypatch, *respuestas):
    """Reemplaza requests.post por una cola. Devuelve (pedidos, avanzar)."""
    pedidos = []
    cola = list(respuestas)

    def fake_post(url, **kwargs):
        pedidos.append((url, kwargs))
        if not cola:
            raise AssertionError(f"request inesperada a {url}")
        r = cola.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    monkeypatch.setattr(requests, "post", fake_post)
    return pedidos


def sin_dormir(monkeypatch):
    """Los reintentos no duermen: los tests no deberían tardar segundos."""
    esperas = []
    monkeypatch.setattr("app.services.ia.openai_compat.dormir", esperas.append)
    return esperas


def proveedor(**kw):
    kw.setdefault("base_url", "https://ejemplo.test/openai/v1")
    kw.setdefault("api_key", "sk-test-123456")
    kw.setdefault("modelo", "llama-3.3-70b-versatile")
    return ProveedorOpenAICompat(**kw)


class TestExtraerJson:
    def test_json_plano(self):
        assert extraer_json('{"a": 1}') == {"a": 1}

    def test_array(self):
        assert extraer_json("[1, 2]") == [1, 2]

    def test_code_fence(self):
        texto = '```json\n{"categoria": "Bebidas"}\n```'
        assert extraer_json(texto) == {"categoria": "Bebidas"}

    def test_fence_sin_lang(self):
        assert extraer_json('```\n{"a": 1}\n```') == {"a": 1}

    def test_con_prose_alrededor(self):
        texto = 'Acá está el resultado:\n{"confianza": 0.9}\nEspero que sirva.'
        assert extraer_json(texto) == {"confianza": 0.9}

    def test_llaves_dentro_de_string(self):
        texto = 'ruido {"nombre": "Coca {grande}"} fin'
        assert extraer_json(texto) == {"nombre": "Coca {grande}"}

    def test_anidado(self):
        texto = 'x {"a": {"b": [1, 2]}} y'
        assert extraer_json(texto) == {"a": {"b": [1, 2]}}

    def test_string_con_llave_de_cierre(self):
        texto = '{"a": "texto } raro"}'
        assert extraer_json(texto) == {"a": "texto } raro"}

    def test_vacio_tira_error(self):
        with pytest.raises(ValueError):
            extraer_json("")

    def test_sin_json_tira_error(self):
        with pytest.raises(ValueError):
            extraer_json("no hay json acá")

    def test_llave_desbalanceada_tira_error(self):
        with pytest.raises(ValueError):
            extraer_json('{"a": ')


class TestReintentos:
    def test_ok_al_primer_intento(self, monkeypatch):
        instalar_post(monkeypatch, cuerpo('{"ok": true}'))
        esperas = sin_dormir(monkeypatch)
        resp = proveedor().completar(sistema="s", usuario="u", como_json=True)
        assert resp.texto == '{"ok": true}'
        assert resp.reintentos == 0
        assert esperas == []

    def test_reintenta_429_y_recupera(self, monkeypatch):
        instalar_post(
            monkeypatch,
            FalsaRespuesta(status=429, text="rate limited"),
            cuerpo("listo"),
        )
        esperas = sin_dormir(monkeypatch)
        resp = proveedor().completar(sistema="s", usuario="u")
        assert resp.texto == "listo"
        assert resp.reintentos == 1
        assert len(esperas) == 1

    def test_respeta_retry_after(self, monkeypatch):
        instalar_post(
            monkeypatch,
            FalsaRespuesta(status=429, headers={"Retry-After": "7"}),
            cuerpo("ok"),
        )
        esperas = sin_dormir(monkeypatch)
        proveedor().completar(sistema="s", usuario="u")
        assert esperas == [7.0]

    def test_acota_retry_after_demasiado_grande(self, monkeypatch):
        instalar_post(
            monkeypatch,
            FalsaRespuesta(status=429, headers={"Retry-After": "9999"}),
            cuerpo("ok"),
        )
        esperas = sin_dormir(monkeypatch)
        proveedor().completar(sistema="s", usuario="u")
        assert esperas == [30.0]

    def test_agota_reintentos_en_500(self, monkeypatch):
        instalar_post(
            monkeypatch,
            FalsaRespuesta(status=500),
            FalsaRespuesta(status=500),
            FalsaRespuesta(status=500),
        )
        sin_dormir(monkeypatch)
        with pytest.raises(ErrorProveedor, match="500"):
            proveedor(max_reintentos=2).completar(sistema="s", usuario="u")

    def test_4xx_no_reintenta(self, monkeypatch):
        pedidos = instalar_post(monkeypatch, FalsaRespuesta(status=400, text="malo"))
        sin_dormir(monkeypatch)
        with pytest.raises(ErrorProveedor, match="400"):
            proveedor().completar(sistema="s", usuario="u")
        assert len(pedidos) == 1

    def test_error_de_red_reintenta(self, monkeypatch):
        instalar_post(
            monkeypatch,
            requests.ConnectionError("cayo"),
            cuerpo("recuperado"),
        )
        esperas = sin_dormir(monkeypatch)
        resp = proveedor().completar(sistema="s", usuario="u")
        assert resp.texto == "recuperado"
        assert len(esperas) == 1

    def test_error_de_red_sin_reintentos_tira_error(self, monkeypatch):
        instalar_post(monkeypatch, requests.Timeout("lento"), requests.Timeout("lento"))
        sin_dormir(monkeypatch)
        with pytest.raises(ErrorProveedor, match="sin conexion"):
            proveedor(max_reintentos=1).completar(sistema="s", usuario="u")

    def test_sin_key_tira_error(self):
        with pytest.raises(ErrorProveedor, match="api_key"):
            proveedor(api_key="").completar(sistema="s", usuario="u")

    def test_sin_modelo_tira_error(self):
        with pytest.raises(ErrorProveedor, match="modelo"):
            proveedor(modelo="").completar(sistema="s", usuario="u")


class TestParseoRespuesta:
    def test_lee_usage(self, monkeypatch):
        instalar_post(monkeypatch, cuerpo("hola", uso={"prompt_tokens": 33, "completion_tokens": 7}))
        resp = proveedor().completar(sistema="s", usuario="u")
        assert resp.tokens_in == 33
        assert resp.tokens_out == 7
        assert resp.modelo == "llama-3.3-70b-versatile"

    def test_usage_faltante_no_explota(self, monkeypatch):
        instalar_post(monkeypatch, cuerpo("hola", sin_usage=True))
        resp = proveedor().completar(sistema="s", usuario="u")
        assert resp.tokens_in == 0
        assert resp.tokens_out == 0

    def test_estructura_invalida_tira_error(self, monkeypatch):
        instalar_post(monkeypatch, FalsaRespuesta(200, json_data={"sin": "choices"}))
        with pytest.raises(ErrorProveedor, match="estructura"):
            proveedor().completar(sistema="s", usuario="u")

    def test_respuesta_sin_json_tira_error(self, monkeypatch):
        instalar_post(monkeypatch, FalsaRespuesta(200, json_data=None))
        with pytest.raises(ErrorProveedor, match="JSON"):
            proveedor().completar(sistema="s", usuario="u")

    def test_envia_authorization_y_modelo(self, monkeypatch):
        pedidos = instalar_post(monkeypatch, cuerpo("ok"))
        proveedor(api_key="sk-secreta").completar(sistema="s", usuario="hola")
        url, kwargs = pedidos[0]
        assert url == "https://ejemplo.test/openai/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer sk-secreta"
        assert kwargs["json"]["model"] == "llama-3.3-70b-versatile"
        assert kwargs["json"]["messages"] == [
            {"role": "system", "content": "s"},
            {"role": "user", "content": "hola"},
        ]

    def test_como_json_agrega_response_format(self, monkeypatch):
        pedidos = instalar_post(monkeypatch, cuerpo("{}"))
        proveedor().completar(sistema="s", usuario="u", como_json=True)
        assert pedidos[0][1]["json"]["response_format"] == {"type": "json_object"}

    def test_sin_json_no_manda_response_format(self, monkeypatch):
        pedidos = instalar_post(monkeypatch, cuerpo("ok"))
        proveedor().completar(sistema="s", usuario="u")
        assert "response_format" not in pedidos[0][1]["json"]

    def test_base_url_con_barra_final(self, monkeypatch):
        pedidos = instalar_post(monkeypatch, cuerpo("ok"))
        proveedor(base_url="https://x.test/v1/").completar(sistema="s", usuario="u")
        assert pedidos[0][0] == "https://x.test/v1/chat/completions"


class TestConfiguracion:
    def test_sin_key_esta_deshabilitada(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "")
        cfg = registro.configuracion(db)
        assert cfg["habilitada"] is False
        assert cfg["configure_key"] is True
        assert cfg["api_key_origen"] == "ninguna"

    def test_key_interna_desde_env(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_interna_abcd")
        cfg = registro.configuracion(db)
        assert cfg["habilitada"] is True
        assert cfg["api_key_origen"] == "interna"
        assert cfg["api_key_enmascarada"] == "gsk_••••abcd"

    def test_key_de_cliente_pisa_la_interna(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_interna_abcd")
        config_service.set_config(db, "ia_api_key", "sk_cliente_9999")
        cfg = registro.configuracion(db)
        assert cfg["api_key_origen"] == "cliente"
        assert cfg["api_key_enmascarada"] == "sk_c••••9999"
        assert "sk_cliente_9999" not in json.dumps(cfg, ensure_ascii=False)

    def test_nunca_devuelve_la_key_cruda(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_super_secreta_key")
        config_service.set_config(db, "ia_api_key", "sk_cliente_remembranza")
        cfg = registro.configuracion(db)
        dump = json.dumps(cfg, ensure_ascii=False)
        assert "gsk_super_secreta_key" not in dump
        assert "sk_cliente_remembranza" not in dump

    def test_default_habilitada_cuando_hay_key(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_abcd1234")
        assert registro.configuracion(db)["habilitada"] is True

    def test_desactivada_expresamente(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_abcd1234")
        config_service.set_config(db, "ia_habilitada", "false")
        assert registro.configuracion(db)["habilitada"] is False

    def test_provider_desconocido_cae_en_custom(self, db):
        config_service.set_config(db, "ia_provider", "proveedor-inventado")
        assert registro.configuracion(db)["provider"] == "custom"

    def test_defaults_del_provider(self, db):
        config_service.set_config(db, "ia_provider", "groq")
        cfg = registro.configuracion(db)
        assert cfg["base_url"] == "https://api.groq.com/openai/v1"
        assert cfg["modelo"] == "openai/gpt-oss-120b"

    def test_limite_por_defecto(self, db):
        assert registro.configuracion(db)["limite_mes"] == registro.LIMITE_MES_DEFECTO

    def test_limite_configurado(self, db):
        config_service.set_config(db, "ia_limite_mes", "42")
        assert registro.configuracion(db)["limite_mes"] == 42

    def test_limite_invalido_cae_en_default(self, db):
        config_service.set_config(db, "ia_limite_mes", "no-es-numero")
        assert registro.configuracion(db)["limite_mes"] == registro.LIMITE_MES_DEFECTO


class TestEnmascarar:
    def test_clave_larga(self):
        assert registro.enmascarar("gsk_1234567890abcd") == "gsk_••••abcd"

    def test_clave_vacia(self):
        assert registro.enmascarar("") == ""

    def test_clave_corta(self):
        assert registro.enmascarar("abc") == "••••••••"


class TestCompletar:
    def _habilitar(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "gsk_abcd1234efgh")
        config_service.set_config(db, "ia_base_url", "https://x.test/v1")
        config_service.set_config(db, "ia_model", "modelo-x")

    def test_deshabilitada_tira_error(self, db, monkeypatch):
        monkeypatch.setattr(registro.settings, "IA_DEFAULT_API_KEY", "")
        with pytest.raises(IADeshabilitada):
            ia.completar(db, sistema="s", usuario="u")

    def test_llamada_ok_registra_uso(self, db, monkeypatch):
        self._habilitar(db, monkeypatch)
        instalar_post(monkeypatch, cuerpo("respuesta"))
        resp = ia.completar(db, sistema="s", usuario="u")
        assert resp.texto == "respuesta"
        uso = limites.leer(db)
        assert uso["llamadas"] == 1
        assert uso["tokens_in"] == 10
        assert uso["tokens_out"] == 5

    def test_uso_se_acumula(self, db, monkeypatch):
        self._habilitar(db, monkeypatch)
        instalar_post(monkeypatch, cuerpo("a"), cuerpo("b"))
        ia.completar(db, sistema="s", usuario="u")
        ia.completar(db, sistema="s", usuario="u")
        assert limites.leer(db)["llamadas"] == 2

    def test_errores_no_se_registran_como_uso(self, db, monkeypatch):
        self._habilitar(db, monkeypatch)
        instalar_post(monkeypatch, FalsaRespuesta(400, text="malo"))
        with pytest.raises(ErrorProveedor):
            ia.completar(db, sistema="s", usuario="u")
        assert limites.leer(db)["llamadas"] == 0

    def test_limite_agotado_tira_error(self, db, monkeypatch):
        self._habilitar(db, monkeypatch)
        config_service.set_config(db, "ia_limite_mes", "1")
        instalar_post(monkeypatch, cuerpo("a"))
        ia.completar(db, sistema="s", usuario="u")
        with pytest.raises(LimiteAgotado):
            ia.completar(db, sistema="s", usuario="u")

    def test_falla_el_llamado_no_consume_cuota(self, db, monkeypatch):
        self._habilitar(db, monkeypatch)
        config_service.set_config(db, "ia_limite_mes", "1")
        instalar_post(monkeypatch, FalsaRespuesta(400, text="malo"))
        with pytest.raises(ErrorProveedor):
            ia.completar(db, sistema="s", usuario="u")
        assert limites.leer(db)["llamadas"] == 0
        # queda cuota para el siguiente intento bueno
        instalar_post(monkeypatch, cuerpo("ok"))
        assert ia.completar(db, sistema="s", usuario="u").texto == "ok"


class TestLimites:
    def test_clave_de_mes(self):
        from datetime import datetime
        assert limites.clave_mes(datetime(2026, 3, 7)) == "ia_uso_2026_03"

    def test_leer_vacio(self, db):
        assert limites.leer(db) == {"llamadas": 0, "tokens_in": 0, "tokens_out": 0}

    def test_registrar_y_leer(self, db):
        limites.registrar(db, llamadas=2, tokens_in=100, tokens_out=50)
        assert limites.leer(db) == {
            "llamadas": 2,
            "tokens_in": 100,
            "tokens_out": 50,
        }

    def test_registrar_invalida_no_explota(self, db):
        config_service.set_config(db, "ia_uso_2026_10", "esto-no-es-json")
        assert limites.leer(db)["llamadas"] == 0

    def test_sin_limite_pasa(self, db):
        assert limites.verificar(db, None)["llamadas"] == 0

    def test_limite_cero_no_bloquea(self, db):
        assert limites.verificar(db, 0)["llamadas"] == 0

    def test_dentro_del_limite_pasa(self, db):
        limites.registrar(db, llamadas=4)
        assert limites.verificar(db, 5)["llamadas"] == 4

    def test_en_el_limite_bloquea_la_siguiente(self, db):
        # El chequeo es previo: con 5 hechas y límite 5, la sexta no entra.
        limites.registrar(db, llamadas=5)
        with pytest.raises(LimiteAgotado):
            limites.verificar(db, 5)
