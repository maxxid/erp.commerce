"""
Motor de base de datos SQLAlchemy.

Proporciona:
- engine: conexión a la BD
- SessionLocal: fábrica de sesiones por request
- Base: clase base declarativa para modelos
- get_db: dependency de FastAPI para obtener sesión
"""

import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,
)

# Habilitar FK en SQLite (por defecto desactivadas)
if "sqlite" in settings.DATABASE_URL:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def verificar_db():
    """Verifica que la DB sea la correcta (tablas esenciales existem)."""
    if "sqlite" not in settings.DATABASE_URL:
        return
    with engine.connect() as conn:
        result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        tablas = {r[0] for r in result}
        tablas_esenciales = {"usuarios", "productos", "ventas", "auditoria"}
        faltantes = tablas_esenciales - tablas
        if faltantes:
            logger.warning(
                f"DB puede no ser la correcta. Tablas faltantes: {faltantes}. "
                f"Tablas encontradas: {tablas}. DATABASE_URL: {settings.DATABASE_URL}"
            )
        else:
            logger.info(f"DB verificada OK. Tablas: {sorted(tablas)}")


verificar_db()


def get_db():
    """Dependency de FastAPI: inyecta una sesión de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
