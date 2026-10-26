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
        "sqlite:///erp_comercio.db",
    )

    # JWT
    JWT_SECRET: str = os.getenv("JWT_SECRET", "cambiar-en-produccion-uso-clave-segura")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "1200"))  # 20 horas (jornada + cierre caja)

    # Multi-cliente (Docker multi-instance, ver MULTITENANT.md)
    # Cada instancia/cliente fija su MACHINE_ID (el slug) porque en Docker el
    # hostname y la MAC cambian al recrear el contenedor y la licencia se ataría
    # a un ID distinto en cada arranque.
    MACHINE_ID: str = os.getenv("MACHINE_ID", "")
    # Secreto maestro para firmar claves de licencia. Si está vacío se usa el
    # JWT_SECRET de la instancia (comportamiento viejo, válido para desarrollo).
    LICENCIA_SECRET: str = os.getenv("LICENCIA_SECRET", "")
    # En clientes se apaga: evita que el arranque cree/renueve una licencia
    # demo pro de 30 días y que el cliente nunca necesite pagar.
    LICENCIA_AUTO: bool = os.getenv("LICENCIA_AUTO", "true").lower() in ("1", "true", "yes", "on")
    # En clientes se apaga: el admin del cliente no puede emitir ni renovar
    # claves desde la UI.
    LICENCIA_GESTION_LOCAL: bool = os.getenv("LICENCIA_GESTION_LOCAL", "true").lower() in ("1", "true", "yes", "on")
    ADMIN_PASSWORD_INICIAL: str = os.getenv("ADMIN_PASSWORD_INICIAL", "admin")

    # CORS
    CORS_ORIGINS: list = ["*"]  # En producción, restringir al dominio real

    # App
    APP_TITLE: str = "ERP Comercio API"
    APP_VERSION: str = "0.1.0"

    # Scraping
    SCRAPER_TIMEOUT: int = 20
    SCRAPER_CACHE_TTL: int = 900
    SCRAPER_MAX_CONCURRENT: int = int(os.getenv("SCRAPER_MAX_CONCURRENT", "8"))
    SCRAPER_USER_AGENT: str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    )
    # Fuentes a no consultar, separadas por coma: SCRAPER_FUENTES_OFF=supercoco
    # Apagar una fuente que rompio no debería obligar a tocar codigo ni redeploy.
    SCRAPER_FUENTES_OFF: str = os.getenv("SCRAPER_FUENTES_OFF", "")

    # Negocio
    DEFAULT_MARGIN: float = 30.0         # % de margen por defecto
    DEFAULT_ROUNDING: float = 50.0       # Redondeo de precio por defecto

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

    # Backup automático (minutos, 0 = deshabilitado). Prendido por defecto:
    # un respaldo que no se hace no se recupera, y la verificación de
    # salud_service (cada 30 min) avisa por Telegram si algo falla.
    BACKUP_INTERVAL_MIN: int = int(os.getenv("BACKUP_INTERVAL_MIN", "15"))
    BACKUP_KEEP_LOCAL: int = int(os.getenv("BACKUP_KEEP_LOCAL", "5"))  # backups locales a conservar
    # En Docker el repo es de sólo lectura/efímero: los respaldos van a un
    # volumen propio (/data/backups). Vacío = carpeta histórica del repo.
    BACKUP_DIR: str = os.getenv("BACKUP_DIR", "")

    # Datos de demostración (4 productos falsos, proveedor y compra) en una base
    # recién creada. **Apagado por defecto**: un negocio real no quiere arrancar
    # con "Coca Cola 2.25L" cargado como si fuera de él — encima bloquea el
    # código de barras cuando alguien lo borra (ver Fase H). Se prende con
    # SEED_DEMO=true sólo para armar demos.
    SEED_DEMO: bool = os.getenv("SEED_DEMO", "false").lower() in ("1", "true", "yes", "on")

    # Continuidad (Fase G): réplica en vivo de la base con Litestream hacia R2.
    # Se prende por servidor, con LITESTREAM_HABILITADO=true en el unit file,
    # recién después de instalar el servicio litestream. Sin eso, el chequeo de
    # salud no mira nada de la réplica: una máquina sin litestream (desarrollo,
    # una segunda PC) no tiene por qué mandar una alerta falsa.
    LITESTREAM_HABILITADO: bool = os.getenv("LITESTREAM_HABILITADO", "false").lower() in ("1", "true", "yes", "on")

    # IA / LLM — la key interna (SaaS) vive SOLO en entorno y nunca en la DB,
    # asi no se filtra por GET /api/config/ajustes. La key del cliente (BYOK)
    # si va en DB y tiene prioridad sobre esta.
    IA_DEFAULT_API_KEY: str = os.getenv("IA_DEFAULT_API_KEY", "")
    IA_DEFAULT_BASE_URL: str = os.getenv("IA_DEFAULT_BASE_URL", "")
    IA_DEFAULT_MODELO: str = os.getenv("IA_DEFAULT_MODELO", "")
    IA_TIMEOUT: int = int(os.getenv("IA_TIMEOUT", "60"))
    IA_MAX_REINTENTOS: int = int(os.getenv("IA_MAX_REINTENTOS", "2"))


settings = Settings()
