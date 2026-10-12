"""Tests de planes de servicio y gating de features por licencia.

El gating es lo que permite vender ApexERP con/sin IA: `requiere_feature`
tiene que dejar pasar al plan correcto y devolver 402 (Payment Required) al
que no lo tiene, para que el frontend ofrezca la mejora en vez de fallar raro.
"""

from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi import HTTPException

import app.models as _m  # noqa: F401  registra todos los modelos en Base.metadata
from app.database import Base as _Base
from app.models.licencia import Licencia
from app.models.usuario import Usuario
from app.services import config_service, licencia_service, planes_service
from app.services.ia import registro as ia_registro


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    _Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def _licencia(db, plan="pro", dias=30, activa=True, limite_ia_mes=None, cliente="Test"):
    lic = Licencia(
        clave=f"APX-TEST-{plan}-{db.query(Licencia).count()}",
        cliente=cliente,
        machine_id="m1",
        plan=plan,
        limite_ia_mes=limite_ia_mes,
        fecha_expiracion=datetime.now(timezone.utc) + timedelta(days=dias),
        activa=activa,
    )
    db.add(lic)
    db.commit()
    db.refresh(lic)
    return lic


def _usuario(db, rol="admin"):
    user = Usuario(
        username=f"u{db.query(Usuario).count()}", password_hash="x",
        nombre="Test", rol=rol,
    )
    db.add(user)
    db.commit()
    return user


class TestPlanDe:
    def test_sin_licencia_es_trial(self, db):
        assert planes_service.plan_de(db) == "trial"

    def test_licencia_pro(self, db):
        _licencia(db, plan="pro")
        assert planes_service.plan_de(db) == "pro"

    def test_licencia_trial(self, db):
        _licencia(db, plan="trial")
        assert planes_service.plan_de(db) == "trial"

    def test_licencia_vencida_es_trial(self, db):
        _licencia(db, plan="pro", dias=-1)
        assert planes_service.plan_de(db) == "trial"

    def test_licencia_inactiva_es_trial(self, db):
        _licencia(db, plan="pro", activa=False)
        assert planes_service.plan_de(db) == "trial"

    def test_plan_desconocido_cae_en_defecto(self, db):
        _licencia(db, plan="plan-inventado")
        assert planes_service.plan_de(db) == "trial"

    def test_plan_vacio_cae_en_defecto(self, db):
        lic = _licencia(db, plan="pro")
        lic.plan = ""
        db.commit()
        assert planes_service.plan_de(db) == "trial"

    def test_toma_la_de_mayor_expiracion(self, db):
        _licencia(db, plan="trial", dias=5)
        _licencia(db, plan="pro", dias=400)
        assert planes_service.plan_de(db) == "pro"


class TestFeatures:
    def test_trial_sin_ia(self, db):
        _licencia(db, plan="trial")
        assert planes_service.tiene_feature(db, "ia") is False

    def test_trial_con_sectores(self, db):
        _licencia(db, plan="trial")
        assert planes_service.tiene_feature(db, "sectores") is True

    def test_basico_sin_ia(self, db):
        _licencia(db, plan="basico")
        assert planes_service.tiene_feature(db, "ia") is False

    def test_pro_con_ia(self, db):
        _licencia(db, plan="pro")
        assert planes_service.tiene_feature(db, "ia") is True

    def test_enterprise_con_ia(self, db):
        _licencia(db, plan="enterprise")
        assert planes_service.tiene_feature(db, "ia") is True

    def test_sin_licencia_ninguna_feature(self, db):
        assert planes_service.features_de(db) == {"ia": False, "sectores": True}

    def test_feature_desconocida_es_false(self, db):
        _licencia(db, plan="pro")
        assert planes_service.tiene_feature(db, "feature-inventada") is False

    def test_todos_los_planes_definen_todas_las_features(self):
        for pid, plan in planes_service.PLANES.items():
            for feature in planes_service.FEATURES:
                assert feature in plan["features"], f"{pid} no define {feature}"

    def test_catalogo_no_expone_estructura_interna(self):
        cat = planes_service.catalogo()
        assert {c["id"] for c in cat} == set(planes_service.PLANES)
        for c in cat:
            assert set(c) == {"id", "nombre", "descripcion", "features"}


class TestLimiteIa:
    def test_sin_licencia_usa_config(self, db):
        config_service.set_config(db, "ia_limite_mes", "77")
        assert planes_service.limite_ia_de(db) == 77

    def test_sin_licencia_ni_config_usa_default(self, db):
        assert planes_service.limite_ia_de(db) == ia_registro.LIMITE_MES_DEFECTO

    def test_override_de_licencia_pisa_config(self, db):
        config_service.set_config(db, "ia_limite_mes", "77")
        _licencia(db, plan="pro", limite_ia_mes=5)
        assert planes_service.limite_ia_de(db) == 5

    def test_licencia_sin_override_usa_config(self, db):
        config_service.set_config(db, "ia_limite_mes", "77")
        _licencia(db, plan="pro")
        assert planes_service.limite_ia_de(db) == 77

    def test_licencia_vencida_no_aplica_su_override(self, db):
        config_service.set_config(db, "ia_limite_mes", "77")
        _licencia(db, plan="pro", dias=-1, limite_ia_mes=5)
        assert planes_service.limite_ia_de(db) == 77

    def test_config_invalida_usa_default(self, db):
        config_service.set_config(db, "ia_limite_mes", "basura")
        assert planes_service.limite_ia_de(db) == ia_registro.LIMITE_MES_DEFECTO

    def test_limite_cero_significa_sin_limite(self, db):
        config_service.set_config(db, "ia_limite_mes", "0")
        assert planes_service.limite_ia_de(db) == 0


class TestRequiereFeature:
    def test_plan_sin_ia_tira_402(self, db):
        from app.auth.dependencies import requiere_feature

        _licencia(db, plan="trial")
        user = _usuario(db)
        checker = requiere_feature("ia")
        with pytest.raises(HTTPException) as exc:
            checker(db=db, user=user)
        assert exc.value.status_code == 402
        assert "ia" in exc.value.detail

    def test_plan_con_ia_pasa(self, db):
        from app.auth.dependencies import requiere_feature

        _licencia(db, plan="pro")
        user = _usuario(db)
        assert requiere_feature("ia")(db=db, user=user) is user

    def test_sin_licencia_tira_402(self, db):
        from app.auth.dependencies import requiere_feature

        user = _usuario(db)
        with pytest.raises(HTTPException) as exc:
            requiere_feature("ia")(db=db, user=user)
        assert exc.value.status_code == 402

    def test_feature_de_todos_los_planes_pasa_en_trial(self, db):
        from app.auth.dependencies import requiere_feature

        _licencia(db, plan="trial")
        user = _usuario(db)
        assert requiere_feature("sectores")(db=db, user=user) is user


class TestCrearLicencia:
    def test_plan_explicito(self, db):
        res = licencia_service.crear_licencia(db, "Cliente", "m1", 30, plan="pro")
        assert res["plan"] == "pro"

    def test_plan_invalido_cae_en_trial(self, db):
        res = licencia_service.crear_licencia(db, "Cliente", "m1", 30, plan="inventado")
        assert res["plan"] == "trial"

    def test_plan_default_es_trial(self, db):
        res = licencia_service.crear_licencia(db, "Cliente", "m1", 30)
        assert res["plan"] == "trial"

    def test_plan_conserva_minusculas(self, db):
        res = licencia_service.crear_licencia(db, "Cliente", "m1", 30, plan="Enterprise")
        assert res["plan"] == "enterprise"

    def test_plan_recien_creado_no_da_ia(self, db):
        licencia_service.crear_licencia(db, "Cliente", "m1", 30)
        assert planes_service.tiene_feature(db, "ia") is False


class TestEstadoEndpoint:
    """El endpoint /api/licencia/estado es lo que consume el frontend para gatear."""

    def _datos(self, db):
        from app.routers.licencia import estado
        return estado(db=db).data

    def test_sin_licencia_declara_plan_y_features(self, db):
        datos = self._datos(db)
        assert datos["plan"] == "trial"
        assert datos["features"]["ia"] is False
        assert datos["ia_disponible"] is False
        assert datos["tiene_licencia"] is False

    def test_plan_pro_sin_key_no_esta_disponible(self, db, monkeypatch):
        monkeypatch.setattr(ia_registro.settings, "IA_DEFAULT_API_KEY", "")
        _licencia(db, plan="pro")
        datos = self._datos(db)
        assert datos["features"]["ia"] is True
        assert datos["ia_configurada"] is False
        assert datos["ia_disponible"] is False

    def test_plan_pro_con_key_esta_disponible(self, db, monkeypatch):
        monkeypatch.setattr(ia_registro.settings, "IA_DEFAULT_API_KEY", "gsk_abcd1234efgh")
        _licencia(db, plan="pro")
        datos = self._datos(db)
        assert datos["ia_disponible"] is True

    def test_plan_trial_con_key_no_esta_disponible(self, db, monkeypatch):
        monkeypatch.setattr(ia_registro.settings, "IA_DEFAULT_API_KEY", "gsk_abcd1234efgh")
        _licencia(db, plan="trial")
        datos = self._datos(db)
        assert datos["ia_configurada"] is True
        assert datos["ia_disponible"] is False

    def test_incluye_uso_y_limite(self, db):
        _licencia(db, plan="pro", limite_ia_mes=250)
        config_service.set_config(db, "ia_uso_2026_10", '{"llamadas": 3, "tokens_in": 9, "tokens_out": 4}')
        datos = self._datos(db)
        assert datos["ia_uso"] == {"llamadas": 3, "limite": 250}

    def test_expone_catalogo_de_planes(self, db):
        datos = self._datos(db)
        assert {p["id"] for p in datos["planes"]} == set(planes_service.PLANES)

    def test_no_fuga_la_api_key(self, db, monkeypatch):
        monkeypatch.setattr(ia_registro.settings, "IA_DEFAULT_API_KEY", "gsk_super_secreta_xyz")
        config_service.set_config(db, "ia_api_key", "sk_cliente_secreta_abc")
        import json
        assert "gsk_super_secreta_xyz" not in json.dumps(self._datos(db), ensure_ascii=False)
        assert "sk_cliente_secreta_abc" not in json.dumps(self._datos(db), ensure_ascii=False)
