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
from app.routers import auth, productos, categorias, dashboard, caja, clientes, ventas, proveedores, compras, calendario, backups, usuarios, auditoria, licencia, catalogo, ofertas, facturacion, configuracion as config_router


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
        _seed_database()
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
        existentes_lic = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(licencias)"))]
        if "machine_id" not in existentes_lic:
            conn.execute(sa.text("ALTER TABLE licencias ADD COLUMN machine_id VARCHAR(200)"))
            conn.commit()
        existentes_conf = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(configuraciones)"))]
        if "valor_texto" not in existentes_conf:
            conn.execute(sa.text("ALTER TABLE configuraciones ADD COLUMN valor_texto TEXT"))
            conn.commit()
    finally:
        conn.close()


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
