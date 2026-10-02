"""Tests del QR interoperable (EMVCo QRCPS v1.0, Comunicación BCRA "A" 6425).

La norma exige, para QR generados por el propio comercio:

  - CUIT/CUIL del comercio en el campo 50 (obligatorio, dato obligatorio),
  - campo 51 reservado en exclusiva para el Alias/CBU (reserva obligatoria,
    contenido opcional),
  - CRC-16/CCITT (polinomio 0x1021, valor inicial 0xFFFF) sobre todo el
    payload, incluido el identificador y longitud del propio campo 63.

Lo que más importa acá es la CBU. Un dígito mal tipeado produce un QR con
estructura y checksum correctos que igual rechaza la billetera, porque el
dígito verificador no cierra. Como `qr_interop_cuenta` se carga a mano desde
Ajustes, conviene fallar en el backend al generar el QR y no dejar que el
rechazo llegue al cliente.

El checksum se contrasta contra el ejemplo publicado en el Boletín CIMPRA 525
(Anexo I), que es el mismo que usa la docstring del servicio.
"""

import pytest

from app.services import qr_interop_service as q


CUIT = "20123456789"
CUENTA = "0140356690000000123457"  # CBU de 22 digitos con DV correctos


def parsear(payload):
    """Desarma el TLV plano y devuelve {tag: valor}."""
    campos = {}
    i = 0
    while i < len(payload):
        tag = payload[i : i + 2]
        largo = int(payload[i + 2 : i + 4])
        campos[tag] = payload[i + 4 : i + 4 + largo]
        i += 4 + largo
    return campos


class TestCrc:
    def test_reproduce_el_ejemplo_del_boletin_525(self):
        # Anexo I, Boletín CIMPRA 525, desglose oficial.
        oficial = (
            "000201010211"
            "4139" + "0016" + "com.adquirente" + "0115" + "info_adquirente"
            "5013" + "0009" + "123456789"
            "5204" + "9700"
            "5303" + "032"
            "5802" + "AR"
            "5909" + "FULL NAME"
            "6010" + "CITY LEGAL"
            "6304"
        )
        assert q.crc16_ccitt(oficial) == "5BE9"

    def test_es_crc16_ccitt_false(self):
        # poly 0x1021, init 0xFFFF, sin reflexion, sin XOR final.
        assert q.crc16_ccitt("123456789") == "29B1"

    def test_el_crc_cubre_el_prefijo_6304(self):
        payload = q.generar_qr_interoperable(CUIT, CUENTA, 1000, "MI COMERCIO")
        assert payload.endswith("6304" + q.crc16_ccitt(payload[:-4]))


class TestValidacionCbu:
    @pytest.mark.parametrize(
        "cuenta",
        [
            "0140356690000000123457",  # DV correctos
        ],
    )
    def test_acepta_cbu_con_dv_correctos(self, cuenta):
        assert q.cbu_es_valida(cuenta) is True

    @pytest.mark.parametrize(
        "cuenta",
        [
            "0140356690000000123458",  # DV2 +1
            "0140356690000000123447",  # DV2 desfasado
            "0140356680000000123457",  # DV1 +1
        ],
    )
    def test_rechaza_cbu_con_dv_roto(self, cuenta):
        assert q.cbu_es_valida(cuenta) is False

    @pytest.mark.parametrize(
        "cuenta",
        ["123", "014035669000000012345", "01403566900000001234570", "mi.empresa.erp", ""],
    )
    def test_rechaza_lo_que_no_es_cbu(self, cuenta):
        assert q.cbu_es_valida(cuenta) is False

    def test_es_alias_no_es_cbu(self):
        assert q.es_alias("mi.empresa.erp") is True
        assert q.es_alias(CUENTA) is False


class TestPayload:
    def test_cumple_la_estructura_de_la_comunicacion_6425(self):
        payload = q.generar_qr_interoperable(
            cuit=CUIT,
            cuenta=CUENTA,
            monto=1234.56,
            nombre_comercio="MI COMERCIO",
            ciudad="CORDOBA",
            dinamico=True,
        )
        campos = parsear(payload)

        assert campos["00"] == "01"
        assert campos["01"] == "12"
        # 50 obligatorio con la CUIT del comercio.
        assert campos["50"] == "0011" + CUIT
        # 51 de uso exclusivo para el alias/CBU.
        assert campos["51"] == "0022" + CUENTA
        assert campos["52"] == "9700"
        assert campos["53"] == "032"
        assert campos["54"] == "1234.56"
        assert campos["58"] == "AR"
        assert campos["59"] == "MI COMERCIO"
        assert campos["60"] == "CORDOBA"
        assert len(campos["63"]) == 4

    def test_campos_ordenados_por_id(self):
        payload = q.generar_qr_interoperable(CUIT, CUENTA, 100, "X")
        ids = [t for t in parsear(payload)]
        assert ids == sorted(ids)

    def test_dinamico_incluye_monto_y_estatico_no(self):
        dinamico = parsear(
            q.generar_qr_interoperable(CUIT, CUENTA, 100, "X", dinamico=True)
        )
        estatico = parsear(
            q.generar_qr_interoperable(CUIT, CUENTA, 100, "X", dinamico=False)
        )

        assert dinamico["01"] == "12"
        assert dinamico["54"] == "100.00"
        # Estatico sin importe: el cliente lo ingresa en la billetera.
        assert estatico["01"] == "11"
        assert "54" not in estatico

    def test_el_campo_51_acepta_alias(self):
        payload = q.generar_qr_interoperable(
            cuit=CUIT, cuenta="mi.empresa.erp", monto=100, nombre_comercio="X"
        )
        assert parsear(payload)["51"] == "0014mi.empresa.erp"


class TestErrores:
    def test_cbu_de_22_digitos_con_dv_roto_falla(self):
        with pytest.raises(ValueError, match="verificadores"):
            q.generar_qr_interoperable(
                CUIT, "0140356690000000123458", 100, "MI COMERCIO"
            )

    @pytest.mark.parametrize(
        "cuit,error",
        [
            ("123", "11 d"),
            ("2012345678a", "11 d"),
            ("", "11 d"),
        ],
    )
    def test_cuit_invalida(self, cuit, error):
        with pytest.raises(ValueError, match=error):
            q.generar_qr_interoperable(cuit, CUENTA, 100, "X")

    def test_monto_no_positivo(self):
        with pytest.raises(ValueError, match="mayor a cero"):
            q.generar_qr_interoperable(CUIT, CUENTA, 0, "X")

    def test_sin_nombre_de_comercio(self):
        with pytest.raises(ValueError, match="nombre del comercio"):
            q.generar_qr_interoperable(CUIT, CUENTA, 100, "   ")

    def test_nombre_se_recorta_a_25_caracteres(self):
        payload = q.generar_qr_interoperable(CUIT, CUENTA, 100, "N" * 40)
        assert len(parsear(payload)["59"]) == 25

    def test_nombre_con_acentos_se_normaliza_a_ascii(self):
        payload = q.generar_qr_interoperable(CUIT, CUENTA, 100, "Panadería Añejo")
        nombre = parsear(payload)["59"]
        assert nombre.isascii()
        assert "Panaderia" in nombre