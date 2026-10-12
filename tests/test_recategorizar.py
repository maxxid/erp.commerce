"""Tests del panel de recategorización.

Lo crítico acá es la promesa de la feature: **nada se mueve sin que una persona
lo confirme**. Por eso `aplicar()` es el único punto de escritura, la IA solo
propone y cualquier respuesta del modelo se filtra contra el catálogo real
antes de llegar a la pantalla.
"""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.categoria import Categoria
from app.models.producto import Producto
from app.models.usuario import Usuario
from app.routers import recategorizar as router
from app.schemas.recategorizar import (
    AplicarRequest,
    CambioRequest,
    SugerenciasIARequest,
)
from app.services import categorizacion_service as svc
from app.services.ia import registro as ia_registro
from app.services.ia.proveedor import IARespuesta, IADeshabilitada


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


def _cat(db, nombre, activo=True):
    c = Categoria(nombre=nombre, activo=activo)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _prod(db, nombre, categoria_id=None, marca=None, descripcion=None, activo=True):
    p = Producto(
        codigo_barras=f"779{db.query(Producto).count():08d}",
        nombre=nombre,
        marca=marca,
        descripcion=descripcion,
        categoria_id=categoria_id,
        precio_venta=100.0,
        activo=activo,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ---------------------------------------------------------------------------
# Normalización y resolución de catálogo
# ---------------------------------------------------------------------------

class TestNormalizar:
    def test_saca_tildes_y_baja(self):
        assert svc.normalizar("Café Instantáneo") == "cafe instantaneo"

    def test_colapsa_espacios(self):
        assert svc.normalizar("  Coca   Cola  ") == "coca cola"

    def test_none_y_vacio(self):
        assert svc.normalizar(None) == ""
        assert svc.normalizar("") == ""


class TestResolver:
    def test_igualdad_exacta(self, db):
        _cat(db, "Bebidas")
        assert svc._resolver("Bebidas", svc.catalogo(db))[1] == "Bebidas"

    def test_contencion_cubre_subcategoria(self, db):
        beb = _cat(db, "Bebidas frías")
        assert svc._resolver("Bebidas", svc.catalogo(db))[1] == beb.nombre

    def test_categoria_corta_no_por_contencion(self, db):
        """'Pan' no debería casar con 'Panadería' por containment de 3 letras."""
        _cat(db, "Pan")
        assert svc._resolver("Panaderia", svc.catalogo(db)) is None

    def test_general_nunca_es_destino(self, db):
        _cat(db, "General")
        assert svc._resolver("General", svc.catalogo(db)) is None

    def test_inactiva_queda_fuera(self, db):
        _cat(db, "Bebidas", activo=False)
        assert svc.catalogo(db) == []
        assert svc._resolver("Bebidas", []) is None


# ---------------------------------------------------------------------------
# Sugerencia local
# ---------------------------------------------------------------------------

class TestSugerirLocal:
    def test_palabra_clave_en_nombre_da_alta_confianza(self, db):
        beb = _cat(db, "Bebidas frías")
        p = _prod(db, "Gaseosa Coca Cola 500ml", marca="Coca")
        s = svc.sugerir_local(p, svc.catalogo(db))
        assert s["categoria_id"] == beb.id
        assert s["confianza"] >= 0.7
        assert "gaseosa" in s["motivo"]

    def test_pista_solo_en_descripcion_pesa_menos(self, db):
        ref = _cat(db, "Bebidas frías")
        p = _prod(db, "Lata misteriosa", descripcion="Refresco de cola con gas")
        s = svc.sugerir_local(p, svc.catalogo(db))
        assert s["categoria_id"] == ref.id
        assert s["confianza"] < 0.75

    def test_nombre_de_categoria_en_producto_es_la_senal_mas_fuerte(self, db):
        leche = _cat(db, "Leche")
        p = _prod(db, "Leche entera La Serenísima 1L")
        s = svc.sugerir_local(p, svc.catalogo(db))
        assert s["categoria_id"] == leche.id
        assert s["confianza"] >= 0.9
        assert "Leche" in s["motivo"]

    def test_sin_pista_no_inventa(self, db):
        _cat(db, "Bebidas frías")
        p = _prod(db, "Caja marrón 20x15")
        assert svc.sugerir_local(p, svc.catalogo(db)) is None

    def test_no_sugiere_lo_que_ya_tiene(self, db):
        beb = _cat(db, "Bebidas frías")
        p = _prod(db, "Gaseosa Coca Cola 500ml", categoria_id=beb.id)
        assert svc.sugerir_local(p, svc.catalogo(db)) is None

    def test_las_tres_senales_de_general_quedan_afuera(self, db):
        _cat(db, "General")
        p = _prod(db, "Gaseosa Coca Cola 500ml")
        assert svc.sugerir_local(p, svc.catalogo(db)) is None


# ---------------------------------------------------------------------------
# Candidatos del panel
# ---------------------------------------------------------------------------

class TestCandidatos:
    def test_pendientes_junta_sin_categoria_y_general(self, db):
        gen = _cat(db, "General")
        _cat(db, "Lácteos")
        sin = _prod(db, "Producto sin rubro")
        en_general = _prod(db, "Otro sin rubro", categoria_id=gen.id)

        filas, total = svc.candidatos(db, modo="pendientes")
        ids = {f["producto_id"] for f in filas}
        assert ids == {sin.id, en_general.id}
        assert total == 2

    def test_modo_sin_categoria_excluye_general(self, db):
        gen = _cat(db, "General")
        sin = _prod(db, "Producto sin rubro")
        _prod(db, "En general", categoria_id=gen.id)

        filas, total = svc.candidatos(db, modo="sin_categoria")
        assert total == 1
        assert filas[0]["producto_id"] == sin.id

    def test_todos_trae_tambien_los_clasificados(self, db):
        lac = _cat(db, "Lácteos")
        clasificado = _prod(db, "Queso cremoso", categoria_id=lac.id)
        filas, total = svc.candidatos(db, modo="todos")
        assert total == 1
        assert filas[0]["producto_id"] == clasificado.id

    def test_excluye_inactivos(self, db):
        _prod(db, "Borrado", activo=False)
        _, total = svc.candidatos(db, modo="todos")
        assert total == 0

    def test_destino_arranca_en_lo_que_ya_tiene(self, db):
        lac = _cat(db, "Lácteos")
        p = _prod(db, "Queso cremoso", categoria_id=lac.id)
        filas, _ = svc.candidatos(db, modo="todos")
        assert filas[0]["destino_id"] == lac.id
        assert filas[0]["categoria_actual"] == "Lácteos"

    def test_paginacion(self, db):
        for i in range(7):
            _prod(db, f"Item {i}")
        filas, total = svc.candidatos(db, modo="todos", page=1, page_size=3)
        assert total == 7
        assert len(filas) == 3

    def test_busqueda_por_texto(self, db):
        _prod(db, "Yerba Playadito 1kg")
        otro = _prod(db, "Galletitas Oreo")
        filas, total = svc.candidatos(db, modo="todos", q="playadito")
        assert total == 1
        assert filas[0]["producto_id"] != otro.id

    def test_modo_invalido_cae_en_el_por_defecto(self, db):
        _prod(db, "X")
        filas, total = svc.candidatos(db, modo="cualquier_cosa")
        assert total == 1


# ---------------------------------------------------------------------------
# Limpieza de la respuesta de la IA
# ---------------------------------------------------------------------------

def _filas_de(db, *productos):
    filas, _ = svc.detalle(db, [p.id for p in productos])
    return filas


class TestInterpretarIA:
    def test_lee_json_envuelto_en_prose(self, db):
        _cat(db, "Bebidas")
        p = _prod(db, "Coca Cola 500ml")
        filas = _filas_de(db, p)
        cat = svc.catalogo(db)

        crudo = f"Claro! Aquí tenés:\n```json\n{{\"sugerencias\":[{{\"producto_id\":{p.id},\"categoria_id\":{cat[0][0]},\"motivo\":\"gaseosa\"}}]}}\n```"
        out = svc.interpretar_ia(crudo, filas, cat)
        assert len(out) == 1
        assert out[0]["categoria_id"] == cat[0][0]

    def test_descarta_ids_que_no_se_pidieron(self, db):
        _cat(db, "Bebidas")
        p = _prod(db, "Coca Cola 500ml")
        filas = _filas_de(db, p)
        cat = svc.catalogo(db)
        crudo = json.dumps({"sugerencias": [
            {"producto_id": p.id, "categoria_id": cat[0][0]},
            {"producto_id": 99999, "categoria_id": cat[0][0]},
        ]})
        out = svc.interpretar_ia(crudo, filas, cat)
        assert [o["producto_id"] for o in out] == [p.id]

    def test_id_de_categoria_inventada_no_pasa(self, db):
        _cat(db, "Bebidas")
        p = _prod(db, "Coca Cola 500ml")
        filas = _filas_de(db, p)
        crudo = json.dumps({"sugerencias": [
            {"producto_id": p.id, "categoria_id": 9999, "motivo": "inventada"},
        ]})
        assert svc.interpretar_ia(crudo, filas, svc.catalogo(db)) == []

    def test_nueva_categoria_es_valida_como_salida(self, db):
        p = _prod(db, "Auriculares inalámbricos")
        filas = _filas_de(db, p)
        crudo = json.dumps({"sugerencias": [
            {"producto_id": p.id, "categoria_id": None,
             "nueva_categoria": "Electrónica", "motivo": "no entra en el catálogo"},
        ]})
        out = svc.interpretar_ia(crudo, filas, svc.catalogo(db))
        assert out[0]["nueva_categoria"] == "Electrónica"
        assert out[0]["categoria_id"] is None

    def test_nueva_categoria_neutra_se_tira(self, db):
        p = _prod(db, "Cualquiera")
        filas = _filas_de(db, p)
        crudo = json.dumps({"sugerencias": [
            {"producto_id": p.id, "categoria_id": None, "nueva_categoria": "General"},
        ]})
        assert svc.interpretar_ia(crudo, filas, svc.catalogo(db)) == []

    def test_categoria_elegida_anula_la_nueva(self, db):
        beb = _cat(db, "Bebidas")
        p = _prod(db, "Coca Cola 500ml")
        filas = _filas_de(db, p)
        crudo = json.dumps({"sugerencias": [
            {"producto_id": p.id, "categoria_id": beb.id, "nueva_categoria": "Gaseosas"},
        ]})
        out = svc.interpretar_ia(crudo, filas, svc.catalogo(db))
        assert out[0]["categoria_id"] == beb.id
        assert out[0]["nueva_categoria"] is None

    def test_respuesta_sin_estructura_tira_value_error(self, db):
        p = _prod(db, "X")
        filas = _filas_de(db, p)
        with pytest.raises(ValueError):
            svc.interpretar_ia("esto no es json", filas, svc.catalogo(db))

    def test_ignora_basura_de_tipos_raros(self, db):
        _cat(db, "Bebidas")
        p = _prod(db, "Coca Cola 500ml")
        filas = _filas_de(db, p)
        crudo = json.dumps({"sugerencias": [
            "no-soy-un-objeto",
            {"producto_id": "no-numero"},
            {"producto_id": p.id, "categoria_id": "abc", "nueva_categoria": None},
        ]})
        assert svc.interpretar_ia(crudo, filas, svc.catalogo(db)) == []


# ---------------------------------------------------------------------------
# Aplicación (el único punto de escritura)
# ---------------------------------------------------------------------------

class TestAplicar:
    def test_asigna_la_categoria_elegida(self, db):
        lac = _cat(db, "Lácteos")
        p = _prod(db, "Queso cremoso")
        res = svc.aplicar(db, [{"producto_id": p.id, "categoria_id": lac.id}])

        assert res["aplicados"] == 1
        assert res["errores"] == []
        db.refresh(p)
        assert p.categoria_id == lac.id

    def test_crea_categoria_nueva(self, db):
        p = _prod(db, "Auriculares")
        res = svc.aplicar(db, [
            {"producto_id": p.id, "categoria_id": None, "nueva_categoria": "Electrónica"},
        ])

        assert res["aplicados"] == 1
        assert len(res["categorias_creadas"]) == 1
        db.refresh(p)
        nueva = db.get(Categoria, p.categoria_id)
        assert nueva.nombre == "Electrónica"

    def test_no_duplica_categoria_por_tilde_o_mayusculas(self, db):
        p1 = _prod(db, "Auriculares")
        p2 = _prod(db, "Cable HDMI")
        svc.aplicar(db, [
            {"producto_id": p1.id, "nueva_categoria": "Electrónica"},
            {"producto_id": p2.id, "nueva_categoria": "ELECTRONICA"},
        ])

        nombres = [c.nombre for c in db.query(Categoria).all()]
        assert len(nombres) == 1
        res = svc.aplicar(db, [{"producto_id": p1.id, "nueva_categoria": "Electrónica"}])
        assert res["categorias_creadas"] == []

    def test_categoria_inexistente_da_error_y_no_mueve(self, db):
        p = _prod(db, "Queso cremoso")
        res = svc.aplicar(db, [{"producto_id": p.id, "categoria_id": 424242}])

        assert res["aplicados"] == 0
        assert res["errores"][0]["motivo"] == "categoría inexistente"
        db.refresh(p)
        assert p.categoria_id is None

    def test_producto_inactivo_da_error(self, db):
        lac = _cat(db, "Lácteos")
        p = _prod(db, "Borrado", activo=False)
        res = svc.aplicar(db, [{"producto_id": p.id, "categoria_id": lac.id}])

        assert res["aplicados"] == 0
        assert res["errores"][0]["motivo"] == "producto no encontrado"

    def test_sin_destino_da_error(self, db):
        p = _prod(db, "X")
        res = svc.aplicar(db, [{"producto_id": p.id, "categoria_id": None}])
        assert res["errores"][0]["motivo"] == "sin categoría destino"

    def test_reaplicar_lo_mismo_no_cuenta(self, db):
        lac = _cat(db, "Lácteos")
        p = _prod(db, "Queso", categoria_id=lac.id)
        res = svc.aplicar(db, [{"producto_id": p.id, "categoria_id": lac.id}])
        assert res["aplicados"] == 0
        assert res["errores"] == []

    def test_reactiva_categoria_inactiva(self, db):
        cat = _cat(db, "Lácteos", activo=False)
        p = _prod(db, "Queso")
        svc.aplicar(db, [{"producto_id": p.id, "nueva_categoria": "lacteos"}])
        db.refresh(cat)
        assert cat.activo is True


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

class TestRutasRegistradas:
    """Cubre el registro del router: si algo se mueve, que falle acá."""

    @staticmethod
    def _rutas():
        from fastapi.routing import APIRoute
        from app.main import app

        def caminar(rutas):
            encontradas = []
            for ruta in rutas:
                if type(ruta).__name__ == "_IncludedRouter":
                    encontradas += caminar(ruta.original_router.routes)
                elif isinstance(ruta, APIRoute):
                    encontradas.append(ruta)
            return encontradas

        return caminar(app.routes)

    def _ruta(self, path, metodo):
        for ruta in self._rutas():
            if ruta.path == path and metodo in ruta.methods:
                return ruta
        raise AssertionError(f"No existe {metodo} {path}")

    def test_las_tres_rutas_existen(self):
        assert self._ruta("/api/productos/sugerencias/candidatos", "GET")
        assert self._ruta("/api/productos/sugerencias/ia", "POST")
        assert self._ruta("/api/productos/aplicar-sugerencias", "POST")

    def test_ia_esta_gateada_por_plan(self):
        ruta = self._ruta("/api/productos/sugerencias/ia", "POST")
        nombres = [d.name for d in ruta.dependant.dependencies]
        assert "_plan" in nombres

    def test_candidatos_pide_rol(self):
        ruta = self._ruta("/api/productos/sugerencias/candidatos", "GET")
        nombres = [d.name for d in ruta.dependant.dependencies]
        assert "_user" in nombres

    def test_aplicar_pide_rol(self):
        ruta = self._ruta("/api/productos/aplicar-sugerencias", "POST")
        nombres = [d.name for d in ruta.dependant.dependencies]
        assert "user" in nombres


class TestEndpointIA:
    def test_devuelve_lo_que_propuso_el_modelo(self, db, user, monkeypatch):
        beb = _cat(db, "Bebidas frías")
        p = _prod(db, "Coca Cola 500ml")

        def falso_completar(_db, *, sistema, usuario, como_json, max_tokens, temperatura):
            assert beb.nombre in usuario  # el catálogo real, con id
            assert f"{p.id} | Coca Cola 500ml" in usuario
            assert como_json is True
            return IARespuesta(
                texto=json.dumps({"sugerencias": [
                    {"producto_id": p.id, "categoria_id": beb.id, "motivo": "gaseosa"},
                ]}),
                tokens_out=30,
            )

        monkeypatch.setattr(ia_registro, "completar", falso_completar)
        resp = router.sugerir_con_ia(
            SugerenciasIARequest(productos_ids=[p.id]),
            db=db, _user=user, _plan=user,
        )
        assert resp.data.lote[0].categoria_id == beb.id
        assert resp.data.tokens_out == 30

    def test_sin_ia_configurada_devuelve_402(self, db, user, monkeypatch):
        p = _prod(db, "Coca Cola 500ml")

        def falla(*args, **kwargs):
            raise IADeshabilitada("La IA está deshabilitada o falta configurar la API key")

        monkeypatch.setattr(ia_registro, "completar", falla)
        with pytest.raises(HTTPException) as exc:
            router.sugerir_con_ia(
                SugerenciasIARequest(productos_ids=[p.id]),
                db=db, _user=user, _plan=user,
            )
        assert exc.value.status_code == 402

    def test_lote_mayor_se_recorta(self, db, user, monkeypatch):
        prompts = []

        def falso_completar(_db, *, sistema, usuario, como_json, max_tokens, temperatura):
            prompts.append(usuario)
            return IARespuesta(texto=json.dumps({"sugerencias": []}))

        monkeypatch.setattr(ia_registro, "completar", falso_completar)
        ids = [_prod(db, f"Prod {i}").id for i in range(30)]

        router.sugerir_con_ia(
            SugerenciasIARequest(productos_ids=ids),
            db=db, _user=user, _plan=user,
        )
        # Un solo prompt, con a lo sumo TAMANO_LOTE_IA productos (3 campos por fila).
        assert len(prompts) == 1
        assert prompts[0].count(" | Prod ") == svc.TAMANO_LOTE_IA

    def test_sin_productos_validos_devuelve_400(self, db, user):
        with pytest.raises(HTTPException) as exc:
            router.sugerir_con_ia(
                SugerenciasIARequest(productos_ids=[123456]),
                db=db, _user=user, _plan=user,
            )
        assert exc.value.status_code == 400


class TestEndpointAplicar:
    def test_escribe_y_audita(self, db, user):
        lac = _cat(db, "Lácteos")
        p = _prod(db, "Queso cremoso")

        resp = router.aplicar_sugerencias(
            AplicarRequest(cambios=[CambioRequest(producto_id=p.id, categoria_id=lac.id)]),
            db=db, user=user,
        )
        assert resp.data["aplicados"] == 1
        db.refresh(p)
        assert p.categoria_id == lac.id

        from app.models.auditoria import Auditoria
        eventos = [a.tipo for a in db.query(Auditoria).all()]
        assert "recategorizacion_producto" in eventos

    def test_mas_de_500_cambios_se_rechaza(self, db, user):
        cambios = [CambioRequest(producto_id=i) for i in range(501)]
        with pytest.raises(HTTPException) as exc:
            router.aplicar_sugerencias(AplicarRequest(cambios=cambios), db=db, user=user)
        assert exc.value.status_code == 400


class TestEndpointCandidatos:
    def test_lista_con_sugerencia_y_paginacion(self, db, user):
        _cat(db, "Golosinas")
        _prod(db, "Alfajor Jorgito")
        _prod(db, "Caja marrón")

        resp = router.listar_candidatos(
            modo="todos", q="", page=1, page_size=50, db=db, _user=user,
        )
        assert resp.data.total == 2
        por_nombre = {f.nombre: f for f in resp.data.items}
        assert por_nombre["Alfajor Jorgito"].sugerencia is not None
        assert por_nombre["Caja Marrón"].sugerencia is None
