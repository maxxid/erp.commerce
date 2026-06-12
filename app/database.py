"""
Motor de base de datos SQLAlchemy.

Proporciona:
- engine: conexión a la BD
- SessionLocal: fábrica de sesiones por request
- Base: clase base declarativa para modelos
- get_db: dependency de FastAPI para obtener sesión
"""

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in settings.DATABASE_URL else {},
    echo=False,  # Cambiar a True para debuggear SQL
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


def get_db():
    """Dependency de FastAPI: inyecta una sesión de BD por request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
