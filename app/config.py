"""Configuración central de la aplicación.

Carga variables desde entorno o usa valores por defecto.
Para producción, configurar mediante variables de entorno.
"""
import os


class Settings:
    """Configuración global accesible como settings.DATABASE_URL, etc."""

    # Base de datos
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:///erp_comercio.db",
    )

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cambiar-en-produccion-uso-clave-segura")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 horas

    # CORS
    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:5000", "http://127.0.0.1:5173"]

    # App
    APP_TITLE: str = "ERP Comercio API"
    APP_VERSION: str = "0.1.0"

    # Scraping
    SCRAPER_TIMEOUT: int = 20
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )

    # Negocio
    DEFAULT_MARGIN: float = 30.0         # % de margen por defecto
    DEFAULT_ROUNDING: float = 50.0       # Redondeo de precio por defecto
    LOW_STOCK_THRESHOLD: float = 5.0     # Umbral para alerta de stock bajo


settings = Settings()
