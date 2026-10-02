"""Servicio de QR interoperable: EMVCo QRCPS v1.0 (paga cualquier billetera).

El payload se arma según EMVCo LLC - EMV QR Code Specification for Payment
Systems (EMVCo QRCPS) Versión 1.0 (julio 2017), conforme a la Comunicación
BCRA "A" 6425 (texto ordenado SNP - Servicios de pago, punto 4.1):

    - Campo ID 00: Payload Format Indicator = "01"
    - Campo ID 01: Punto de iniciación = "11" (estático) / "12" (dinámico)
    - Campo ID 50 (template): sub-ID 00 = GUID con la CUIT/CUIL (obligatorio),
      "0011" + CUIT. Este es el formato real que usan los QRs interoperables
      en producción (p. ej. MercadoPago "com.mercadolibre").
    - Campo ID 51 (template, optativo): sub-ID 00 = GUID con la CBU/CVU/alias,
      "00<len><cuenta>". Posición 51 reservada al dato de cuenta destino.
    - Campo ID 52: Merchant Category Code (MCC), obligatorio en EMVCo MPM.
      Default "9700" (mismo valor que usan los QRs interoperables AR reales).
    - Campo ID 53: Moneda de transacción = "032" (ARS)
    - Campo ID 54: Importe en formato NNNN.DD (punto decimal, siempre 2 decimales),
      que es lo que usan los QR de transferencia inmediata en Argentina. No es el
      formato de unidades menores del exponente ISO 4217.
    - Campo ID 58: País = "AR"
    - Campo ID 59: Nombre del comercio
    - Campo ID 60: Ciudad del comercio
    - Campo ID 63: CRC-16/CCITT (polinomio 0x1021, init 0xFFFF, 4 hex).

Validación del CRC verificada contra payloads reales de MercadoPago
(p. ej. "000201010211...630457A8"), cuyo valor se reproduce exactamente.

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
    "52": 4,
    "53": 3,
    "54": 13,
    "58": 2,
    "59": 25,
    "60": 15,
}

# Longitud máxima de CBU/CVU/alias (el dato va envuelto en sub-ID 00 + len).
_MAX_CUENTA = 29

# Pesos de los dígitos verificadores de la CBU. El bloque 1 (banco + sucursal)
# son 7 dígitos con pesos 7,1,3,9,7,1,3 y el bloque 2 (cuenta) son 13 con la
# serie corrida 3,9,7,1. Total 7 + 1 dv + 13 + 1 dv = 22 dígitos.
_PESOS_B1 = [7, 1, 3, 9, 7, 1, 3]
_PESOS_B2 = [3, 9, 7, 1, 3, 9, 7, 1, 3, 9, 7, 1, 3]


def _digito_verificador(bloque: str, pesos: list) -> int:
    suma = sum(int(d) * p for d, p in zip(bloque, pesos))
    resto = 10 - (suma % 10)
    return 0 if resto == 10 else resto


def cbu_es_valida(cbu: str) -> bool:
    """Valida los dígitos verificadores de una CBU/CVU de 22 dígitos.

    Estructura: banco (4) + sucursal (3) + dv1 (1) + cuenta (13) + dv2 (1).
    """
    cbu = str(cbu).strip()
    if len(cbu) != 22 or not cbu.isdigit():
        return False
    b1, dv1 = cbu[0:7], cbu[7]
    b2, dv2 = cbu[8:21], cbu[21]
    return dv1 == str(_digito_verificador(b1, _PESOS_B1)) and dv2 == str(
        _digito_verificador(b2, _PESOS_B2)
    )


def es_alias(cuenta: str) -> bool:
    """El alias no es numérico de 22 dígitos: es un alias del BCRA."""
    cuenta = str(cuenta).strip()
    return not (cuenta.isdigit() and len(cuenta) == 22)


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


def _tlv_template(campo_id: str, guid: str) -> str:
    """Template de información de cuenta: 'XX<len>(00<glen><guid>)'."""
    guid = str(guid)
    inner = f"00{len(guid):02d}{guid}"
    if len(inner) > 99:
        raise ValueError(f"Campo {campo_id}: dato demasiado largo")
    return f"{campo_id}{len(inner):02d}{inner}"


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
    mcc: str = "9700",
) -> str:
    """Genera el payload EMVCo del QR interoperable (campo 63 CRC incluido).

    Args:
        cuit: CUIT/CUIL del comercio, 11 dígitos (obligatorio).
        cuenta: CBU (22), CVU (22) o alias de la cuenta destino del pago.
        monto: importe en pesos ARS.
        nombre_comercio: razón/denominación corta (max 25 chars ASCII).
        ciudad: Ciudad del comercio (max 15 chars ASCII).
        dinamico: True -> QR con importe (01=12), False -> QR sin importe (01=11).
        mcc: Merchant Category Code (4 dígitos, default "9700" como los QRs AR reales).

    Returns:
        String completo listo para renderizar como QR.
    """
    cuit = str(cuit).strip()
    if not cuit.isdigit() or len(cuit) != 11:
        raise ValueError("El CUIT/CUIL debe tener exactamente 11 dígitos")

    cuenta = str(cuenta).strip()
    if not cuenta:
        raise ValueError("Falta la CBU, CVU o alias de la cuenta receptora")
    if len(cuenta) > _MAX_CUENTA:
        raise ValueError(f"La CBU/CVU/alias no puede superar {_MAX_CUENTA} caracteres")
    if cuenta.isdigit() and len(cuenta) == 22 and not cbu_es_valida(cuenta):
        raise ValueError(
            "La CBU/CVU tiene 22 dígitos pero los dígitos verificadores no "
            "coinciden. Revisala en Ajustes: un dígito mal tipeado hace que la "
            "billetera rechace el pago."
        )

    mcc = str(mcc or "9700").strip()
    if not mcc.isdigit() or len(mcc) != 4:
        raise ValueError("El MCC debe tener exactamente 4 dígitos (o '0000')")

    nombre = _ascii(nombre_comercio).strip()
    if not nombre:
        raise ValueError("Falta el nombre del comercio")
    if len(nombre) > _MAX_LEN["59"]:
        nombre = nombre[:_MAX_LEN["59"]]

    if ciudad:
        ciudad = _ascii(ciudad).strip()[:_MAX_LEN["60"]]

    monto_str = None
    if dinamico:
        monto_str = f"{float(monto):.2f}"
        if float(monto_str) <= 0:
            raise ValueError("El monto debe ser mayor a cero")
        if len(monto_str) > _MAX_LEN["54"]:
            raise ValueError("El monto es demasiado grande")

    partes = [_tlv("00", "01")]
    partes.append(_tlv("01", "12" if dinamico else "11"))
    partes.append(_tlv_template("50", cuit))
    partes.append(_tlv_template("51", cuenta))
    partes.append(_tlv("52", mcc))
    partes.append(_tlv("53", "032"))
    if monto_str is not None:
        partes.append(_tlv("54", monto_str))
    partes.append(_tlv("58", "AR"))
    partes.append(_tlv("59", nombre))
    if ciudad:
        partes.append(_tlv("60", ciudad))

    payload = "".join(partes) + "6304"
    return payload + crc16_ccitt(payload)