"""Tests de sectores: CRUD, asignación en lote y filtro/orden en etiquetas."""

from datetime import date, datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.producto import Producto
from app.models.sector import Sector
from app.models.usuario import Usuario
from app.routers import productos as productos_router
from app.routers import sectores as sectores_router
from app.schemas.etiquetas import EtiquetasFiltros
from app.schemas.sector import SectorCreate, SectorUpdate
from app.services.etiquetas_service import obtener_productos_para_etiquetar


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def user(db):
    u = Usuario(username="admin", password_hash="x", nombre="Admin", rol="admin")
    db.add(u)
    db.commit()
    return u


def _producto(db, codigo, sector_id=None, activo=True, created_at=None, nombre=None):
    p = Producto(
        codigo_barras=codigo, nombre=nombre or f"Prod {codigo}",
        precio_venta=100.0, activo=activo,
        sector_id=sector_id,
        created_at=created_at or datetime(2026, 1, 1, 10, 0),
        updated_at=created_at or datetime(2026, 1, 1, 10, 0),
    )
    db.add(p)
    db.commit()
    return p


def _crear(db, nombre, orden=0):
    return sectores_router.crear(SectorCreate(nombre=nombre, orden=orden), db=db, user=None)


def _nombres(db):
    return [s.nombre for s in sectores_router.listar(db=db, user=None).data]


class TestCRUD:
    def test_crear_y_listar(self, db):
        _crear(db, "Góndola 1")
        assert _nombres(db) == ["Góndola 1"]

    def test_crear_vacio_rechazado(self, db):
        with pytest.raises(HTTPException) as exc:
            _crear(db, "   ")
        assert exc.value.status_code == 400

    def test_crear_duplicado_devuelve_el_existente(self, db, user):
        _crear(db, "Góndola 1")
        repetido = _crear(db, "Góndola 1")
        assert repetido.data.nombre == "Góndola 1"
        assert len(db.query(Sector).all()) == 1

    def test_duplicado_es_insensible_a_mayusculas_y_espacios(self, db):
        _crear(db, "Góndola 1")
        repetido = _crear(db, "  gÓndola 1  ")
        assert repetido.message.startswith("El sector")
        assert len(db.query(Sector).all()) == 1

    def test_eliminar_no_borra_la_fila(self, db, user):
        sector = _crear(db, "Mesa 1").data
        sectores_router.eliminar(sector.id, db=db, user=user)
        assert db.query(Sector).filter(Sector.id == sector.id).first().activo is False
        assert _nombres(db) == []

    def test_eliminar_inexistente_tira_404(self, db, user):
        with pytest.raises(HTTPException) as exc:
            sectores_router.eliminar(999, db=db, user=user)
        assert exc.value.status_code == 404

    def test_recrear_con_nombre_de_un_borrado_lo_reactiva(self, db, user):
        sector = _crear(db, "Mesa 1").data
        sectores_router.eliminar(sector.id, db=db, user=user)
        _crear(db, "Mesa 1")
        assert len(db.query(Sector).all()) == 1
        assert _nombres(db) == ["Mesa 1"]

    def test_reactivar_no_trae_de_vuelta_los_productos(self, db, user):
        """Borrar un sector libera sus productos; crearlo de nuevo es otra entidad."""
        sector = _crear(db, "Mesa 1").data
        p = _producto(db, "7790000000001", sector_id=sector.id)
        sectores_router.eliminar(sector.id, db=db, user=user)
        _crear(db, "Mesa 1")
        assert db.query(Producto).filter(Producto.id == p.id).first().sector_id is None

    def test_reactivar_puede_cambiar_orden(self, db, user):
        sector = _crear(db, "Mesa 1").data
        sectores_router.eliminar(sector.id, db=db, user=user)
        _crear(db, "Mesa 1", orden=7)
        assert db.query(Sector).first().orden == 7


class TestActualizar:
    def test_renombrar(self, db, user):
        sector = _crear(db, "Mesa 1").data
        res = sectores_router.actualizar(sector.id, SectorUpdate(nombre="Mesa Grande"), db=db, user=user)
        assert res.data.nombre == "Mesa Grande"

    def test_renombrar_a_un_nombre_activo_choca(self, db, user):
        _crear(db, "Mesa 1")
        otro = _crear(db, "Mesa 2").data
        with pytest.raises(HTTPException) as exc:
            sectores_router.actualizar(otro.id, SectorUpdate(nombre="Mesa 1"), db=db, user=user)
        assert exc.value.status_code == 400

    def test_renombrarse_a_si_mismo_esta_permitido(self, db, user):
        sector = _crear(db, "Mesa 1").data
        res = sectores_router.actualizar(sector.id, SectorUpdate(nombre="mesa 1"), db=db, user=user)
        assert res.data.nombre == "Mesa 1"

    def test_reordenar(self, db, user):
        sector = _crear(db, "Mesa 1").data
        res = sectores_router.actualizar(sector.id, SectorUpdate(orden=5), db=db, user=user)
        assert res.data.orden == 5

    def test_nombre_en_blanco_rechazado(self, db, user):
        sector = _crear(db, "Mesa 1").data
        with pytest.raises(HTTPException) as exc:
            sectores_router.actualizar(sector.id, SectorUpdate(nombre="  "), db=db, user=user)
        assert exc.value.status_code == 400


class TestEliminarLiberaProductos:
    def test_quita_el_sector_de_sus_productos(self, db, user):
        sector = _crear(db, "Mesa 1").data
        p = _producto(db, "7790000000001", sector_id=sector.id)
        res = sectores_router.eliminar(sector.id, db=db, user=user)
        assert res.data["productos_afectados"] == 1
        assert db.query(Producto).filter(Producto.id == p.id).first().sector_id is None

    def test_no_toca_los_de_otro_sector(self, db, user):
        a = _crear(db, "Mesa 1").data
        b = _crear(db, "Mesa 2").data
        _producto(db, "7790000000001", sector_id=a.id)
        otro = _producto(db, "7790000000002", sector_id=b.id)
        sectores_router.eliminar(a.id, db=db, user=user)
        assert db.query(Producto).filter(Producto.id == otro.id).first().sector_id == b.id


class TestListarConteo:
    def test_cuenta_solo_productos_activos(self, db, user):
        sector = _crear(db, "Mesa 1").data
        _producto(db, "7790000000001", sector_id=sector.id)
        _producto(db, "7790000000002", sector_id=sector.id)
        _producto(db, "7790000000003", sector_id=sector.id, activo=False)
        datos = sectores_router.listar(db=db, user=user).data
        assert datos[0].cantidad_productos == 2

    def test_sector_vacio_cuenta_cero(self, db, user):
        _crear(db, "Mesa 1")
        assert sectores_router.listar(db=db, user=user).data[0].cantidad_productos == 0

    def test_no_lista_inactivos(self, db, user):
        sector = _crear(db, "Mesa 1").data
        sectores_router.eliminar(sector.id, db=db, user=user)
        assert sectores_router.listar(db=db, user=user).data == []


class TestAsignarSector:
    def test_asigna_en_lote(self, db, user):
        sector = _crear(db, "Mesa 1").data
        ids = [_producto(db, f"779000000000{i}").id for i in range(1, 4)]
        res = productos_router.asignar_sector(
            productos_router.AsignarSectorRequest(productos_ids=ids, sector_id=sector.id),
            db=db, user=user,
        )
        assert res.data["asignados"] == 3
        assert db.query(Producto).filter(Producto.id.in_(ids)).count() == 3
        assert all(p.sector_id == sector.id for p in db.query(Producto).filter(Producto.id.in_(ids)))

    def test_sector_null_quita_el_sector(self, db, user):
        sector = _crear(db, "Mesa 1").data
        p = _producto(db, "7790000000001", sector_id=sector.id)
        res = productos_router.asignar_sector(
            productos_router.AsignarSectorRequest(productos_ids=[p.id], sector_id=None),
            db=db, user=user,
        )
        assert res.data["sector_id"] is None
        assert db.query(Producto).filter(Producto.id == p.id).first().sector_id is None

    def test_sector_inexistente_tira_404(self, db, user):
        with pytest.raises(HTTPException) as exc:
            productos_router.asignar_sector(
                productos_router.AsignarSectorRequest(productos_ids=[1], sector_id=999),
                db=db, user=user,
            )
        assert exc.value.status_code == 404

    def test_sector_inactivo_no_asigna(self, db, user):
        sector = _crear(db, "Mesa 1").data
        sectores_router.eliminar(sector.id, db=db, user=user)
        with pytest.raises(HTTPException) as exc:
            productos_router.asignar_sector(
                productos_router.AsignarSectorRequest(productos_ids=[1], sector_id=sector.id),
                db=db, user=user,
            )
        assert exc.value.status_code == 404

    def test_lista_vacia_rechazada(self, db, user):
        with pytest.raises(HTTPException) as exc:
            productos_router.asignar_sector(
                productos_router.AsignarSectorRequest(productos_ids=[], sector_id=None),
                db=db, user=user,
            )
        assert exc.value.status_code == 400

    def test_ignora_productos_inactivos(self, db, user):
        sector = _crear(db, "Mesa 1").data
        activo = _producto(db, "7790000000001")
        inactivo = _producto(db, "7790000000002", activo=False)
        res = productos_router.asignar_sector(
            productos_router.AsignarSectorRequest(
                productos_ids=[activo.id, inactivo.id], sector_id=sector.id
            ),
            db=db, user=user,
        )
        assert res.data["asignados"] == 1
        assert db.query(Producto).filter(Producto.id == inactivo.id).first().sector_id is None


class TestEtiquetasFiltroYOrden:
    def _consultar(self, db, **kw):
        filtros = EtiquetasFiltros(desde=date(2026, 1, 1), hasta=date(2026, 12, 31), **kw)
        return obtener_productos_para_etiquetar(db, filtros)

    def test_filtro_por_sector(self, db):
        a = _crear(db, "Mesa 1").data
        b = _crear(db, "Mesa 2").data
        _producto(db, "7790000000001", sector_id=a.id, created_at=datetime(2026, 5, 1, 10, 0))
        _producto(db, "7790000000002", sector_id=b.id, created_at=datetime(2026, 5, 2, 10, 0))
        result = self._consultar(db, sector_id=a.id)
        assert [p.codigo_barras for p in result] == ["7790000000001"]

    def test_filtro_por_sector_sin_coincidencias(self, db):
        vacio = _crear(db, "Mesa 1").data
        con_producto = _crear(db, "Mesa 2").data
        _producto(db, "7790000000001", sector_id=con_producto.id, created_at=datetime(2026, 5, 1, 10, 0))
        assert self._consultar(db, sector_id=vacio.id) == []

    def test_orden_por_sector_respeta_el_orden_del_sector(self, db):
        b = _crear(db, "Bebidas", orden=2).data
        a = _crear(db, "Almacén", orden=1).data
        _producto(db, "7790000000001", sector_id=b.id, created_at=datetime(2026, 5, 1, 10, 0))
        _producto(db, "7790000000002", sector_id=a.id, created_at=datetime(2026, 5, 2, 10, 0))
        result = self._consultar(db, orden="sector")
        assert [p.codigo_barras for p in result] == ["7790000000002", "7790000000001"]

    def test_orden_por_sector_deja_los_sin_sector_al_final(self, db):
        a = _crear(db, "Almacén", orden=1).data
        _producto(db, "7790000000001", created_at=datetime(2026, 5, 1, 10, 0))
        _producto(db, "7790000000002", sector_id=a.id, created_at=datetime(2026, 5, 2, 10, 0))
        result = self._consultar(db, orden="sector")
        assert [p.codigo_barras for p in result] == ["7790000000002", "7790000000001"]

    def test_orden_por_sector_ordena_por_nombre_dentro_del_sector(self, db):
        a = _crear(db, "Almacén", orden=1).data
        _producto(db, "7790000000001", sector_id=a.id, nombre="Zeta",
                  created_at=datetime(2026, 5, 1, 10, 0))
        _producto(db, "7790000000002", sector_id=a.id, nombre="Alfa",
                  created_at=datetime(2026, 5, 2, 10, 0))
        result = self._consultar(db, orden="sector")
        assert [p.nombre for p in result] == ["Alfa", "Zeta"]

    def test_combina_filtro_de_sector_con_categoria(self, db):
        from app.models.categoria import Categoria

        a = _crear(db, "Almacén").data
        cat = Categoria(nombre="Bebidas")
        db.add(cat)
        db.commit()

        _producto(db, "7790000000001", sector_id=a.id, created_at=datetime(2026, 5, 1, 10, 0)).categoria_id = cat.id
        _producto(db, "7790000000002", sector_id=a.id, created_at=datetime(2026, 5, 2, 10, 0))
        sin_sector = _producto(db, "7790000000003", created_at=datetime(2026, 5, 3, 10, 0))
        sin_sector.categoria_id = cat.id
        db.commit()

        result = self._consultar(db, sector_id=a.id, categoria_id=cat.id)
        assert [p.codigo_barras for p in result] == ["7790000000001"]
