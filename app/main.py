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
from app.routers import auth, productos, categorias, dashboard, caja, clientes, ventas, proveedores, compras, calendario, backups, usuarios, auditoria, licencia, catalogo


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

    # Servir el frontend
    @app.get("/app")
    async def serve_frontend():
        import os
        frontend_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "index.html")
        return FileResponse(frontend_path)

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
        existentes_lic = [row[1] for row in conn.execute(sa.text("PRAGMA table_info(licencias)"))]
        if "machine_id" not in existentes_lic:
            conn.execute(sa.text("ALTER TABLE licencias ADD COLUMN machine_id VARCHAR(200)"))
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
