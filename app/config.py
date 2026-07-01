"""Configuración central de la aplicación.

Carga variables desde entorno o usa valores por defecto.
Para producción, configurar mediante variables de entorno.
"""
import os


class Settings:
    """Configuración global accesible como settings.DATABASE_URL, etc."""

    # Base de datos - DEFAULT_ABSOLUTE para evitar fallback a ruta relativa
    # En producción usar variable DATABASE_URL en systemd
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "sqlite:////data/erp/erp_comercio.db",
    )

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cambiar-en-produccion-uso-clave-segura")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "480"))  # 8 horas

    # CORS
    CORS_ORIGINS: list = ["*"]  # En producción, restringir al dominio real

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

    # Cloudflare R2 — Backup remoto
    R2_ENDPOINT: str = os.getenv("R2_ENDPOINT", "")
    R2_ACCESS_KEY: str = os.getenv("R2_ACCESS_KEY", "")
    R2_SECRET_KEY: str = os.getenv("R2_SECRET_KEY", "")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "erp-backups")
    R2_ENABLED: bool = bool(os.getenv("R2_ACCESS_KEY", ""))  # solo si hay credenciales

    # AFIP — Factura Electrónica (pyafipws)
    AFIP_CERT: str = os.getenv("AFIP_CERT", "")          # Ruta al certificado .crt
    AFIP_KEY: str = os.getenv("AFIP_KEY", "")            # Ruta a la clave .key
    AFIP_CUIT: str = os.getenv("AFIP_CUIT", "")
    AFIP_PTO_VTA: int = int(os.getenv("AFIP_PTO_VTA", "1"))
    AFIP_MODE: str = os.getenv("AFIP_MODE", "testing")   # testing | production

    # Backup automático (minutos, 0 = deshabilitado)
    BACKUP_INTERVAL_MIN: int = int(os.getenv("BACKUP_INTERVAL_MIN", "0"))
    BACKUP_KEEP_LOCAL: int = int(os.getenv("BACKUP_KEEP_LOCAL", "5"))  # backups locales a conservar


settings = Settings()
