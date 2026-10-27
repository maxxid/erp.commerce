"""Alta manual desde el POS para cajeros y carritos abandonados que se descartan.

Dos pedidos del dueño (26/10/2026):

1. **El cajero tiene que poder vender un producto que no está en el catálogo.**
   Antes `POST /api/productos` era solo admin/encargado, así que el POS le
   respondía 403 al cajero y la venta quedaba a medias. Ahora hay un alta
   específica del POS (`POST /api/productos/pos`) abierta al cajero, que crea
   el producto como `fuente='manual'` y **siempre deja un evento en Auditoría**:
   si lo hizo un cajero queda pendiente (`sospechoso`), si lo hizo el dueño o un
   encargado queda normal. La pantalla de Productos sigue restringida.

2. **El botón "Descartar" de un carrito abandonado no hacía nada.** Los
   carritos se generaban al vuelo en cada GET (`id = abandon_<venta>`), no
   existían en la tabla y el frontend solo cambiaba la fila en memoria: al
   refrescar volvían. Además, se listaban **todos** los pendientes históricos
   (55 carritos viejos en producción), sin paginación. Ahora se registran una
   sola vez como filas reales de `auditoria`, solo para los últimos 7 días, y el
   PATCH de estado funciona como con cualquier otro evento.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.auth.dependencies import require_role
from app.database import Base as _Base
from app.models.auditoria import Auditoria
from app.models.producto import Producto
from app.models.usuario import Sucursal, Usuario
from app.models.venta import Venta, VentaItem
from app.routers import productos as productos_router
from app.schemas.producto import ProductoCreate
from app.services import auditoria_service

RAIZ = Path(__file__).resolve().parent.parent
SRC = RAIZ / "frontend" / "src"

POS = SRC / "views" / "POSView.vue"
COBRO = SRC / "views" / "CobroMovilView.vue"
COLA = SRC / "composables" / "useOfflineSales.js"
QUICK = SRC / "components" / "pos" / "QuickCreateModal.vue"
AUDITORIA = SRC / "views" / "AuditoriaView.vue"
PERMISOS = RAIZ / "app" / "auth" / "permisos.py"


def _leer(path):
    return path.read_text(encoding="utf-8")


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        session.add(Sucursal(id=1, nombre="Principal"))
        session.add(Producto(
            codigo_barras="7790000000001", nombre="Producto de prueba",
            precio_venta=100, activo=True,
        ))
        session.commit()
        yield session
    finally:
        session.close()


def _usuario(db, rol, username=None):
    u = Usuario(
        username=username or f"user_{rol}",
        nombre=f"Persona {rol}",
        password_hash="x",
        rol=rol,
        activo=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _manual(codigo="*MANUAL*000001", nombre="Producto manual", precio=1500):
    return ProductoCreate(
        codigo_barras=codigo,
        nombre=nombre,
        precio_venta=precio,
        categoria_id=None,
    )


def _evento_manual(db):
    return (
        db.query(Auditoria)
        .filter(Auditoria.tipo == "producto_manual_creado")
        .order_by(Auditoria.id.desc())
        .first()
    )


class TestAltaManualDesdeElPos:
    def test_un_cajero_puede_crear_el_producto_que_esta_vendiendo(self, db):
        cajero = _usuario(db, "cajero")

        resp = productos_router.crear_desde_pos(_manual(), db=db, user=cajero)

        assert resp.data.id
        assert resp.data.codigo_barras == "*MANUAL*000001"
        assert resp.data.fuente == "manual", (
            "el alta del POS no puede quedar con otra fuente: es lo que la "
            "distingue de una carga del catálogo"
        )

    def test_siempre_queda_el_evento_en_auditoria(self, db):
        cajero = _usuario(db, "cajero")

        productos_router.crear_desde_pos(
            _manual(nombre="Carga urgente", precio=2500), db=db, user=cajero,
        )

        evento = _evento_manual(db)
        assert evento is not None
        assert evento.usuario_id == cajero.id
        assert evento.estado == "sospechoso", (
            "una carga manual de un cajero tiene que quedar pendiente para el auditor"
        )
        detalle = json.loads(evento.detalle)
        assert detalle["nombre"].lower() == "carga urgente"
        assert detalle["precio_venta"] == 2500
        assert detalle["codigo_barras"] == "*MANUAL*000001"
        assert detalle["rol"] == "cajero"

    def test_la_carga_del_dueño_no_queda_pendiente(self, db):
        admin = _usuario(db, "admin")

        productos_router.crear_desde_pos(_manual(), db=db, user=admin)

        evento = _evento_manual(db)
        assert evento is not None, "también se audita, para tener el rastro"
        assert evento.estado == "normal"

    def test_la_pantalla_de_productos_sigue_restringida(self, db):
        cajero = _usuario(db, "cajero")

        with pytest.raises(HTTPException) as exc:
            require_role("admin", "encargado")(user=cajero)

        assert exc.value.status_code == 403
        assert require_role("admin", "encargado", "cajero")(user=cajero) is cajero

    def test_el_alta_del_pos_valida_el_codigo_repetido(self, db):
        cajero = _usuario(db, "cajero")
        productos_router.crear_desde_pos(_manual(), db=db, user=cajero)

        with pytest.raises(HTTPException) as exc:
            productos_router.crear_desde_pos(_manual(), db=db, user=cajero)

        assert exc.value.status_code == 400
        assert "Producto Manual" in exc.value.detail

    def test_el_frontend_usa_el_endpoint_del_pos(self):
        for path in (POS, COBRO, COLA, QUICK):
            texto = _leer(path)
            assert "/api/productos/pos" in texto, (
                f"{path.name} sigue usando el alta general: el cajero recibe 403"
            )

    def test_la_matriz_de_permisos_lo_documenta(self):
        assert "Crear un producto manual desde el POS" in _leer(PERMISOS)


class TestElModalRapidoDelPos:
    def test_emite_el_producto_real_y_no_un_id_falso(self):
        """`api.post` ya desenvuelve el `data`: con `resp.data` se emitía un
        id `Date.now()` que después no existía al vender."""
        texto = _leer(QUICK)
        linea = next(l for l in texto.splitlines() if "emit('created'" in l)

        assert linea.strip() == "emit('created', resp)"
        assert "if (!resp || !resp.id) throw" in texto


def _venta_pendiente(db, cajero, creada, items=1, numero=None):
    numero = numero or f"V-{int(creada.timestamp())}"
    producto = db.query(Producto).first()
    venta = Venta(
        numero=numero,
        usuario_id=cajero.id,
        sucursal_id=1,
        subtotal=100 * items,
        total=100 * items,
        estado="pendiente",
        created_at=creada,
    )
    db.add(venta)
    db.flush()
    for _ in range(items):
        db.add(VentaItem(
            venta_id=venta.id,
            producto_id=producto.id,
            cantidad=1,
            precio_unitario=100,
            subtotal=100,
        ))
    db.commit()
    db.refresh(venta)
    return venta


def _ahora():
    return datetime.now(timezone.utc)


def _carritos(data):
    return [d for d in data if d["tipo"] == "carrito_abandonado"]


class TestCarritosAbandonados:
    def test_se_registran_como_eventos_reales(self, db):
        cajero = _usuario(db, "cajero")
        venta = _venta_pendiente(db, cajero, _ahora() - timedelta(minutes=15))

        data, total = auditoria_service.listar_con_carritos_abandonados(db)
        carritos = _carritos(data)

        assert len(carritos) == 1
        evento = carritos[0]
        assert isinstance(evento["id"], int), (
            "antes era un id virtual 'abandon_<n>' que el PATCH no podía tocar"
        )
        assert evento["venta_id"] == venta.id
        assert evento["estado"] == "sospechoso"
        assert evento["detalle"]["items"] == 1
        assert total == 1

    def test_no_se_duplica_en_cada_carga(self, db):
        cajero = _usuario(db, "cajero")
        _venta_pendiente(db, cajero, _ahora() - timedelta(minutes=15))

        auditoria_service.listar_con_carritos_abandonados(db)
        auditoria_service.listar_con_carritos_abandonados(db)
        auditoria_service.listar_con_carritos_abandonados(db)

        assert db.query(Auditoria).filter(
            Auditoria.tipo == "carrito_abandonado"
        ).count() == 1

    def test_descartar_lo_saca_de_pendientes_y_sobrevive_al_refresco(self, db):
        cajero = _usuario(db, "cajero")
        admin = _usuario(db, "admin", username="admin_auditor")
        _venta_pendiente(db, cajero, _ahora() - timedelta(minutes=15))

        data, _ = auditoria_service.listar_con_carritos_abandonados(db)
        evento_id = _carritos(data)[0]["id"]

        resultado = auditoria_service.cambiar_estado(db, evento_id, admin.id, "descartado")
        assert resultado["actualizado"] is True

        pendientes, _ = auditoria_service.listar_con_carritos_abandonados(db, estado="sospechoso")
        assert all(d["id"] != evento_id for d in pendientes), (
            "el carrito descartado volvió a aparecer en pendientes"
        )

        descartados, _ = auditoria_service.listar_con_carritos_abandonados(db, estado="descartado")
        assert any(d["id"] == evento_id for d in descartados)

        fila = db.query(Auditoria).filter(Auditoria.id == evento_id).one()
        assert fila.estado == "descartado"
        assert fila.auditado_por == admin.id

    def test_un_carrito_viejo_ya_no_es_una_alerta(self, db):
        cajero = _usuario(db, "cajero")
        _venta_pendiente(db, cajero, _ahora() - timedelta(days=8))

        data, _ = auditoria_service.listar_con_carritos_abandonados(db)

        assert _carritos(data) == [], (
            "en producción había 55 carritos de junio a octubre: no son alertas de hoy"
        )

    def test_un_carrito_recien_abierto_todavia_no_es_abandonado(self, db):
        cajero = _usuario(db, "cajero")
        _venta_pendiente(db, cajero, _ahora() - timedelta(minutes=5))

        data, _ = auditoria_service.listar_con_carritos_abandonados(db)

        assert _carritos(data) == []

    def test_un_carrito_vacio_no_genera_alerta(self, db):
        cajero = _usuario(db, "cajero")
        _venta_pendiente(db, cajero, _ahora() - timedelta(minutes=15), items=0)

        data, _ = auditoria_service.listar_con_carritos_abandonados(db)

        assert _carritos(data) == []


class TestLaVistaDeAuditoria:
    def test_el_descarte_va_al_backend(self):
        texto = _leer(AUDITORIA)

        assert "String(log.id).startsWith('abandon_')" not in texto, (
            "quedó el atajo que solo cambiaba la fila en memoria"
        )
        assert "await api.patch(`/api/auditoria/${log.id}/estado`, { estado })" in texto

    def test_ya_no_hay_datos_de_demo(self):
        texto = _leer(AUDITORIA)

        assert "cliente.anonimo" not in texto
        assert "const logs = ref([])" in texto
        assert "if (Array.isArray(data))" in texto, (
            "con `data.length` un resultado vacío dejaba los 20 eventos de demo"
        )

    def test_muestra_el_producto_manual_creado(self):
        texto = _leer(AUDITORIA)

        assert "producto_manual_creado: 'Producto manual creado'" in texto
        assert "row.event === 'producto_manual_creado'" in texto
        assert "rol_creador" in texto

    def test_el_contador_de_sospechosos_de_hoy_esta_definido(self):
        texto = _leer(AUDITORIA)

        assert "const suspiciousToday = computed(" in texto
        assert "esHoy(l.creada_en)" in texto

    def test_el_filtro_por_area_mapea_los_tipos_del_backend(self):
        texto = _leer(AUDITORIA)

        assert "categoriaDe(e.tipo)" in texto
        assert "result.filter(l => l.categoria === activeFilter.value)" in texto
