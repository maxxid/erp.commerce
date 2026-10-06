"""
ERP Comercio — Aplicación principal.

FastAPI + SQLAlchemy + JWT.
Arranca con: uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from app.config import settings
from app.database import engine, Base
from app.models import *  # noqa: F401, F403 — Registrar todos los modelos
from app.routers import auth, productos, categorias, dashboard, caja, clientes, ventas, proveedores, compras, calendario, backups, usuarios, auditoria, licencia, catalogo, ofertas, facturacion, configuracion as config_router, pagos, lotes, denominaciones, reportes, recargas, etiquetas


def crear_app() -> FastAPI:
    """Fábrica de la aplicación FastAPI."""
    app = FastAPI(
        title=settings.APP_TITLE,
        version=settings.APP_VERSION,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Routers
    app.include_router(auth.router)
    app.include_router(productos.router)
    app.include_router(categorias.router)
    app.include_router(dashboard.router)
    app.include_router(caja.router)
    app.include_router(clientes.router)
    app.include_router(ventas.router)
    app.include_router(proveedores.router)
    app.include_router(compras.router)
    app.include_router(calendario.router)
    app.include_router(backups.router)
    app.include_router(usuarios.router)
    app.include_router(auditoria.router)
    app.include_router(licencia.router)
    app.include_router(catalogo.router)
    app.include_router(ofertas.router)
    app.include_router(facturacion.router)
    app.include_router(config_router.router)
    app.include_router(pagos.router)
    app.include_router(lotes.router)
    app.include_router(denominaciones.router)
    app.include_router(reportes.router)
    app.include_router(recargas.router)
    app.include_router(etiquetas.router)

    # Servir el frontend Vue 3 (producción)
    @app.get("/app")
    async def serve_frontend():
        import os
        frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        # Fallback al viejo index.html
        fallback = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
        return FileResponse(fallback)

    # SPA fallback: todas las rutas bajo /app/ sirven el index.html de Vue
    @app.get("/app/{full_path:path}")
    async def serve_vue_spa(full_path: str):
        import os
        frontend_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "dist")
        file_path = os.path.join(frontend_dist, full_path)
        if os.path.exists(file_path) and os.path.isfile(file_path):
            return FileResponse(file_path)
        index_path = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_path):
            return FileResponse(index_path)
        return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html"))

    @app.get("/movil")
    async def serve_movil():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/app")

    # Crear tablas en SQLite (desarrollo). En prod usar Alembic.
    @app.on_event("startup")
    def on_startup():
        Base.metadata.create_all(bind=engine)
        _migrate_new_columns()
        _migrate_lotes_iniciales()
        _seed_denominaciones()
        _seed_database()
        _seed_producto_recarga()
        _start_backup_scheduler()

    return app


def _seed_database():
    """Inserta datos iniciales si la BD está vacía."""
    from app.database import SessionLocal
    from app.models.usuario import Usuario, Sucursal
    from app.models.categoria import Categoria
    from app.models.licencia import Licencia
    from app.auth.security import hash_password
    from app.services.licencia_service import generar_clave
    from datetime import datetime, timezone, timedelta

    db = SessionLocal()
    try:
        if not db.query(Sucursal).first():
            db.add(Sucursal(nombre="Sucursal Principal", direccion="Dirección principal"))
            db.commit()

        if not db.query(Usuario).first():
            db.add(Usuario(
                username="admin",
                password_hash=hash_password("admin"),
                nombre="Administrador",
                rol="admin",
            ))
            db.commit()

        if not db.query(Categoria).first():
            categorias_default = [
                "Almacén", "Bebidas", "Frescos", "Golosinas",
                "Limpieza", "Perfumería", "Otros",
            ]
            for nombre in categorias_default:
                db.add(Categoria(nombre=nombre))
            db.commit()

        # Datos DEMO: productos, proveedor, compra (solo si no hay productos)
        from app.models.producto import Producto
        if not db.query(Producto).first():
            from app.models.proveedor import Proveedor
            from app.models.compra import Compra, CompraItem
            from app.services.compra_service import generar_numero_compra

            demo_productos = [
                {"codigo_barras": "7790895000997", "nombre": "Coca Cola 2.25L", "marca": "Coca Cola", "precio_venta": 2500, "precio_costo": 1800, "categoria_id": 2, "stock": 24},
                {"codigo_barras": "7791234567890", "nombre": "Yerba Mate Playadito 1kg", "marca": "Playadito", "precio_venta": 3200, "precio_costo": 2400, "categoria_id": 1, "stock": 12},
                {"codigo_barras": "7795555444333", "nombre": "Aceite de Girasol Natura 1.5L", "marca": "Natura", "precio_venta": 3800, "precio_costo": 2900, "categoria_id": 1, "stock": 8},
                {"codigo_barras": "7794001234567", "nombre": "Arroz Gallo Oro 1kg", "marca": "Gallo Oro", "precio_venta": 1800, "precio_costo": 1200, "categoria_id": 1, "stock": 30},
            ]
            for p in demo_productos:
                db.add(Producto(
                    codigo_barras=p["codigo_barras"], nombre=p["nombre"], marca=p["marca"],
                    precio_venta=p["precio_venta"], precio_costo=p["precio_costo"],
                    categoria_id=p["categoria_id"], stock_actual=p["stock"],
                    fuente="demo", sku=p["codigo_barras"][:8],
                ))
            db.commit()

            # Proveedor demo
            prov = Proveedor(nombre="Distribuidora Demo SA", cuit="30-99999999-9", telefono="1144445555")
            db.add(prov)
            db.flush()

            # Compra demo (para que los costos tengan fuente)
            compra = Compra(
                numero=generar_numero_compra(db), proveedor_id=prov.id,
                usuario_id=1, sucursal_id=1, estado="recibida",
                subtotal=0, total=0,
            )
            db.add(compra)
            db.flush()
            for prod in db.query(Producto).all():
                total = prod.precio_costo * prod.stock_actual
                db.add(CompraItem(compra_id=compra.id, producto_id=prod.id, cantidad=prod.stock_actual, precio_unitario=prod.precio_costo, subtotal=total))
                compra.subtotal += total
            compra.total = compra.subtotal
            db.commit()

            # Marcar demo como etiquetados
            for prod in db.query(Producto).all():
                prod.precio_etiqueta = prod.precio_venta
            db.commit()

        if not db.query(Licencia).first():
            try:
                from app.services.licencia_service import generar_clave, obtener_machine_id
                mid = obtener_machine_id()
                exp_demo = datetime.now(timezone.utc) + timedelta(days=30)
                db.add(Licencia(
                    clave=generar_clave("DEMO", mid, exp_demo),
                    cliente="DEMO - Licencia de prueba",
                    machine_id=mid,
                    fecha_expiracion=exp_demo,
                    activa=True,
                ))
                db.commit()
            except Exception as e:
                print(f"[Licencia] Error al crear licencia demo: {e}")
        else:
            try:
                from app.services.licencia_service import licencia_valida, obtener_machine_id, generar_clave
                if not licencia_valida(db):
                    mid = obtener_machine_id()
                    exp_demo = datetime.now(timezone.utc) + timedelta(days=30)
                    nueva = Licencia(
                        clave=generar_clave("DEMO-TRIAL", mid, exp_demo),
                        cliente="DEMO-TRIAL - 30 dias de prueba",
                        machine_id=mid,
                        fecha_expiracion=exp_demo,
                        activa=True,
                    )
                    db.add(nueva)
                    db.commit()
            except Exception as e:
                print(f"[Licencia] Error al renovar licencia demo: {e}")

    finally:
        db.close()


app = crear_app()


def _migrate_new_columns():
    """Agrega columnas nuevas a tablas existentes sin borrar datos (SQLite-safe)."""
    from app.database import engine
    import sqlalchemy as sa
    conn = engine.connect()
    try:
        existentes = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(compra_items)"))]
        if "cantidad_recibida" not in existentes:
            conn.execute(sa.text("ALTER TABLE compra_items ADD COLUMN cantidad_recibida FLOAT NOT NULL DEFAULT 0.0"))
            conn.commit()
        existentes_prod = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(productos)"))]
        if "precio_etiqueta" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN precio_etiqueta FLOAT"))
            conn.commit()
        if "observaciones" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN observaciones TEXT"))
            conn.commit()
        if "fecha_vencimiento" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN fecha_vencimiento DATETIME"))
            conn.commit()
        if "flag_revision_stock" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN flag_revision_stock BOOLEAN DEFAULT 0"))
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN deficit_stock FLOAT DEFAULT 0.0"))
            conn.commit()
        if "controla_stock" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN controla_stock BOOLEAN NOT NULL DEFAULT 1"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_productos_controla_stock ON productos (controla_stock)"))
            conn.commit()
        if "es_recarga" not in existentes_prod:
            conn.execute(sa.text("ALTER TABLE productos ADD COLUMN es_recarga BOOLEAN NOT NULL DEFAULT 0"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_productos_es_recarga ON productos (es_recarga)"))
            conn.commit()
        existentes_lic = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(licencias)"))]
        if "machine_id" not in existentes_lic:
            conn.execute(sa.text("ALTER TABLE licencias ADD COLUMN machine_id VARCHAR(200)"))
            conn.commit()
        existentes_conf = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(configuraciones)"))]
        if "valor_texto" not in existentes_conf:
            conn.execute(sa.text("ALTER TABLE configuraciones ADD COLUMN valor_texto TEXT"))
            conn.commit()
        # Extender tabla puente producto_proveedor con datos por-relación
        existentes_pp = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(producto_proveedor)"))]
        for col, tipo in [
            ("codigo_proveedor", "VARCHAR(100)"),
            ("costo", "FLOAT"),
            ("plazo_entrega_dias", "INTEGER"),
            ("es_principal", "INTEGER NOT NULL DEFAULT 0"),
            ("activo", "INTEGER NOT NULL DEFAULT 1"),
            ("notas", "TEXT"),
            ("created_at", "DATETIME"),
            ("updated_at", "DATETIME"),
        ]:
            if col not in existentes_pp:
                conn.execute(sa.text(f"ALTER TABLE producto_proveedor ADD COLUMN {col} {tipo}"))
                conn.commit()
        existentes_ms = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(movimientos_stock)"))]
        if "lote_id" not in existentes_ms:
            conn.execute(sa.text("ALTER TABLE movimientos_stock ADD COLUMN lote_id INTEGER"))
            conn.execute(sa.text("CREATE INDEX IF NOT EXISTS ix_movimientos_stock_lote_id ON movimientos_stock (lote_id)"))
            conn.commit()
        existentes_mc = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(movimientos_caja)"))]
        for col, tipo in [
            ("monto_esperado", "FLOAT"),
            ("monto_confirmado", "FLOAT"),
            ("confirmado_por_id", "INTEGER"),
            ("confirmado_at", "DATETIME"),
            ("fue_automatico", "INTEGER NOT NULL DEFAULT 0"),
            ("comentario_concil", "TEXT"),
            ("saldo_efectivo", "FLOAT"),
            # Egresos de cierre que además apuntan a un tercero (pago a
            # proveedor): el id del proveedor va en referencia_id y el de la
            # sesión acá.
            ("sesion_cierre_id", "INTEGER"),
        ]:
            if col not in existentes_mc:
                conn.execute(sa.text(f"ALTER TABLE movimientos_caja ADD COLUMN {col} {tipo}"))
                conn.commit()
        # venta_items: medio_pago_carga para recargas (opcional, permite no generar egreso)
        existentes_vi = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(venta_items)"))]
        if "medio_pago_carga" not in existentes_vi:
            conn.execute(sa.text("ALTER TABLE venta_items ADD COLUMN medio_pago_carga VARCHAR(30)"))
            conn.commit()
        # Cuentas corrientes con proveedor: saldo cacheado en el maestro
        # (la verdad son las filas de deudas_proveedor y pagos_proveedor).
        existentes_prov = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(proveedores)"))]
        if "saldo_cta_corriente" not in existentes_prov:
            conn.execute(
                sa.text("ALTER TABLE proveedores ADD COLUMN saldo_cta_corriente FLOAT NOT NULL DEFAULT 0.0")
            )
            conn.commit()
        # Rescate de los datos previos a las tablas de deuda y pago.
        #
        # 1) Cada compra no anulada que aún no tiene deuda genera una. Si no, un
        #    comercio que ya venía usando el sistema vería a todos sus
        #    proveedores con saldo cero y recién las compras nuevas le
        #    mostrarían algo.
        # 2) Cada egreso de caja con referencia_tipo='pago_proveedor' se
        #    convierte en un pago. Sin este paso el saldo del proveedor saldría
        #    inflado: las compras generarían deuda pero los pagos ya hechos no se
        #    contabilizarían. Quedan sin deuda asociada, o sea marcados como "sin
        #    verificar" para que el dueño los revise con calma.
        #
        # Sólo corre una vez: si pagos_proveedor ya tiene filas, la migración ya
        # se hizo y no se toca nada.
        if not conn.execute(sa.text("SELECT 1 FROM pagos_proveedor LIMIT 1")).fetchone():
            compras = conn.execute(
                sa.text(
                    "SELECT c.id, c.proveedor_id, c.total, c.numero, c.fecha "
                    "FROM compras c "
                    "WHERE c.estado != 'anulada' "
                    "AND NOT EXISTS (SELECT 1 FROM deudas_proveedor d WHERE d.compra_id = c.id)"
                )
            ).fetchall()
            for c in compras:
                conn.execute(
                    sa.text(
                        "INSERT INTO deudas_proveedor "
                        "(proveedor_id, origen, compra_id, detalle, monto_original, saldo, "
                        " fecha_emision, estado, created_at, updated_at) "
                        "VALUES (:pid, 'compra', :cid, :det, :monto, :monto, :fecha, "
                        "        'pendiente', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
                    ),
                    {
                        "pid": c[1],
                        "cid": c[0],
                        "det": f"Compra {c[3]}",
                        "monto": float(c[2] or 0.0),
                        "fecha": c[4],
                    },
                )
            pagos = conn.execute(
                sa.text(
                    "SELECT m.id, m.referencia_id, m.monto, m.medio_pago, m.created_at, "
                    "       m.usuario_id, m.sucursal_id, m.sesion_cierre_id, p.nombre "
                    "FROM movimientos_caja m "
                    "LEFT JOIN proveedores p ON p.id = m.referencia_id "
                    "WHERE m.tipo = 'egreso' AND m.referencia_tipo = 'pago_proveedor' "
                    "AND m.referencia_id IS NOT NULL "
                    "AND NOT EXISTS (SELECT 1 FROM pagos_proveedor pp WHERE pp.movimiento_caja_id = m.id)"
                )
            ).fetchall()
            for m in pagos:
                conn.execute(
                    sa.text(
                        "INSERT INTO pagos_proveedor "
                        "(proveedor_id, usuario_id, monto, medio_pago, fecha, proveedor_nombre, "
                        " comprobante_nro, descripcion, afecta_arqueo, sesion_cierre_id, "
                        " movimiento_caja_id, anulado, created_at) "
                        "VALUES (:pid, :uid, :monto, :medio, :fecha, :nombre, NULL, "
                        "        'Rescatado del registro de caja anterior', 1, :sesion, :mov, 0, "
                        "        CURRENT_TIMESTAMP)"
                    ),
                    {
                        "pid": m[1],
                        "uid": m[5],
                        "monto": float(m[2] or 0.0),
                        "medio": m[3] or "efectivo",
                        "fecha": m[4],
                        "nombre": m[8],
                        "sesion": m[6],
                        "mov": m[0],
                    },
                )
            # Saldo final derivado de las filas, nunca calculado a mano: el
            # mismo criterio que usa proveedor_pago_service.recalcular_saldo.
            conn.execute(
                sa.text(
                    "UPDATE proveedores SET saldo_cta_corriente = ("
                    "  SELECT COALESCE((SELECT SUM(d.saldo) FROM deudas_proveedor d"
                    "                   WHERE d.proveedor_id = proveedores.id), 0.0)"
                    "  - COALESCE((SELECT SUM(pp.monto) FROM pagos_proveedor pp"
                    "               WHERE pp.proveedor_id = proveedores.id AND pp.anulado = 0), 0.0)"
                    ")"
                )
            )
            conn.commit()
    finally:
        conn.close()


def _migrate_lotes_iniciales():
    """Crea un 'Lote inicial' para cada producto con stock > 0 que aún no tenga lotes.

    Esto preserva el stock existente al activar el sistema de lotes: las ventas
    futuras consumirán primero de este lote (sin vencimiento → FEFO lo manda al
    final), y al recibir nueva mercadería se crearán lotes frescos con vencimiento
    que tendrán prioridad en el despacho.
    """
    from app.database import SessionLocal
    from app.models.producto import Producto
    from app.models.lote import Lote
    from datetime import datetime, timezone, timedelta

    db = SessionLocal()
    try:
        productos_con_stock = (
            db.query(Producto)
            .filter(Producto.activo == True, Producto.stock_actual > 0)
            .all()
        )
        creados = 0
        for prod in productos_con_stock:
            tiene_lotes = db.query(Lote).filter(Lote.producto_id == prod.id).first()
            if tiene_lotes:
                continue
            fecha_vto = prod.fecha_vencimiento
            db.add(Lote(
                producto_id=prod.id,
                codigo_lote="INICIAL",
                cantidad_inicial=prod.stock_actual,
                cantidad_actual=prod.stock_actual,
                costo=prod.precio_costo,
                activo=True,
                notas="Lote creado automáticamente al activar el sistema de lotes/FEFO.",
                fecha_vencimiento=fecha_vto,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            ))
            creados += 1
        if creados:
            db.commit()
            print(f"[Lotes] {creados} lote(s) inicial(es) creado(s) para stock preexistente")
    except Exception as e:
        print(f"[Lotes] Error al crear lotes iniciales: {e}")
        db.rollback()
    finally:
        db.close()


def _seed_denominaciones():
    """Crea las denominaciones de efectivo por defecto si la tabla está vacía."""
    from app.database import SessionLocal
    from app.services import denominacion_service

    db = SessionLocal()
    try:
        creadas = denominacion_service.asegurar_defaults(db)
        if creadas:
            print(f"[Denominaciones] {creadas} denominación(es) por defecto creada(s)")
    except Exception as e:
        print(f"[Denominaciones] Error al crear denominaciones por defecto: {e}")
        db.rollback()
    finally:
        db.close()


def _seed_producto_recarga():
    """Crea el producto de servicio de recarga si todavía no hay ninguno.

    Es idempotente: solo corre la primera vez (o si el usuario lo borró).
    El precio de venta real lo calcula el POS como base + adicional, así que
    el precio del producto es solo un valor de referencia.
    """
    from app.database import SessionLocal
    from app.models.producto import Producto

    db = SessionLocal()
    try:
        if db.query(Producto).filter(Producto.es_recarga == True).first():
            return
        db.add(Producto(
            codigo_barras="REC-SUBE",
            nombre="Recarga SUBE",
            descripcion="Carga de saldo. Se cobra base + adicional; el dinero sale de la cuenta digital configurada.",
            precio_venta=1100,
            precio_costo=1000,
            stock_actual=0,
            controla_stock=False,
            es_recarga=True,
            fuente="sistema",
        ))
        db.commit()
        print("[Recargas] Producto 'Recarga SUBE' creado")
    except Exception as e:
        print(f"[Recargas] Error al crear el producto de recarga: {e}")
        db.rollback()
    finally:
        db.close()


def _start_backup_scheduler():
    """Inicia el scheduler de backups automáticos si está configurado."""
    from app.config import settings
    interval = settings.BACKUP_INTERVAL_MIN
    if interval <= 0:
        return
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from app.services.backup_service import backup_automatico
        scheduler = BackgroundScheduler()
        scheduler.add_job(backup_automatico, "interval", minutes=interval, id="backup_auto")
        scheduler.start()
        print(f"[Backup] Scheduler iniciado: cada {interval} minuto(s)")
    except ImportError:
        print("[Backup] APScheduler no disponible. Instalá: pip install apscheduler")
    except Exception as e:
        print(f"[Backup] Error al iniciar scheduler: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
