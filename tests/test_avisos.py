"""Aviso proactivo de stock bajo por Telegram.

El ERP manda el listado de productos bajo mínimo al canal una vez por día, a
la hora configurada en Ajustes. El chequeo corre cada 10 minutos y lee la
config en cada vuelta, así que se puede cambiar la hora sin reiniciar y, si
el servicio estaba caído, el aviso sale igual más tarde.
"""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.compra import Compra, CompraItem
from app.models.producto import Producto
from app.models.proveedor import Proveedor
from app.models.usuario import Usuario
from app.routers import avisos as router
from app.services import avisos_service, config_service

import itertools

_barras = itertools.count(1)
TZ_AR = timezone(timedelta(hours=-3))


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
def user(db):
    u = Usuario(username="admin", password_hash="x", nombre="Admin", rol="admin")
    db.add(u)
    db.commit()
    return u


def producto(db, nombre, stock, minimo, venta=None):
    p = Producto(
        codigo_barras=f"7790000{next(_barras):06d}",
        nombre=nombre,
        stock_actual=stock,
        stock_minimo=minimo,
        precio_venta=venta,
    )
    db.add(p)
    db.commit()
    return p


def compra_de(db, p, proveedor, precio):
    prov = Proveedor(nombre=proveedor, cuit="30-00000000-0")
    db.add(prov)
    db.commit()
    compra = Compra(numero=f"C{next(_barras):06d}", proveedor_id=prov.id, usuario_id=1)
    db.add(compra)
    db.commit()
    db.add(CompraItem(compra_id=compra.id, producto_id=p.id, cantidad=10,
                      cantidad_recibida=10, precio_unitario=precio, subtotal=precio * 10))
    db.commit()
    return prov


def configurar(db, **claves):
    for clave, valor in claves.items():
        config_service.set_config(db, clave, str(valor))


class _Reloj:
    """Reloj congelado para probar la hora del aviso sin depender del reloj real."""

    def __init__(self, fijo):
        self.fijo = fijo

    def now(self, tz=None):
        return self.fijo


class TestMensaje:
    def test_lista_producto_con_proveedor_y_precios(self, db):
        p = producto(db, "Gaseosa", stock=2, minimo=8, venta=2500)
        compra_de(db, p, "Carrefour", 1500)

        texto = avisos_service.mensaje_stock_bajo(db)

        assert "Gaseosa" in texto
        assert "Stock 2 / mínimo 8" in texto
        assert "Proveedor: Carrefour" in texto
        assert "$1,500.00" in texto
        assert "$2,500.00" in texto

    def test_vacio_si_no_hay_nada_bajo(self, db):
        producto(db, "Alfajor", stock=50, minimo=1)
        assert avisos_service.mensaje_stock_bajo(db) == ""

    def test_escapa_html_de_los_nombres(self, db):
        producto(db, "Coca <script>alert(1)</script>", stock=0, minimo=1)
        assert "<script>" not in avisos_service.mensaje_stock_bajo(db)


class TestChequeoDiario:
    def _mandador(self, monkeypatch, db, lista):
        def _fake(token, chat_id, texto):
            lista.append((token, chat_id, texto))
            return True, "Mensaje enviado"
        monkeypatch.setattr(avisos_service, "enviar_a_telegram", _fake)
        monkeypatch.setattr(avisos_service, "SessionLocal", lambda: db)

    def test_no_manda_si_esta_apagado(self, db, monkeypatch):
        producto(db, "Gaseosa", stock=2, minimo=8)
        configurar(db, stock_aviso_enabled="false", telegram_bot_token="t", telegram_chat_id="1")
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert mandados == []

    def test_manda_una_vez_por_dia_y_anota_el_envio(self, db, monkeypatch):
        producto(db, "Gaseosa", stock=2, minimo=8)
        ahora = datetime.now(TZ_AR)
        configurar(db, stock_aviso_enabled="true", stock_aviso_hora="00:00",
                   telegram_bot_token="123:abc", telegram_chat_id="-1001")
        # Caja cerrada del día (apertura + cierre) para que el resumen se envíe
        from app.models.movimiento_caja import MovimientoCaja
        db.add(MovimientoCaja(tipo="apertura", monto=1000, usuario_id=1, sucursal_id=1))
        db.add(MovimientoCaja(tipo="cierre", monto=1000, usuario_id=1, sucursal_id=1, medio_pago=None))
        db.commit()
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert len(mandados) == 1
        assert mandados[0][0] == "123:abc"
        assert "Gaseosa" in mandados[0][2]
        assert config_service.get_config(db, "stock_aviso_ultimo_envio") == ahora.strftime("%Y-%m-%d")

        avisos_service.chequear_aviso_diario()
        assert len(mandados) == 1

    def test_no_manda_si_la_hora_falta(self, db, monkeypatch):
        producto(db, "Gaseosa", stock=2, minimo=8)
        configurar(db, stock_aviso_enabled="true", stock_aviso_hora="23:00",
                   telegram_bot_token="t", telegram_chat_id="1")
        # Reloj fijo a las 10:00: la hora del aviso es 23:00, todavía no.
        monkeypatch.setattr(avisos_service, "datetime", _Reloj(datetime(2026, 10, 13, 10, 0, tzinfo=TZ_AR)))
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert mandados == []

    def test_no_manda_sin_token(self, db, monkeypatch):
        producto(db, "Gaseosa", stock=2, minimo=8)
        configurar(db, stock_aviso_enabled="true", stock_aviso_hora="00:00",
                   telegram_bot_token="", telegram_chat_id="-1001")
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert mandados == []

    def test_no_anota_envio_si_no_hay_bajos(self, db, monkeypatch):
        producto(db, "Alfajor", stock=50, minimo=1)
        configurar(db, stock_aviso_enabled="true", stock_aviso_hora="00:00",
                   telegram_bot_token="t", telegram_chat_id="1")
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert mandados == []
        # Sin anotar: si algo se cae a cero más tarde, el aviso sale igual hoy.
        assert config_service.get_config(db, "stock_aviso_ultimo_envio") is None

    def test_hora_rota_no_explota(self, db, monkeypatch):
        producto(db, "Gaseosa", stock=2, minimo=8)
        configurar(db, stock_aviso_enabled="true", stock_aviso_hora="banana",
                   telegram_bot_token="t", telegram_chat_id="1")
        mandados = []
        self._mandador(monkeypatch, db, mandados)

        avisos_service.chequear_aviso_diario()
        assert mandados == []


class TestProbar:
    def test_sin_config_devuelve_error(self, db):
        ok, detalle = avisos_service.probar_envio(db)
        assert ok is False
        assert "Ajustes" in detalle

    def test_con_config_manda(self, db, user, monkeypatch):
        configurar(db, telegram_bot_token="t", telegram_chat_id="1")
        llamadas = []
        monkeypatch.setattr(avisos_service, "enviar_a_telegram",
                            lambda t, c, x: llamadas.append(x) or (True, "Mensaje enviado"))

        ok, detalle = avisos_service.probar_envio(db, user.id)
        assert ok is True
        assert llamadas and "ApexERP" in llamadas[0]


class TestRutas:
    def test_las_rutas_estan_registradas(self):
        rutas = {r.path for r in router.router.routes}
        assert "/api/avisos/probar" in rutas
        assert "/api/avisos/bot/estado" in rutas
        post_routes = [r for r in router.router.routes if r.methods == {"POST"}]
        assert any(r.path == "/api/avisos/probar" for r in post_routes)

    def test_probar_es_admin(self):
        nombres = [d.name for d in router.router.routes[0].dependant.dependencies]
        assert "user" in nombres
