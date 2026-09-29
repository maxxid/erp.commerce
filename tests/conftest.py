"""Configuracion de pytest.

app/database.py llama verificar_db() a nivel de modulo, asi que DATABASE_URL
tiene que estar seteada ANTES de cualquier import de app.* o la suite intenta
abrir la base de datos de desarrollo.
"""

import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(ROOT))
os.environ.setdefault(
    "DATABASE_URL",
    f"sqlite:///{(Path(os.environ.get('TEMP', '/tmp')) / 'apexerp_test.db').as_posix()}",
)

BARCODE = "7790001234567"


@pytest.fixture(autouse=True)
def sin_red(monkeypatch):
    """Ningun test puede pegarle a la red.

    Los scrapers se testean con fixtures, no contra Carrefour/Vea reales: contra
    la red los tests serian lentos, flaky y te quemarian el rate limit de las
    fuentes a las que les scrapeas todos los dias.
    """
    import socket

    def bloqueado(*args, **kwargs):
        raise RuntimeError(
            "Los tests no pueden hacer red. Usá una fixture de tests/fixtures/."
        )

    monkeypatch.setattr(socket.socket, "connect", bloqueado)
    monkeypatch.setattr(socket, "create_connection", bloqueado)
    monkeypatch.setattr(socket, "getaddrinfo", bloqueado)


@pytest.fixture
def fixture_path():
    return FIXTURES


@pytest.fixture
def leer_fixture():
    def _leer(nombre):
        return (FIXTURES / nombre).read_text(encoding="utf-8")
    return _leer


@pytest.fixture
def leer_json():
    def _leer(nombre):
        return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))
    return _leer


@pytest.fixture
def sin_cache():
    """Aisla la cache de scraping para que los tests no se contaminen."""
    from app.services import lookup_service
    lookup_service._cache.clear()
    yield lookup_service
    lookup_service._cache.clear()
