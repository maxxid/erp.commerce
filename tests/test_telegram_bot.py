"""Bot de Telegram interactivo.

Pruebas de parseo de comandos, autorización por chat_id, persistencia del
offset y de que los handlers generen texto con los datos esperados.
"""
import itertools

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401
from app.database import Base as _Base
from app.models.categoria import Categoria
from app.models.cliente import Cliente
from app.models.movimiento_caja import MovimientoCaja
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.models.venta import Venta, VentaItem
from app.services import config_service, telegram_bot_service as tbs

_barras = itertools.count(1)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def cfg(db):
    config_service.set_config(db, "telegram_bot_token", "TOK")
    config_service.set_config(db, "telegram_chat_id", "42")
    config_service.set_config(db, "telegram_bot_interactivo", "true")
    return db


def producto(db, nombre, stock=5, minimo=8, venta=1000, cat=None):
    p = Producto(codigo_barras=f"7790000{next(_barras):06d}", nombre=nombre,
                 stock_actual=stock, stock_minimo=minimo, precio_venta=venta,
                 categoria_id=cat, activo=True, controla_stock=True)
    db.add(p)
    db.commit()
    return p


def test_procesar_update_ignora_chat_no_autorizado(db, cfg, monkeypatch):
    enviados = []
    monkeypatch.setattr(tbs, "_send", lambda token, chat_id, texto, reply_markup=None: enviados.append((chat_id, texto)))
    upd = {"message": {"chat": {"id": 999}, "text": "/stock"}}
    tbs.procesar_update(db, "TOK", upd)
    assert any("No autorizado" in t[1] for t in enviados)


def test_comando_stock_genera_texto(db, cfg, monkeypatch):
    producto(db, "Gaseosa", stock=5, minimo=8)
    enviados = []
    monkeypatch.setattr(tbs, "_send", lambda token, chat_id, texto, reply_markup=None: enviados.append(texto))
    upd = {"message": {"chat": {"id": 42}, "text": "/stock"}}
    tbs.procesar_update(db, "TOK", upd)
    assert enviados and "Stock" in enviados[0]


def test_comando_ventas_hoy(db, cfg, monkeypatch):
    u = Usuario(username="admin", password_hash="x", nombre="Admin", rol="admin")
    db.add(u)
    db.commit()
    v = Venta(numero="V-1", usuario_id=u.id, sucursal_id=1, total=1000, medio_pago="efectivo",
              estado="confirmada")
    db.add(v)
    db.commit()
    enviados = []
    monkeypatch.setattr(tbs, "_send", lambda token, chat_id, texto, reply_markup=None: enviados.append(texto))
    tbs.procesar_update(db, "TOK", {"message": {"chat": {"id": 42}, "text": "/ventas"}})
    assert enviados and "Ventas" in enviados[0]
    assert "1.000" in enviados[0] or "1000" in enviados[0]


def test_comando_desconocido(db, cfg, monkeypatch):
    enviados = []
    monkeypatch.setattr(tbs, "_send", lambda token, chat_id, texto, reply_markup=None: enviados.append(texto))
    tbs.procesar_update(db, "TOK", {"message": {"chat": {"id": 42}, "text": "/foo"}})
    assert enviados and "no reconocido" in enviados[0].lower() or "Comandos" in enviados[0]


def test_stockbajo_menu_envia_keyboard(db, cfg, monkeypatch):
    cat = Categoria(nombre="Bebidas", activo=True)
    db.add(cat)
    db.commit()
    producto(db, "Gaseosa", stock=2, minimo=8, cat=cat.id)
    enviados = []
    keyboards = []
    def fake(token, chat_id, texto, reply_markup=None):
        enviados.append(texto)
        keyboards.append(reply_markup)
    monkeypatch.setattr(tbs, "_send", fake)
    tbs.procesar_update(db, "TOK", {"message": {"chat": {"id": 42}, "text": "/stockbajo"}})
    assert enviados
    assert keyboards and keyboards[0] is not None
    assert "inline_keyboard" in keyboards[0]


def test_callback_stockbajo_categoria(db, cfg, monkeypatch):
    cat = Categoria(nombre="Bebidas", activo=True)
    db.add(cat)
    db.commit()
    producto(db, "Gaseosa", stock=2, minimo=8, cat=cat.id)
    editados = []
    monkeypatch.setattr(tbs, "_edit_message", lambda token, chat_id, mid, texto: editados.append(texto))
    monkeypatch.setattr(tbs, "_answer_callback", lambda token, cb_id, text=None: None)
    cb_upd = {"callback_query": {"id": "cb1", "data": f"sb:{cat.id}",
                                 "message": {"chat": {"id": 42}, "message_id": 7}}}
    tbs.procesar_update(db, "TOK", cb_upd)
    assert editados and "Gaseosa" in editados[0]


def test_chequear_mensajes_persiste_offset(db, cfg, monkeypatch):
    class Resp:
        ok = True
        def json(self):
            return {"ok": True, "result": [{"update_id": 5, "message": {"chat": {"id": 42}, "text": "/stock"}}]}
    class RespPost:
        ok = True
        def json(self):
            return {"ok": True, "result": True}
    monkeypatch.setattr("requests.get", lambda *a, **k: Resp())
    monkeypatch.setattr("requests.post", lambda *a, **k: RespPost())
    monkeypatch.setattr(tbs, "SessionLocal", lambda: db)
    monkeypatch.setattr(tbs, "_WEBHOOK_DELETED", False)
    enviados = []
    monkeypatch.setattr(tbs, "_send", lambda token, chat_id, texto, reply_markup=None: enviados.append(texto))
    tbs.chequear_mensajes()
    assert config_service.get_config(db, "telegram_bot_offset") == "6"


def test_chequear_mensajes_desactivado_no_hace_nada(db, monkeypatch):
    config_service.set_config(db, "telegram_bot_token", "TOK")
    config_service.set_config(db, "telegram_chat_id", "42")
    config_service.set_config(db, "telegram_bot_interactivo", "false")
    monkeypatch.setattr(tbs, "SessionLocal", lambda: db)
    llamadas = []
    monkeypatch.setattr("requests.get", lambda *a, **k: llamadas.append(1) or None)
    tbs.chequear_mensajes()
    assert llamadas == []