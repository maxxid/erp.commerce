"""Tests de la ficha PDF de analisis de precios.

Se arma el dict que devuelve analisis_precios_service y se verifica que
reportlab genere un PDF valido. El caso importante es que no revienta cuando
el producto no tiene historial, proveedores ni precios online.
"""

from app.services.analisis_precios_pdf import generar_analisis_precios_pdf


def _base(**overrides):
    analisis = {
        "producto": {
            "id": 1,
            "codigo_barras": "7790001234567",
            "nombre": "Café Molido 1kg",
            "marca": "Nescafé",
            "precio_venta": 30000.0,
        },
        "precios_online": [],
        "online": None,
        "historial": [],
        "proveedores": [],
        "ultimo_costo": None,
        "mejor_historico": None,
        "mejor_oferta_proveedor": None,
        "ahorro_vs_ultimo_costo": None,
        "ahorro_vs_mejor_historico": None,
        "margen_actual": None,
        "tiene_historico": False,
    }
    analisis.update(overrides)
    return analisis


def _con_datos():
    historial = [
        {
            "compra_id": 10,
            "numero": "C-000010",
            "fecha": "2025-12-12T10:00:00",
            "estado": "recibida",
            "proveedor_id": 1,
            "proveedor_nombre": "Distribuidora Norte",
            "precio_unitario": 700.0,
            "cantidad": 10.0,
            "cantidad_recibida": 10.0,
            "subtotal": 7000.0,
        },
        {
            "compra_id": 11,
            "numero": "C-000011",
            "fecha": "2026-01-20T09:30:00",
            "estado": "parcial",
            "proveedor_id": 2,
            "proveedor_nombre": "Mayorista Sur",
            "precio_unitario": 2500.0,
            "cantidad": 24.0,
            "cantidad_recibida": 20.0,
            "subtotal": 60000.0,
        },
    ]
    proveedores = [
        {
            "proveedor_id": 1,
            "nombre": "Distribuidora Norte",
            "costo_actual": 1100.0,
            "plazo_entrega_dias": 3,
            "es_principal": True,
            "ultimo_precio_pagado": 700.0,
            "ultima_fecha_pago": "2025-12-12T10:00:00",
        },
        {
            "proveedor_id": 2,
            "nombre": "Mayorista Sur",
            "costo_actual": 950.0,
            "plazo_entrega_dias": None,
            "es_principal": False,
            "ultimo_precio_pagado": 2500.0,
            "ultima_fecha_pago": "2026-01-20T09:30:00",
        },
    ]
    precios = [
        {"fuente": "vea", "precio": 1500.0, "nombre": "Café", "descuento": None},
        {"fuente": "carrefour", "precio": 1200.0, "nombre": "Café", "descuento": {
            "activo": True, "precio_original": 1600.0, "precio_oferta": 1200.0}},
    ]
    return _base(
        precios_online=precios,
        online={"fuente": "carrefour", "precio": 1200.0},
        historial=historial,
        proveedores=proveedores,
        ultimo_costo=historial[1],
        mejor_historico=historial[0],
        mejor_oferta_proveedor=950.0,
        tiene_historico=True,
        margen_actual={"precio_venta": 30000.0, "precio_costo": 1200.0,
                        "utilidad": 28800.0, "porcentaje": 96.0, "positivo": True},
    )


def _es_pdf(valor):
    return isinstance(valor, bytes) and valor.startswith(b"%PDF") and len(valor) > 500


class TestGeneracion:
    def test_genera_pdf_valido(self):
        assert _es_pdf(generar_analisis_precios_pdf(_con_datos()))

    def test_genera_pdf_sin_historial(self):
        """Un producto nuevo no debe romper la descarga."""
        assert _es_pdf(generar_analisis_precios_pdf(_base()))

    def test_genera_pdf_solo_con_historial(self):
        analisis = _base(historial=_con_datos()["historial"], tiene_historico=True)
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_genera_pdf_solo_con_proveedores(self):
        analisis = _base(proveedores=_con_datos()["proveedores"], mejor_oferta_proveedor=950.0)
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_genera_pdf_solo_con_precios_online(self):
        analisis = _base(precios_online=_con_datos()["precios_online"],
                         online={"fuente": "carrefour", "precio": 1200.0})
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_sin_producto_no_revienta(self):
        analisis = _base()
        analisis["producto"] = {}
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_precios_nulos_no_revientan(self):
        analisis = _con_datos()
        analisis["online"] = None
        analisis["mejor_historico"] = None
        analisis["ultimo_costo"] = None
        assert _es_pdf(generar_analisis_precios_pdf(analisis))


class TestRobustez:
    def test_escapa_caracteres_de_marcado(self):
        """Un nombre con & o < no debe romper el PDF ni inyectar marcado."""
        analisis = _base()
        analisis["producto"]["nombre"] = "Jabón & Limpia <b>x</b>"
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_escapa_nombres_de_proveedor(self):
        analisis = _con_datos()
        analisis["proveedores"][0]["nombre"] = "A&B <Dist>"
        analisis["historial"][0]["proveedor_nombre"] = "A&B <Dist>"
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_precios_grandes(self):
        analisis = _con_datos()
        analisis["precios_online"][0]["precio"] = 1234567.89
        analisis["proveedores"][0]["costo_actual"] = 99999999.0
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_nombre_muy_largo(self):
        analisis = _con_datos()
        analisis["producto"]["nombre"] = "Producto " * 80
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_fechas_invalidas_no_revientan(self):
        analisis = _con_datos()
        analisis["historial"][0]["fecha"] = None
        analisis["proveedores"][0]["ultima_fecha_pago"] = "no-es-fecha"
        assert _es_pdf(generar_analisis_precios_pdf(analisis))

    def test_cantidad_decimal(self):
        analisis = _con_datos()
        analisis["historial"][0]["cantidad_recibida"] = 2.5
        assert _es_pdf(generar_analisis_precios_pdf(analisis))
