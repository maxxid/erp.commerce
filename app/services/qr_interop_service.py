"""Servicio de QR interoperable: EMVCo QRCPS v1.0 (paga cualquier billetera).

El payload se arma según EMVCo LLC - EMV QR Code Specification for Payment
Systems (EMVCo QRCPS) Versión 1.0 (julio 2017), conforme a la Comunicación
BCRA "A" 6425 (texto ordenado SNP - Servicios de pago, punto 4.1):

    - Campo ID 00: Payload Format Indicator = "01"
    - Campo ID 01: Punto de iniciación = "11" (estático) / "12" (dinámico)
    - Campo ID 50: CUIT/CUIL del comercio (campo y dato obligatorios)
    - Campo ID 51: CBU o CVU, o alias (posición de uso exclusivo, dato optativo)
    - Campo ID 53: Moneda de transacción = "032" (ARS)
    - Campo ID 54: Importe (sin separador decimal; exponente ISO 4217, ARS = 2)
    - Campo ID 58: País = "AR"
    - Campo ID 59: Nombre del comercio
    - Campo ID 60: Ciudad del comercio
    - Campo ID 63: CRC-16/CCITT (polinomio 0x1021, init 0xFFFF, 4 hex)

El pago viaja como transferencia inmediata (PCT) a la CBU/CVU codificada, por
eso lo puede pagar cualquier billetera interoperable registrada en el BCRA y
no solo la app de MercadoPago.
"""

import logging
import unicodedata
from typing import Optional

logger = logging.getLogger(__name__)

# Límites de longitud por campo según EMVCo QRCPS v1.0.
_MAX_LEN = {
    "00": 2,
    "01": 2,
    "50": 11,
    "51": 29,
    "53": 3,
    "54": 13,
    "58": 2,
    "59": 25,
    "60": 15,
}


def _ascii(text: str) -> str:
    """Normaliza a ASCII imprimible (EMVCo solo admite 0x20-0x7E)."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    out = []
    for ch in text:
        if 0x20 <= ord(ch) <= 0x7E:
            out.append(ch)
        elif ch in " ,.-_":
            out.append(ch)
        else:
            out.append(" ")
    return " ".join("".join(out).split())


def _tlv(campo_id: str, data: str) -> str:
    data = str(data)
    max_len = _MAX_LEN[campo_id]
    if len(data) > max_len:
        raise ValueError(
            f"Campo {campo_id}: {len(data)} caracteres supera el máximo de {max_len}"
        )
    return f"{campo_id}{len(data):02d}{data}"


def crc16_ccitt(data: str) -> str:
    """CRC-16/CCITT como lo define EMVCo: polinomio 0x1021, init 0xFFFF, sin XOR final."""
    crc = 0xFFFF
    for ch in data:
        crc ^= ord(ch) << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return f"{crc:04X}"


def generar_qr_interoperable(
    cuit: str,
    cuenta: str,
    monto: float,
    nombre_comercio: str,
    ciudad: str = "",
    dinamico: bool = True,
) -> str:
    """Genera el payload EMVCo del QR interoperable (campo 63 CRC incluido).

    Args:
        cuit: CUIT/CUIL del comercio, 11 dígitos (obligatorio).
        cuenta: CBU (22), CVU (23) o alias de la cuenta destino del pago.
        monto: importe en pesos ARS.
        nombre_comercio: razón/denominación corta (max 25 chars ASCII).
        ciudad: Ciudad del comercio (max 15 chars ASCII).
        dinamico: True -> QR con importe (01=12), False -> QR sin importe (01=11).

    Returns:
        String completo listo para renderizar como QR.
    """
    cuit = str(cuit).strip()
    if not cuit.isdigit() or len(cuit) != 11:
        raise ValueError("El CUIT/CUIL debe tener exactamente 11 dígitos")

    cuenta = str(cuenta).strip()
    if not cuenta:
        raise ValueError("Falta la CBU, CVU o alias de la cuenta receptora")
    if len(cuenta) > 29:
        raise ValueError("La CBU/CVU/alias no puede superar 29 caracteres")

    nombre = _ascii(nombre_comercio).strip()
    if not nombre:
        raise ValueError("Falta el nombre del comercio")
    if len(nombre) > 25:
        nombre = nombre[:25]

    if ciudad:
        ciudad = _ascii(ciudad).strip()[:15]

    monto_centavos = None
    if dinamico:
        monto_centavos = int(round(float(monto) * 100))
        if monto_centavos <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        if len(str(monto_centavos)) > 13:
            raise ValueError("El monto es demasiado grande")

    partes = [_tlv("00", "01")]
    partes.append(_tlv("01", "12" if dinamico else "11"))
    partes.append(_tlv("50", cuit))
    partes.append(_tlv("51", cuenta))
    partes.append(_tlv("53", "032"))
    if monto_centavos is not None:
        partes.append(_tlv("54", str(monto_centavos)))
    partes.append(_tlv("58", "AR"))
    partes.append(_tlv("59", nombre))
    if ciudad:
        partes.append(_tlv("60", ciudad))

    payload = "".join(partes) + "6304"
    return payload + crc16_ccitt(payload)