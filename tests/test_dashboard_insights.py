"""Tests de la comparativa contra el período anterior, el stock por velocidad
de venta y el panel de datos sucios.

Lo que cubre:
  - cada KPI se compara contra la ventana anterior del mismo largo, no contra
    "lo que había en el mismo día del mes pasado"
  - con base 0 no se muestra un porcentaje inventado
  - el ritmo de venta cruza stock real con lo vendido, y "sin ventas" no inventa
    una proyección
  - datos sucios cuenta una sola vez un producto que está en las dos listas
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

# Jueves 1/10/2026 12:00 local (15:00 UTC). Deja ayer y el mes pasado con datos.
AHORA = datetime(2026, 10, 1, 15, 0, tzinfo=UTC)


@pytest.fixture
def db(monkeypatch):
    monkeypatch.setattr(dash, "HOY", lambda: AHORA)
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    sesion = sessionmaker(bind=engine)()
    try:
        yield sesion
    finally:
        sesion.close()


class Sembrador:
    def __init__(self, db, con_categoria=True, con_costo=True):
        self.sufijo = uuid.uuid4().hex[:8]
        self.user = Usuario(
            username=f"cmp_{self.sufijo}", nombre="Cmp", password_hash="x",
            rol="admin", activo=True,
        )
        db.add(self.user)
        db.add(Sucursal(id=1, nombre="Principal"))
        db.flush()
        self.cat = None
        if con_categoria:
            self.cat = Categoria(nombre=f"Bebidas {self.sufijo}")
            db.add(self.cat)
            db.flush()

    def producto(self, db, nombre="Gaseosa", stock=10, minimo=0, con_costo=None):
        if con_costo is None:
            con_costo = self.con_costo if hasattr(self, "con_costo") else True
        p = Producto(
            codigo_barras=f"CB-{nombre}-{self.sufijo}", nombre=nombre,
            categoria_id=self.cat.id if self.cat else None,
            precio_venta=1000.0, precio_costo=600.0 if con_costo else None,
            stock_actual=stock, stock_minimo=minimo, activo=True,
        )
        db.add(p)
        db.flush()
        return p

    def vender(self, db, prod, fecha, cantidad=1, precio_unitario=1000.0, estado="confirmada"):
        total = cantidad * precio_unitario
        v = Venta(
            numero=f"V-{self.sufijo}-{uuid.uuid4().hex[:6]}", usuario_id=self.user.id,
            sucursal_id=1, estado=estado, subtotal=total, total=total, fecha=fecha,
        )
        db.add(v)
        db.flush()
        db.add(VentaItem(
            venta_id=v.id, producto_id=prod.id, cantidad=cantidad,
            precio_unitario=precio_unitario, subtotal=total, precio_costo=600.0,
        ))
        db.commit()


class TestComparativaVsAnterior:
    def test_hoy_se_compara_con_ayer(self, db):
        u = Sembrador(db)
        p = u.producto(db)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), cantidad=1, precio_unitario=3000.0)
        u.vender(db, p, datetime(2026, 9, 30, 15, 0, tzinfo=UTC), cantidad=1, precio_unitario=1000.0)
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["ventas"]["actual"] == 3000.0
        assert vs["ventas"]["anterior"] == 1000.0
        assert vs["ventas"]["pct"] == 200.0

    def test_ayer_sin_ventas_no_da_porcentaje_inventado(self, db):
        """Con base 0 el porcentaje no significa nada: de 0 a 500 no es +100%."""
        u = Sembrador(db)
        p = u.producto(db)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), cantidad=1, precio_unitario=500.0)
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["ventas"]["pct"] is None
        assert vs["ventas"]["actual"] == 500.0

    def test_baja_da_porcentaje_negativo(self, db):
        u = Sembrador(db)
        p = u.producto(db)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), cantidad=1, precio_unitario=2500.0)
        u.vender(db, p, datetime(2026, 9, 30, 15, 0, tzinfo=UTC), cantidad=1, precio_unitario=5000.0)
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["ventas"]["pct"] == -50.0

    def test_el_ticket_promedio_se_compara_con_el_del_ayer(self, db):
        u = Sembrador(db)
        p = u.producto(db)
        # Hoy: una venta de 3000. Ayer: dos de 1000 (ticket 1000).
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=3000.0)
        u.vender(db, p, datetime(2026, 9, 30, 11, 0, tzinfo=UTC), precio_unitario=1000.0)
        u.vender(db, p, datetime(2026, 9, 30, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["ticket"]["actual"] == 3000.0
        assert vs["ticket"]["anterior"] == 1000.0
        assert vs["ticket"]["pct"] == 200.0
        assert vs["cantidad"]["actual"] == 1
        assert vs["cantidad"]["anterior"] == 2

    def test_las_ventas_anuladas_no_entran_en_la_comparativa(self, db):
        u = Sembrador(db)
        p = u.producto(db)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        u.vender(db, p, datetime(2026, 10, 1, 16, 0, tzinfo=UTC), precio_unitario=99999.0, estado="anulada")
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["ventas"]["actual"] == 1000.0

    def test_el_margen_compara_ventas_menos_costo(self, db):
        u = Sembrador(db)
        p = u.producto(db)  # precio_costo 600
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        u.vender(db, p, datetime(2026, 9, 30, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        vs = dash._comparativa_vs_anterior(db, datetime(2026, 10, 1, 3, 0, tzinfo=UTC),
                                            datetime(2026, 10, 2, 3, 0, tzinfo=UTC))
        assert vs["margen"]["actual"] == 400.0   # 1000 - 600
        assert vs["margen"]["pct"] == 0.0         # contra ayer, igual


class TestStockPorVelocidad:
    def _res(self, db, user, **kw):
        # Los defaults de Query() no se aplican al llamar la función directo, así
        # que se pasan siempre: en el server los pone FastAPI.
        kw.setdefault("dias", 30)
        kw.setdefault("limite", 10)
        kw.setdefault("solo_criticos", True)
        return dash.stock_por_velocidad(db=db, user=user, **kw).data

    def test_calcula_cuantos_dias_dura_el_stock(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Gaseosa", stock=3, minimo=0)
        # 30 días, 8 por día = 240 unidades. Quedan 3 → 0,4 días.
        for d in range(30):
            u.vender(db, p, datetime(2026, 9, 2, 15, 0, tzinfo=UTC) + timedelta(days=d), cantidad=8)
        res = self._res(db, u.user, dias=30, solo_criticos=True)
        fila = next(r for r in res["productos"] if r["id"] == p.id)
        assert fila["por_dia"] == 8.0
        assert fila["dias_stock"] == pytest.approx(0.4, abs=0.1)

    def test_lo_urgente_arriba(self, db):
        u = Sembrador(db)
        lento = u.producto(db, "Lento", stock=5)
        rapido = u.producto(db, "Rapido", stock=5)
        for d in range(30):
            u.vender(db, lento, datetime(2026, 9, 2, 15, 0, tzinfo=UTC) + timedelta(days=d), cantidad=1)
            u.vender(db, rapido, datetime(2026, 9, 2, 15, 0, tzinfo=UTC) + timedelta(days=d), cantidad=20)
        res = self._res(db, u.user, dias=30, solo_criticos=True)
        assert res["productos"][0]["nombre"].startswith("Rapido")

    def test_sin_ventas_no_inventa_una_proyeccion(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Estatico", stock=2, minimo=0)
        res = self._res(db, u.user, dias=30, solo_criticos=True)
        fila = next((r for r in res["productos"] if r["id"] == p.id), None)
        # No entra en la lista de críticos: no hay con qué proyectar.
        assert fila is None

    def test_con_ventas_pero_stock_abundante_no_entra(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Abundante", stock=1000, minimo=0)
        for d in range(30):
            u.vender(db, p, datetime(2026, 9, 2, 15, 0, tzinfo=UTC) + timedelta(days=d), cantidad=1)
        res = self._res(db, u.user, dias=30, solo_criticos=True)
        assert all(r["id"] != p.id for r in res["productos"])

    def test_solo_criticos_false_trae_todos(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Tranquilo", stock=900, minimo=0)
        for d in range(30):
            u.vender(db, p, datetime(2026, 9, 2, 15, 0, tzinfo=UTC) + timedelta(days=d), cantidad=1)
        res = self._res(db, u.user, dias=30, solo_criticos=False)
        assert any(r["id"] == p.id for r in res["productos"])

    def test_dias_invalido_400(self, db):
        u = Sembrador(db)
        with pytest.raises(HTTPException) as ei:
            self._res(db, u.user, dias=1)
        assert ei.value.status_code == 400


class TestDatosSucios:
    def _res(self, db, user, **kw):
        # Igual que en stock: Query() no aplica defaults en llamada directa.
        kw.setdefault("periodo", "mes")
        return dash.datos_sucios(db=db, user=user, **kw).data

    def test_avisa_los_que_no_tienen_costo(self, db):
        u = Sembrador(db)
        sin = u.producto(db, "Arroz", con_costo=False)
        con = u.producto(db, "Gaseosa", con_costo=True)
        u.vender(db, sin, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=2000.0)
        u.vender(db, con, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=3000.0)
        res = self._res(db, u.user, periodo="mes")
        assert [r["nombre"] for r in res["sin_costo"]] == ["Arroz"]
        assert res["importe_afectado"] == 2000.0
        assert res["pct_afectado"] == pytest.approx(40.0)

    def test_avisa_los_que_no_tienen_categoria(self, db):
        u = Sembrador(db, con_categoria=True)
        con = u.producto(db, "Cola")
        # Producto sin categoría: hay que crearlo aparte porque Sembrador
        # usa una sola categoría.
        p = Producto(
            codigo_barras=f"CB-sincat-{u.sufijo}", nombre="Vuelto",
            categoria_id=None, precio_venta=1000.0, precio_costo=500.0,
            stock_actual=5, stock_minimo=0, activo=True,
        )
        db.add(p)
        db.flush()
        u.vender(db, con, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=1000.0)
        res = self._res(db, u.user, periodo="mes")
        assert [r["nombre"] for r in res["sin_categoria"]] == ["Vuelto"]

    def test_un_producto_en_las_dos_listas_se_cuenta_una_sola_vez(self, db):
        u = Sembrador(db, con_categoria=False)
        p = u.producto(db, "Vuelto", con_costo=False)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=5000.0)
        res = self._res(db, u.user, periodo="mes")
        assert len(res["sin_costo"]) == 1
        assert len(res["sin_categoria"]) == 1
        # Si se sumara dos veces, sería 10000 y el pct 200.
        assert res["importe_afectado"] == 5000.0
        assert res["pct_afectado"] == 100.0
        assert res["cantidad"] == 1

    def test_ordena_por_importe_descendente(self, db):
        u = Sembrador(db)
        chico = u.producto(db, "Chico", con_costo=False)
        grande = u.producto(db, "Grande", con_costo=False)
        u.vender(db, chico, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=500.0)
        u.vender(db, grande, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=9000.0)
        res = self._res(db, u.user, periodo="mes")
        assert [r["nombre"] for r in res["sin_costo"]] == ["Grande", "Chico"]

    def test_sin_ventas_no_reporta_nada(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Arroz", con_costo=False)
        res = self._res(db, u.user, periodo="mes")
        # El producto existe pero no se vendió: no distorsiona ningún número.
        assert res["sin_costo"] == []
        assert res["cantidad"] == 0
        assert res["pct_afectado"] == 0.0

    def test_ventas_anuladas_no_cuentan(self, db):
        u = Sembrador(db)
        p = u.producto(db, "Arroz", con_costo=False)
        u.vender(db, p, datetime(2026, 10, 1, 15, 0, tzinfo=UTC), precio_unitario=2000.0, estado="anulada")
        assert self._res(db, u.user, periodo="mes")["cantidad"] == 0

    def test_periodo_invalido_400(self, db):
        u = Sembrador(db)
        with pytest.raises(HTTPException) as ei:
            self._res(db, u.user, periodo="decada")
        assert ei.value.status_code == 400
