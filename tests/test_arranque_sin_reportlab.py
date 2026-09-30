"""La app tiene que arrancar aunque falte reportlab.

Esto paso en produccion el 29/09/2026: el venv del server no tenia reportlab,
y como el import era duro y a nivel de modulo, la cadena entera se caia:

    app.main -> app.routers.productos -> analisis_precios_pdf -> reportlab

uvicorn no arrancaba, nginx no encontraba upstream, 502 para toda la app. Y no
por el ultimo commit: el servicio venia corriendo con el codigo viejo en
memoria desde antes de que existiera ese modulo, y un restart de deploy lo
obligo a importar todo de cero.

Un PDF no puede tirar abajo el POS.

Los chequeos corren en un subproceso a proposito. Recargar `app.*` en el
proceso de tests resetea el cache global de lookup_service del que dependen
otros tests, y ademas importar app.main toca la base.
"""

import subprocess
import sys
import textwrap

SCRIPT = textwrap.dedent("""
    import builtins, sys
    real = builtins.__import__
    def bloqueado(nombre, *a, **k):
        if nombre == "reportlab" or nombre.startswith("reportlab."):
            raise ImportError("No module named '%s'" % nombre)
        return real(nombre, *a, **k)
    builtins.__import__ = bloqueado

    main = __import__("app.main", fromlist=["app"])
    print("RUTAS", len(main.app.routes))

    __import__("app.routers.productos", fromlist=["x"])
    print("PRODUCTOS_OK")

    pdf = __import__("app.services.analisis_precios_pdf", fromlist=["x"])
    print("DISPONIBLE", pdf.REPORTLAB_DISPONIBLE)
    # Los estilos se usan como default de argumento en helpers como
    # _p(texto, style=C_10), y los defaults se evaluan al definir la funcion, o
    # sea al importar. Si no existieran, el import reventaria con NameError y la
    # app seguiria sin arrancar.
    print("ESTILOS", pdf.C_10, pdf.ANCHO_UTIL)
    try:
        pdf.generar_analisis_precios_pdf({"producto": {"nombre": "Cafe"}})
    except pdf.ReportlabNoDisponible as e:
        print("MENSAJE", "pip install" in str(e) and "reportlab" in str(e))
    else:
        print("MENSAJE False")
""")


def _correr():
    proc = subprocess.run(
        [sys.executable, "-c", SCRIPT],
        capture_output=True,
        text=True,
    )
    return proc


def test_app_arranca_sin_reportlab():
    """Lo que importaba a proposito: la app completa levanta sin reportlab."""
    proc = _correr()
    salida = proc.stdout
    assert "RUTAS" in salida, f"no arranco:\n{proc.stdout}\n{proc.stderr}"
    assert "PRODUCTOS_OK" in salida, f"router de productos no importo:\n{proc.stderr}"
    assert "ModuleNotFoundError" not in proc.stderr
    assert "NameError" not in proc.stderr

    line_rutas = next(l for l in salida.splitlines() if l.startswith("RUTAS"))
    assert int(line_rutas.split()[1]) > 0, "la app arranco sin rutas registradas"


def test_sin_reportlab_el_pdf_falla_con_mensaje_accionable():
    proc = _correr()
    salida = proc.stdout
    assert "DISPONIBLE False" in salida, salida
    # Los estilos existen pero valen None, para que el import no reviente.
    assert "ESTILOS None None" in salida, salida
    assert "MENSAJE True" in salida, (
        "el error del PDF tiene que decir que instalar y como, no ser un "
        f"traceback generico:\n{salida}"
    )


def test_con_reportlab_el_pdf_sigue_andando():
    """Guarda que el import defensivo no rompio el camino normal."""
    proc = subprocess.run(
        [sys.executable, "-c", textwrap.dedent("""
            from app.services.analisis_precios_pdf import (
                REPORTLAB_DISPONIBLE, C_10, GRIS, generar_analisis_precios_pdf,
            )
            assert REPORTLAB_DISPONIBLE is True
            assert C_10 is not None and GRIS is not None
            analisis = {
                "producto": {"id": 1, "codigo_barras": "7790001234567",
                             "nombre": "Cafe", "marca": "X", "precio_venta": 100.0},
                "precios_online": [], "online": None, "historial": [],
                "proveedores": [], "ultimo_costo": None, "mejor_historico": None,
                "mejor_oferta_proveedor": None, "ahorro_vs_ultimo_costo": None,
                "ahorro_vs_mejor_historico": None, "margen_actual": None,
                "tiene_historico": False,
            }
            assert generar_analisis_precios_pdf(analisis).startswith(b"%PDF")
            print("PDF_OK")
        """)],
        capture_output=True,
        text=True,
    )
    assert "PDF_OK" in proc.stdout, f"{proc.stdout}\n{proc.stderr}"
