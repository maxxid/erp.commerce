"""Color por categoría: columna nueva, defaults y validación.

`categorias.color` es `#RRGGBB` o NULL. NULL significa "usá el color por
defecto del rubro", que vive en el front: así una categoría recién creada ya
se ve con color sin que nadie la edite.
"""

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.usuario import Usuario
from app.routers import categorias as router
from app.schemas.categoria import CategoriaCreate, CategoriaUpdate


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


class TestColor:
    def test_crear_acepta_color(self, db, user):
        resp = router.crear(
            CategoriaCreate(nombre="Golosinas", color="#f59e0b"), db=db, user=user
        )
        assert resp.data.color == "#f59e0b"

    def test_crear_sin_color_queda_null(self, db, user):
        resp = router.crear(CategoriaCreate(nombre="Frescos"), db=db, user=user)
        assert resp.data.color is None

    def test_actualizar_el_color(self, db, user):
        cat = router.crear(CategoriaCreate(nombre="Bebidas"), db=db, user=user).data

        resp = router.actualizar(
            cat.id, CategoriaUpdate(color="#06b6d4"), db=db, user=user
        )

        assert resp.data.color == "#06b6d4"

    def test_el_listado_lo_devuelve(self, db, user):
        router.crear(
            CategoriaCreate(nombre="Limpieza", color="#8b5cf6"), db=db, user=user
        )
        resp = router.listar(db=db, user=user)

        assert len(resp.data) == 1
        assert resp.data[0].color == "#8b5cf6"

    @pytest.mark.parametrize("malo", ["rojo", "#fff", "#12345", "f59e0b", "#gggggg"])
    def test_color_invalido_no_pasa(self, malo):
        with pytest.raises(ValidationError):
            CategoriaUpdate(color=malo)

    def test_color_valido_si_pasa(self):
        assert CategoriaUpdate(color="#ABCDEF").color == "#ABCDEF"
        assert CategoriaUpdate(color=None).color is None
