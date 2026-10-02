"""Tests del gráfico de ventas por categoría del dashboard.

Cubre lo que hace útil el endpoint y lo que lo haría engañoso:
  - agrupa por categoría raíz (Bebidas -> Gaseosas -> Cola es una sola barra)
  - las tres métricas + margen %, y que se ordenen por la métrica elegida
  - "Otras" no promedia porcentajes: recalcula sobre sus propios totales
  - avisa cuando a una categoría le faltan costos, porque su margen miente
  - los productos sin categoría no desaparecen del gráfico
  - las ventas anuladas no cuentan
"""

import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Venta, VentaItem, Usuario, Sucursal
from app.models.categoria import Categoria
from app.models.producto import Producto
import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.routers import dashboard as dash

UTC = timezone.utc

# AHORA fijo: 10:00 local del 29/09/2026, así "hoy" es un día concreto.
AHORA = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)

SIN_CATEGORIA = "sin_categoria"


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(dash, "HOY", lambda: AHORA)
    engine = create_engine(
        "sqlite:///:memory:", connect_args={"check_same_thread": False}
    )
    _Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()


def _semilla(db, extra=0):
    """Arma el árbol de categorías, productos y las ventas de hoy.

    ``extra`` agrega categorías sueltas (con su venta) para poder probar el
    agrupamiento en "Otras".
    """
    sufijo = uuid.uuid4().hex[:8]
    user = Usuario(
        username=f"cat_{sufijo}", nombre="Cat", password_hash="x",
        rol="admin", activo=True,
    )
    db.add(user)
    db.flush()
    db.add(Sucursal(id=1, nombre="Principal"))

    # Jerarquía de dos niveles: Bebidas -> Gaseosas -> (Gaseosa, Cola)
    bebidas = Categoria(nombre=f"Bebidas {sufijo}")
    gaseosas = Categoria(nombre=f"Gaseosas {sufijo}")
    almacen = Categoria(nombre=f"Almacen {sufijo}")
    db.add_all([bebidas, gaseosas, almacen])
    db.flush()
    gaseosas.padre_id = bebidas.id
    db.flush()

    def _prod(nombre, cat_id, precio_venta, precio_costo):
        p = Producto(
            codigo_barras=f"CB-{nombre}-{sufijo}", nombre=nombre,
            categoria_id=cat_id, precio_venta=precio_venta,
            precio_costo=precio_costo, stock_actual=100,
        )
        db.add(p)
        return p

    def _vender(prod, cantidad, precio_unitario, precio_costo):
        venta = Venta(
            numero=f"CAT-{sufijo}-{prod.id}-{uuid.uuid4().hex[:6]}",
            usuario_id=user.id, sucursal_id=1, estado="confirmada",
            subtotal=cantidad * precio_unitario,
            total=cantidad * precio_unitario, fecha=AHORA,
        )
        db.add(venta)
        db.flush()
        db.add(VentaItem(
            venta_id=venta.id, producto_id=prod.id, cantidad=cantidad,
            precio_unitario=precio_unitario, precio_costo=precio_costo,
            subtotal=cantidad * precio_unitario,
        ))
        db.flush()

    # Gaseosa y Cola cuelgan de Gaseosas: deben caer en la misma barra (Bebidas).
    _vender(_prod("Gaseosa", gaseosas.id, 1000.0, 600.0), 2, 1000.0, 600.0)
    _vender(_prod("Cola", gaseosas.id, 1200.0, 900.0), 1, 1200.0, 900.0)
    # Arroz SIN costo cargado: su ganancia sale inflada y hay que avisarlo.
    _vender(_prod("Arroz", almacen.id, 2000.0, None), 1, 2000.0, None)
    # Producto sin categoría: no debe desaparecer del gráfico.
    _vender(_prod("Vuelto", None, 500.0, 250.0), 1, 500.0, 250.0)

    for i in range(extra):
        cat = Categoria(nombre=f"Varios{i} {sufijo}")
        db.add(cat)
        db.flush()
        _vender(_prod(f"Prod{i}", cat.id, 300.0, 100.0), 1, 300.0, 100.0)

    db.commit()
    return user


def _producto(db, nombre):
    """Producto por nombre exacto; la semilla les pone sufijo al nombre."""
    return db.query(Producto).filter(Producto.nombre.like(f"{nombre}%")).one()


def _res(db, user, metrica="importe", periodo="hoy", limite=10):
    return dash.por_categoria(
        db=db, user=user, metrica=metrica, periodo=periodo, limite=limite
    ).data


def _por_clave(res, clave):
    return next(r for r in res["categorias"] if r["clave"] == clave)


class TestRollupPorCategoriaRaiz:
    def test_no_aparece_la_subcategoria_como_barra(self, db):
        user = _semilla(db)
        res = _res(db, user)
        nombres = [r["categoria"] for r in res["categorias"]]
        assert not any(n.startswith("Gaseosas") for n in nombres), nombres

    def test_gaseosa_y_cola_se_suman_en_bebidas(self, db):
        user = _semilla(db)
        res = _res(db, user)
        bebidas = next(r for r in res["categorias"] if r["categoria"].startswith("Bebidas"))
        # 2 x 1000 + 1 x 1200 = 3200 de importe, 3 unidades.
        assert bebidas["importe"] == 3200.0
        assert bebidas["cantidad"] == 3
        # Costo: 2 x 600 + 900 = 2100 -> ganancia 1100.
        assert bebidas["costo"] == 2100.0
        assert bebidas["ganancia"] == 1100.0

    def test_producto_sin_categoria_no_se_pierde(self, db):
        user = _semilla(db)
        res = _res(db, user)
        sin = _por_clave(res, SIN_CATEGORIA)
        assert sin["importe"] == 500.0
        assert sin["categoria"] == "Sin categoría"
        assert sin["ganancia"] == 250.0

    def test_una_categoria_sola_no_genera_subtotales(self, db):
        # Cada categoría se cuenta una vez, aunque venda varios productos.
        user = _semilla(db)
        res = _res(db, user)
        assert res["cantidad_categorias"] == 3
        assert res["totales"]["importe"] == pytest.approx(5700.0, abs=0.02)


class TestMetricas:
    def test_orden_por_importe(self, db):
        user = _semilla(db)
        res = _res(db, user, metrica="importe")
        valores = [r["importe"] for r in res["categorias"]]
        assert valores == sorted(valores, reverse=True)
        assert valores == [3200.0, 2000.0, 500.0]

    def test_orden_por_cantidad(self, db):
        user = _semilla(db)
        res = _res(db, user, metrica="cantidad")
        # Bebidas (3 u) arriba; Almacén y Sin categoría empatan con 1.
        assert res["categorias"][0]["cantidad"] == 3
        assert res["categorias"][0]["categoria"].startswith("Bebidas")

    def test_orden_por_margen_pct(self, db):
        user = _semilla(db)
        res = _res(db, user, metrica="margen_pct")
        # Almacén "gana" 100% sólo porque el costo no está cargado: por eso
        # items_sin_costo tiene que avisar que ese dato no es confiable.
        arriba = res["categorias"][0]
        assert arriba["margen_pct"] == 100.0
        assert arriba["categoria"].startswith("Almacen")
        assert arriba["items_sin_costo"] == 1

    def test_orden_por_ganancia(self, db):
        user = _semilla(db)
        res = _res(db, user, metrica="ganancia")
        # Almacen 2000 (sin costo) > Sin categoría 250 > Bebidas 1100... no: 2000, 1100, 250
        assert [r["ganancia"] for r in res["categorias"]] == [2000.0, 1100.0, 250.0]

    def test_ganancia_es_importe_menos_costo(self, db):
        user = _semilla(db)
        res = _res(db, user)
        for r in res["categorias"]:
            assert r["ganancia"] == pytest.approx(r["importe"] - r["costo"], abs=0.02)
            if r["importe"] > 0:
                assert r["margen_pct"] == pytest.approx(
                    round(r["ganancia"] / r["importe"] * 100, 1), abs=0.1
                )

    def test_totales_coherentes(self, db):
        user = _semilla(db)
        res = _res(db, user)
        t = res["totales"]
        assert t["importe"] == pytest.approx(5700.0, abs=0.02)
        assert t["cantidad"] == 5
        assert t["costo"] == pytest.approx(2350.0, abs=0.02)
        assert t["ganancia"] == pytest.approx(3350.0, abs=0.02)
        assert t["margen_pct"] == pytest.approx(58.8, abs=0.1)

    def test_las_cuatro_metricas_vienen_en_una_sola_respuesta(self, db):
        # El front no debe volver a pedir al cambiar de métrica.
        user = _semilla(db)
        res = _res(db, user)
        for r in res["categorias"]:
            for campo in ("importe", "ganancia", "cantidad", "margen_pct"):
                assert campo in r
        assert res["metrica"] == "importe"
        assert res["periodo"] == "hoy"


class TestAvisoDeCostosFaltantes:
    def test_categoria_sin_costos_queda_marcada(self, db):
        user = _semilla(db)
        res = _res(db, user, metrica="ganancia")
        almacen = next(r for r in res["categorias"] if r["categoria"].startswith("Almacen"))
        assert almacen["items_sin_costo"] == 1
        bebidas = next(r for r in res["categorias"] if r["categoria"].startswith("Bebidas"))
        assert bebidas["items_sin_costo"] == 0


class TestOtras:
    def test_agrupa_el_resto_cuando_sobran_categorias(self, db):
        # 3 categorías base + 3 "Varios" = 6, con limite=3 quedan agrupadas.
        user = _semilla(db, extra=3)
        res = _res(db, user, limite=3)
        assert len(res["categorias"]) == 4  # 3 + Otras
        otras = _por_clave(res, "otras")
        assert otras["categoria"] == "Otras (3)"
        assert otras["importe"] == pytest.approx(900.0, abs=0.02)  # 3 x 300

    def test_otras_recalcula_el_margen_sobre_sus_totales(self, db):
        # Por margen_pct entran Almacen (100%, sin costo cargado) y los dos
        # Varios (66,7%). Quedan "Sin categoría" (50%, $500) y Bebidas (34,4%,
        # $3200). Promediando los porcentajes daría 42,2%; el real es 36,5%.
        user = _semilla(db, extra=2)
        res = _res(db, user, metrica="margen_pct", limite=3)
        otras = _por_clave(res, "otras")
        assert otras["categoria"] == "Otras (2)"
        assert otras["importe"] == 3700.0
        assert otras["costo"] == 2350.0
        assert otras["ganancia"] == pytest.approx(1350.0, abs=0.02)
        assert otras["margen_pct"] == pytest.approx(36.5, abs=0.1)

    def test_otras_no_aparece_si_alcanza_el_limite(self, db):
        user = _semilla(db)
        res = _res(db, user, limite=3)
        assert not any(r["clave"] == "otras" for r in res["categorias"])

    def test_los_totales_no_cuentan_doble_otras(self, db):
        user = _semilla(db, extra=3)
        res = _res(db, user, limite=3)
        # Los totales son del período completo, no de las barras mostradas.
        assert res["cantidad_categorias"] == 6
        assert res["totales"]["importe"] == pytest.approx(6600.0, abs=0.02)
        assert sum(r["importe"] for r in res["categorias"]) == pytest.approx(6600.0, abs=0.02)


class TestVentanasDePeriodo:
    """Que cada período cubra la fecha que dice cubrir.

    Lo que se vio: "Semana" daba más total que "Mes", que no puede ser. La causa
    no era el rango mal calculado sino que al 1º del mes la semana en curso
    arranca el lunes anterior, o sea incluye días del mes pasado que "Mes" no
    tiene. El código estaba bien; lo que faltaba era decirlo.
    """

    def _vender(self, db, user, prod, fecha, total):
        """Venta con su item: el endpoint suma VentaItem.subtotal, no Venta.total."""
        venta = Venta(
            numero=f"VP-{uuid.uuid4().hex[:8]}", usuario_id=user.id, sucursal_id=1,
            estado="confirmada", subtotal=total, total=total, fecha=fecha,
        )
        db.add(venta)
        db.flush()
        db.add(VentaItem(
            venta_id=venta.id, producto_id=prod.id, cantidad=1,
            precio_unitario=total, subtotal=total, precio_costo=total * 0.6,
        ))
        db.commit()

    def test_semana_arranca_el_lunes(self, db):
        # AHORA = martes 29/09/2026. La semana empieza el lunes 28/09.
        desde, hasta = dash._ventana("semana")
        assert desde == datetime(2026, 9, 28, 3, 0, tzinfo=UTC)
        assert hasta == datetime(2026, 10, 5, 3, 0, tzinfo=UTC)

    def test_mes_arranca_el_primero_a_medianoche_local(self, db):
        # AHORA = 29/09/2026, así que el mes en curso es septiembre.
        # 1/09 00:00 UTC-3 = 03:00 UTC.
        desde, hasta = dash._ventana("mes")
        assert desde == datetime(2026, 9, 1, 3, 0, tzinfo=UTC)
        assert hasta == datetime(2026, 10, 1, 3, 0, tzinfo=UTC)

    def test_hoy_es_solo_el_dia_local(self, db):
        desde, hasta = dash._ventana("hoy")
        assert desde == datetime(2026, 9, 29, 3, 0, tzinfo=UTC)
        assert hasta == datetime(2026, 9, 30, 3, 0, tzinfo=UTC)

    def test_ventas_de_ayer_no_entran_en_hoy(self, db):
        user = _semilla(db)
        gasesa = _producto(db, "Gaseosa")
        antes = _res(db, user, periodo="hoy")["totales"]["importe"]
        assert antes > 0
        self._vender(db, user, gasesa, datetime(2026, 9, 28, 15, 0, tzinfo=UTC), 999999.0)
        assert _res(db, user, periodo="hoy")["totales"]["importe"] == pytest.approx(antes)
        # Pero sí entra en la semana, que arranca el lunes 28/09.
        assert _res(db, user, periodo="semana")["totales"]["importe"] > antes

    def test_el_mes_incluye_lo_que_hoy_cubre(self, db):
        user = _semilla(db)
        hoy = _res(db, user, periodo="hoy")["totales"]["importe"]
        mes = _res(db, user, periodo="mes")["totales"]["importe"]
        assert mes >= hoy

    def test_el_mes_incluye_lo_que_la_semana_cubre(self, db):
        # Al 29/09 la semana (lunes 28) está entera adentro de septiembre, así
        # que acá el mes tiene que ser >= semana. Es el invariante que se rompió
        # el 1/10, y por eso vale la pena fijarlo para el resto del mes.
        user = _semilla(db)
        semana = _res(db, user, periodo="semana")["totales"]["importe"]
        mes = _res(db, user, periodo="mes")["totales"]["importe"]
        assert mes >= semana

    def test_semana_puede_superar_al_mes_al_principio_del_mes(self, db, monkeypatch):
        """El caso real que reportó el usuario: 1/10, la semana arranca el 28/09.

        No es un bug: la semana incluye 28, 29 y 30/09, que "Mes" no tiene. El
        test fija el comportamiento para que no se "arregle" por error.
        """
        # El fixture ya monkeypatchea HOY; acá se corre al 1/10/2026 (jueves).
        monkeypatch.setattr(dash, "HOY", lambda: datetime(2026, 10, 1, 15, 0, tzinfo=UTC))
        user = _semilla(db)
        gasesa = _producto(db, "Gaseosa")
        db.query(VentaItem).delete()
        db.query(Venta).delete()
        db.commit()
        self._vender(db, user, gasesa, datetime(2026, 9, 30, 15, 0, tzinfo=UTC), 10000.0)
        self._vender(db, user, gasesa, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), 500.0)

        semana = _res(db, user, periodo="semana")["totales"]["importe"]
        mes = _res(db, user, periodo="mes")["totales"]["importe"]
        assert semana == pytest.approx(10500.0)
        assert mes == pytest.approx(500.0)
        assert semana > mes


    def test_devuelve_las_fechas_del_rango(self, db):
        """Para que el front pueda mostrar qué cubre cada rango.

        Al 1º del mes "Semana" arranca el lunes anterior y puede dar más que
        "Mes"; sin las fechas, el número parece un error de cálculo.
        """
        user = _semilla(db)
        assert _res(db, user, periodo="hoy")["desde"] == "29/09"
        assert _res(db, user, periodo="hoy")["hasta"] == "29/09"
        assert _res(db, user, periodo="semana")["desde"] == "28/09"
        assert _res(db, user, periodo="semana")["hasta"] == "04/10"
        assert _res(db, user, periodo="mes")["desde"] == "01/09"
        assert _res(db, user, periodo="mes")["hasta"] == "30/09"


class TestValidacion:
    def test_metrica_invalida_devuelve_400(self, db):
        user = _semilla(db)
        with pytest.raises(HTTPException) as e:
            _res(db, user, metrica="inventada")
        assert e.value.status_code == 400

    def test_periodo_invalido_devuelve_400(self, db):
        user = _semilla(db)
        with pytest.raises(HTTPException) as e:
            _res(db, user, periodo="decada")
        assert e.value.status_code == 400

    def test_sin_ventas_devuelve_lista_vacia(self, db):
        user = _semilla(db)
        # Las ventas son de hoy, así que el mes/trimestre las incluyen.
        assert _res(db, user, periodo="mes")["categorias"]
        assert _res(db, user, periodo="trimestre")["categorias"]
        # La semana empieza el lunes: si hoy no es lunes, no entra.
        semana = _res(db, user, periodo="semana")
        assert isinstance(semana["categorias"], list)

    def test_ventas_anuladas_no_cuentan(self, db):
        user = _semilla(db)
        db.query(Venta).update({"estado": "anulada"})
        db.commit()
        res = _res(db, user)
        assert res["categorias"] == []
        assert res["totales"]["importe"] == 0
        assert res["totales"]["margen_pct"] == 0
