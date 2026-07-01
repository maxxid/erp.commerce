"""Generación de CSR (Certificate Signing Request) para AFIP/ARCA.

Usa la librería `cryptography` para generar una clave RSA y un CSR,
sin necesidad de OpenSSL externo.

Flujo:
1. Generar CSR desde el ERP con generar_csr()
2. Descargar el CSR y subirlo a ARCA
3. ARCA devuelve un certificado .crt
4. Subir el certificado al ERP con guardar_certificado()
"""

import base64
from datetime import datetime, timedelta, timezone
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from cryptography.x509.oid import NameOID
from sqlalchemy.orm import Session
from app.services.config_service import set_config, get_config


_ALGORITHM = hashes.SHA256()
_KEY_BITS = 2048


def _encrypt_key(private_key_pem: bytes, secret: str) -> str:
    from cryptography.fernet import Fernet
    import hashlib
    key = hashlib.sha256(secret.encode()).digest()
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.encrypt(private_key_pem).decode()


def _decrypt_key(encrypted: str, secret: str) -> bytes:
    from cryptography.fernet import Fernet
    import hashlib
    key = hashlib.sha256(secret.encode()).digest()
    f = Fernet(base64.urlsafe_b64encode(key))
    return f.decrypt(encrypted.encode())


def generar_csr(db: Session, cuit: str, pto_vta: int, razon_social: str = "") -> dict:
    """Genera una nueva clave privada RSA y un CSR para AFIP/ARCA.

    Args:
        db: sesión de base de datos
        cuit: CUIT sin guiones (11 dígitos)
        pto_vta: punto de venta AFIP
        razon_social: razón social para el CSR (opcional, usa "Sin Nombre" si vacío)

    Returns:
        dict con:
          - csr_pem: texto del CSR en formato PEM (para subir a ARCA)
          - clave_privada_descargable: flag indicando que se puede descargar
          - mensaje: texto informativo
    """
    if not razon_social:
        razon_social = get_config(db, "empresa_nombre") or "Sin Nombre"
    if not cuit or len(cuit) != 11 or not cuit.isdigit():
        raise ValueError("CUIT debe tener 11 dígitos numéricos")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=_KEY_BITS,
        backend=default_backend(),
    )

    csr_builder = x509.CertificateSigningRequestBuilder()
    csr_builder = csr_builder.subject_name(
        x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "AR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "ARGENTINA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "BUENOS AIRES"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, razon_social or "Sin Nombre"),
            x509.NameAttribute(NameOID.COMMON_NAME, razon_social or "Sin Nombre"),
        ])
    )
    csr_builder = csr_builder.add_extension(
        x509.BasicConstraints(ca=False, path_length=None),
        critical=True,
    )

    csr = csr_builder.sign(private_key, _ALGORITHM, default_backend())

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )

    csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode("utf-8")

    _encryption_secret = "erp-afip-key-encryption-v1"
    encrypted_key = _encrypt_key(private_key_pem, _encryption_secret)
    set_config(db, "afip_key", encrypted_key, "Clave privada AFIP (encriptada)")
    guardar_csr(db, csr_pem)

    return {
        "csr_pem": csr_pem.replace("\n", "\\n"),
        "clave_privada_descargable": True,
        "mensaje": (
            "CSR generado. Descargá el archivo .csr y subilo a ARCA. "
            "Una vez que ARCA te dé el certificado .crt, volvé acá y subilo."
        ),
    }


def descargar_clave_privada(db: Session) -> str:
    """Devuelve la clave privada desencriptada para descarga."""
    encrypted = get_config(db, "afip_key")
    if not encrypted:
        raise ValueError("No hay clave privada guardada. Generá un CSR primero.")
    _encryption_secret = "erp-afip-key-encryption-v1"
    return _decrypt_key(encrypted, _encryption_secret).decode("utf-8")


def guardar_certificado(db: Session, cert_pem: str) -> dict:
    """Guarda el certificado (.crt) devuelto por ARCA.

    Args:
        db: sesión de base de datos
        cert_pem: contenido del archivo .crt en formato PEM

    Returns:
        dict con info del certificado (subject, expiry, etc.)
    """
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
    except Exception as e:
        raise ValueError(f"Certificado inválido: {e}")

    subject_cn = ""
    for attr in cert.subject:
        if attr.oid == NameOID.COMMON_NAME:
            subject_cn = attr.value

    expiry = cert.not_valid_after_utc
    days_left = (expiry - datetime.now(timezone.utc)).days

    set_config(db, "afip_cert", cert_pem, f"Certificado AFIP (subject: {subject_cn})")

    return {
        "subject": subject_cn,
        "valido_hasta": expiry.strftime("%Y-%m-%d"),
        "dias_restantes": days_left,
        "mensaje": f"Certificado guardado. Válido hasta {expiry.strftime('%d/%m/%Y')} ({days_left} días).",
    }


def guardar_csr(db: Session, csr_pem: str):
    set_config(db, "afip_csr", csr_pem, "CSR AFIP generado (PEM)")


def get_csr_guardado(db: Session) -> str | None:
    return get_config(db, "afip_csr")


def get_cert_info(db: Session) -> dict | None:
    """Lee info del certificado guardado, o None si no hay."""
    cert_pem = get_config(db, "afip_cert")
    if not cert_pem:
        return None
    try:
        cert = x509.load_pem_x509_certificate(cert_pem.encode(), default_backend())
        for attr in cert.subject:
            if attr.oid == NameOID.COMMON_NAME:
                cn = attr.value
        return {
            "subject": cn,
            "valido_hasta": cert.not_valid_after_utc.strftime("%Y-%m-%d"),
            "dias_restantes": (cert.not_valid_after_utc - datetime.now(timezone.utc)).days,
        }
    except Exception:
        return None
