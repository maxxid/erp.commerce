"""Tests de los rangos del gráfico de ventas y del drill-down de categorías.

El gráfico de ventas estaba clavado en "últimos 7 días": no se podía mirar la
semana ni el mes anterior, que es la comparación que sirve para saber si un
período fue bueno. Y el agrupado por categoría raíz escondía qué productos
traen cada barra, justamente lo que delata un producto mal cargado.
"""

import uuid
from datetime import datetime, timezone, timedelta

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

# Martes 29/09/2026 10:00 local. La semana arranca el lunes 28/09.
AHORA = datetime(2026, 9, 29, 13, 0, tzinfo=UTC)


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


class Sembrador:
    """Usuario + sucursal + ventas sueltas en fechas concretas."""

    def __init__(self, db):
        self.sufijo = uuid.uuid4().hex[:8]
        self.user = Usuario(
            username=f"vp_{self.sufijo}", nombre="VP", password_hash="x",
            rol="admin", activo=True,
        )
        db.add(self.user)
        db.flush()
        db.add(Sucursal(id=1, nombre="Principal"))
        db.commit()

    def vender(self, db, fecha, total):
        db.add(Venta(
            numero=f"V-{self.sufijo}-{uuid.uuid4().hex[:6]}",
            usuario_id=self.user.id, sucursal_id=1, estado="confirmada",
            subtotal=total, total=total, fecha=fecha,
        ))
        db.commit()


def _res(db, user, periodo):
    return dash.ventas_periodo(db=db, user=user, periodo=periodo).data


class TestVentasPorHora:
    """/por-hora: el gráfico por hora tenía el rango clavado en "hoy"."""

    def _res(self, db, user, periodo):
        return dash.ventas_por_hora(db=db, user=user, periodo=periodo).data

    def test_hoy_solo_toma_el_dia_de_hoy(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)  # hoy 13:00
        u.vender(db, datetime(2026, 9, 26, 16, 0, tzinfo=UTC), 9000.0)  # sábado
        res = self._res(db, u.user, "hoy")
        assert res["total"] == 5000.0
        assert res["valores"][13] == 5000.0

    def test_7dias_agrega_los_dias_anteriores(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)
        u.vender(db, datetime(2026, 9, 26, 16, 0, tzinfo=UTC), 9000.0)
        res = self._res(db, u.user, "7dias")
        assert res["total"] == 14000.0
        assert res["valores"][13] == 14000.0  # mismo bucket horario, dos días

    def test_solo_ventas_confirmadas(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)
        anulada = Venta(
            numero=f"V-AN-{uuid.uuid4().hex[:6]}", usuario_id=u.user.id,
            sucursal_id=1, estado="anulada", subtotal=7000, total=7000,
            fecha=datetime(2026, 9, 29, 18, 0, tzinfo=UTC),
        )
        db.add(anulada)
        db.commit()
        res = self._res(db, u.user, "hoy")
        assert res["total"] == 5000.0

    def test_devuelve_las_24_horas_para_el_eje(self, db):
        res = self._res(db, Sembrador(db).user, "hoy")
        assert len(res["labels"]) == 24
        assert len(res["valores"]) == 24
        assert res["labels"][0] == "00:00"
        assert res["labels"][23] == "23:00"

    def test_horas_con_venta_no_cuenta_las_vacias(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)
        u.vender(db, datetime(2026, 9, 29, 20, 0, tzinfo=UTC), 1000.0)
        res = self._res(db, u.user, "hoy")
        assert res["horas_con_venta"] == 2

    def test_hora_local_no_utc(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)  # 13:00 local
        res = self._res(db, u.user, "hoy")
        assert res["valores"][13] == 5000.0
        assert res["valores"][16] == 0.0

    def test_sin_ventas_devuelve_ceros_y_no_falla(self, db):
        res = self._res(db, Sembrador(db).user, "mes")
        assert res["total"] == 0.0
        assert res["horas_con_venta"] == 0
        assert len(res["valores"]) == 24

    def test_periodo_invalido_400(self, db):
        with pytest.raises(HTTPException) as ei:
            self._res(db, Sembrador(db).user, "trimestre")
        assert ei.value.status_code == 400

    def test_hoy_no_es_lo_mismo_que_mes(self, db):
        # Regresión: "hoy" caía en el else de _ventana_ventas y devolvía el mes
        # anterior, así que el combobox "Hoy" mentía.
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)
        u.vender(db, datetime(2026, 9, 10, 16, 0, tzinfo=UTC), 3000.0)
        assert self._res(db, u.user, "hoy")["total"] == 5000.0
        assert self._res(db, u.user, "mes")["total"] == 8000.0


class TestResumenPicosPorHora:
    """El gráfico por hora usaba v.fecha.hour, que es la hora UTC.

    Un local que abre de 9 a 21 veía el gráfico corrido tres horas: la venta de
    las 9 marcaba 12, y la de medianoche caía en el día anterior.
    """

    def test_usa_hora_local_no_utc(self, db):
        u = Sembrador(db)
        # 16:00 UTC = 13:00 local.
        u.vender(db, datetime(2026, 9, 29, 16, 0, tzinfo=UTC), 5000.0)
        res = dash.resumen(db, u.user).data
        horas = res["ventas_por_hora"]
        assert horas["valores"][13] == 5000.0
        assert horas["valores"][16] == 0.0

    def test_venta_de_la_noche_local_no_se_pierde(self, db):
        # 01:00 UTC del 30/09 = 22:00 local del 29: es parte del día de hoy.
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 30, 1, 0, tzinfo=UTC), 3000.0)
        res = dash.resumen(db, u.user).data
        assert res["ventas_por_hora"]["valores"][22] == 3000.0
        assert res["ventas_hoy"] == 3000.0

    def test_agrupa_varias_ventas_en_la_misma_hora(self, db):
        u = Sembrador(db)
        for _ in range(3):
            u.vender(db, datetime(2026, 9, 29, 15, 0, tzinfo=UTC), 1000.0)
        horas = dash.resumen(db, u.user).data["ventas_por_hora"]
        assert horas["valores"][12] == 3000.0


class TestVentasPeriodo:
    def test_7dias_devuelve_7_buckets_diarios(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "7dias")
        assert res["granularidad"] == "dia"
        assert len(res["labels"]) == 7
        assert len(res["valores"]) == 7

    def test_7dias_empieza_6_dias_atras(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "7dias")
        # Último bucket = hoy (martes 29), primero = miércoles 23.
        assert res["labels"][-1] == "Tue 29"
        assert res["labels"][0] == "Wed 23"

    def test_semana_actual_empieza_el_lunes(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "semana")
        assert res["labels"][0] == "Mon 28"
        assert res["labels"][-1] == "Sun 04"

    def test_semana_y_semana_anterior_no_se_mezclan(self, db):
        u = Sembrador(db)
        # Domingo 27/09 (semana pasada) y martes 29/09 (esta semana).
        u.vender(db, datetime(2026, 9, 27, 15, 0, tzinfo=UTC), 1000.0)
        u.vender(db, datetime(2026, 9, 29, 15, 0, tzinfo=UTC), 2000.0)
        actual = _res(db, u.user, "semana")
        anterior = _res(db, u.user, "semana_anterior")
        assert actual["total"] == 2000.0
        assert anterior["total"] == 1000.0
        # Y cada serie tiene un solo día con venta, en la posición correcta.
        assert actual["valores"][1] == 2000.0     # martes = índice 1
        assert anterior["valores"][6] == 1000.0   # domingo = índice 6

    def test_meses_se_agrupan_por_semana(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "mes")
        assert res["granularidad"] == "semana"
        # Del 1 al 30/09: 4 semanas completas más el resto.
        assert 4 <= len(res["labels"]) <= 5
        assert all(l.startswith("S") for l in res["labels"])

    def test_mes_anterior_empieza_el_primero_de_agosto(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "mes_anterior")
        assert res["labels"][0].endswith("01/08")

    def test_mes_y_mes_anterior_no_se_mezclan(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 8, 10, 15, 0, tzinfo=UTC), 500.0)
        u.vender(db, datetime(2026, 9, 10, 15, 0, tzinfo=UTC), 700.0)
        assert _res(db, u.user, "mes")["total"] == 700.0
        assert _res(db, u.user, "mes_anterior")["total"] == 500.0

    def test_ventas_anuladas_no_cuentan(self, db):
        u = Sembrador(db)
        u.vender(db, datetime(2026, 9, 29, 15, 0, tzinfo=UTC), 2000.0)
        db.query(Venta).update({"estado": "anulada"})
        db.commit()
        assert _res(db, u.user, "7dias")["total"] == 0

    def test_sin_ventas_devuelve_ceros_no_lista_vacia(self, db):
        u = Sembrador(db)
        res = _res(db, u.user, "mes")
        assert res["valores"] and all(v == 0 for v in res["valores"])
        assert res["total"] == 0

    def test_total_es_la_suma_de_los_buckets(self, db):
        u = Sembrador(db)
        for d in (23, 25, 27, 29):
            u.vender(db, datetime(2026, 9, d, 15, 0, tzinfo=UTC), 1000.0)
        res = _res(db, u.user, "7dias")
        assert res["total"] == 4000.0
        assert res["total"] == round(sum(res["valores"]), 2)

    def test_periodo_invalido_devuelve_400(self, db):
        u = Sembrador(db)
        with pytest.raises(HTTPException) as e:
            _res(db, u.user, "decada")
        assert e.value.status_code == 400


class Catalogo:
    """Bebidas -> Gaseosas, más Almacen y un producto sin categoría."""

    def __init__(self, db):
        u = Sembrador(db)
        self.sufijo = s = u.sufijo
        self.user = u.user
        self.vendedor = u
        self.bebidas = Categoria(nombre=f"Bebidas {s}")
        self.gaseosas = Categoria(nombre=f"Gaseosas {s}")
        self.almacen = Categoria(nombre=f"Almacen {s}")
        db.add_all([self.bebidas, self.gaseosas, self.almacen])
        db.flush()
        self.gaseosas.padre_id = self.bebidas.id
        db.flush()

        self.gaseosa = self._prod(db, "Gaseosa", self.gaseosas.id, 1000.0, 600.0)
        self.cola = self._prod(db, "Cola", self.gaseosas.id, 1200.0, 900.0)
        self.arroz = self._prod(db, "Arroz", self.almacen.id, 2000.0, None)
        self.suelto = self._prod(db, "Vuelto", None, 500.0, 250.0)
        self.fantasma = self._prod(db, "Fantasma", self.almacen.id, 800.0, 400.0)
        db.flush()

        # Todo hoy, menos el fantasma que se vendió en agosto.
        for prod, cant, fecha in (
            (self.gaseosa, 2, AHORA),
            (self.cola, 1, AHORA),
            (self.arroz, 1, AHORA),
            (self.suelto, 1, AHORA),
            (self.fantasma, 1, datetime(2026, 8, 10, 15, 0, tzinfo=UTC)),
        ):
            self._vender(db, prod, cant, fecha)
        db.commit()

    def _prod(self, db, nombre, cat_id, venta, costo):
        p = Producto(
            codigo_barras=f"CB-{nombre}-{self.sufijo}", nombre=nombre,
            categoria_id=cat_id, precio_venta=venta, precio_costo=costo,
            stock_actual=50,
        )
        db.add(p)
        return p

    def _vender(self, db, prod, cant, fecha):
        total = prod.precio_venta * cant
        v = Venta(
            numero=f"PC-{self.sufijo}-{uuid.uuid4().hex[:6]}",
            usuario_id=self.user.id, sucursal_id=1, estado="confirmada",
            subtotal=total, total=total, fecha=fecha,
        )
        db.add(v)
        db.flush()
        db.add(VentaItem(
            venta_id=v.id, producto_id=prod.id, cantidad=cant,
            precio_unitario=prod.precio_venta, precio_costo=prod.precio_costo,
            subtotal=total,
        ))
        db.flush()

    def res(self, db, categoria, metrica="importe", periodo="mes", limite=15):
        return dash.productos_por_categoria(
            db=db, user=self.user, categoria=categoria,
            periodo=periodo, metrica=metrica, limite=limite,
        ).data


class TestProductosPorCategoria:
    def test_trae_los_productos_de_la_raiz_y_sus_hijas(self, db):
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id))
        assert {p["nombre"] for p in res["productos"]} == {"Gaseosa", "Cola"}

    def test_no_se_le_pisan_productos_de_otra_categoria(self, db):
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id))
        nombres = {p["nombre"] for p in res["productos"]}
        assert "Arroz" not in nombres and "Fantasma" not in nombres

    def test_cada_producto_trae_su_ruta_real_de_categoria(self, db):
        # La barra es "Bebidas" pero el producto es de Gaseosas: eso es
        # justamente lo que delata un producto mal cargado.
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id))
        rutas = {p["nombre"]: p["categoria"] for p in res["productos"]}
        s = c.sufijo
        assert rutas["Cola"] == f"Bebidas {s} / Gaseosas {s}"
        assert rutas["Gaseosa"] == f"Bebidas {s} / Gaseosas {s}"

    def test_sin_categoria_trae_solo_los_sueltos(self, db):
        c = Catalogo(db)
        res = c.res(db, "sin_categoria")
        assert {p["nombre"] for p in res["productos"]} == {"Vuelto"}
        assert res["productos"][0]["categoria"] == "Sin categoría"

    def test_producto_sin_costo_calcula_100_de_margen(self, db):
        c = Catalogo(db)
        arroz = c.res(db, str(c.almacen.id))["productos"][0]
        assert arroz["nombre"] == "Arroz"
        assert arroz["margen_pct"] == 100.0
        assert arroz["items_sin_costo"] == 1

    def test_orden_por_importe(self, db):
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id), "importe")
        # Gaseosa 2 x 1000 = 2000; Cola 1 x 1200 = 1200.
        assert [p["nombre"] for p in res["productos"]] == ["Gaseosa", "Cola"]

    def test_orden_por_cantidad(self, db):
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id), "cantidad")
        assert res["productos"][0]["nombre"] == "Gaseosa"
        assert res["productos"][0]["cantidad"] == 2

    def test_orden_por_margen_pct_difiere_del_importe(self, db):
        # Gaseosa 40% de margen, Cola 25%: el mismo orden que por importe, pero
        # los porcentajes son los que delatan cuál conviene cuidar.
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id), "margen_pct")
        pcts = {p["nombre"]: p["margen_pct"] for p in res["productos"]}
        assert pcts == {"Gaseosa": 40.0, "Cola": 25.0}

    def test_limite_recorta_pero_el_total_no(self, db):
        c = Catalogo(db)
        res = c.res(db, str(c.bebidas.id), limite=1)
        assert len(res["productos"]) == 1
        assert res["total_productos"] == 2

    def test_respeta_el_periodo(self, db):
        # El fantasma se vendió en agosto: entra en "trimestre" (jul-sep) pero
        # no en el mes actual.
        c = Catalogo(db)
        mes = c.res(db, str(c.almacen.id), periodo="mes")
        assert {p["nombre"] for p in mes["productos"]} == {"Arroz"}
        trim = c.res(db, str(c.almacen.id), periodo="trimestre")
        assert {p["nombre"] for p in trim["productos"]} == {"Arroz", "Fantasma"}

    def test_otras_no_puede_bajar(self, db):
        c = Catalogo(db)
        with pytest.raises(HTTPException) as e:
            c.res(db, "otras")
        assert e.value.status_code == 400

    def test_categoria_inexistente_devuelve_404(self, db):
        c = Catalogo(db)
        with pytest.raises(HTTPException) as e:
            c.res(db, "999999")
        assert e.value.status_code == 404

    def test_categoria_no_numerica_devuelve_400(self, db):
        c = Catalogo(db)
        with pytest.raises(HTTPException) as e:
            c.res(db, "bebidas")
        assert e.value.status_code == 400

    def test_periodo_y_metrica_invalidos_devuelven_400(self, db):
        c = Catalogo(db)
        cat = str(c.bebidas.id)
        with pytest.raises(HTTPException) as e:
            c.res(db, cat, periodo="decada")
        assert e.value.status_code == 400
        with pytest.raises(HTTPException) as e:
            c.res(db, cat, metrica="inventada")
        assert e.value.status_code == 400
