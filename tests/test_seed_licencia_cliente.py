"""El generador de licencias de un cliente.

Se prueba en subproceso a propósito: el script arma el engine de SQLAlchemy al
importar `app.database`, así que importarlo en el proceso de pytest cambiaría el
engine global que usan los demás tests.
"""

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SCRIPT = RAIZ / "scripts" / "seed_licencia_cliente.py"


def _correr(db, *extra):
    env = {**os.environ, "LICENCIA_SECRET": "secreto-maestro-de-prueba"}
    return subprocess.run(
        [
            sys.executable, str(SCRIPT),
            "--db", str(db),
            "--machine-id", "cliente-test",
            "--cliente", "Cliente Test",
            "--plan", "trial",
            "--dias", "30",
            *extra,
        ],
        cwd=str(RAIZ),
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )


def _licencias(db):
    with sqlite3.connect(str(db)) as conn:
        return conn.execute(
            "SELECT clave, machine_id, plan, activa FROM licencias ORDER BY id"
        ).fetchall()


def test_siembra_la_primera_licencia(tmp_path):
    db = tmp_path / "cliente.db"
    r = _correr(db)

    assert r.returncode == 0, r.stderr
    assert "Clave:" in r.stdout
    filas = _licencias(db)
    assert len(filas) == 1
    clave, machine_id, plan, activa = filas[0]
    assert clave.startswith("APX-")
    assert machine_id == "cliente-test"
    assert plan == "trial"
    assert activa == 1


def test_es_idempotente_sin_reemplazar(tmp_path):
    db = tmp_path / "cliente.db"
    assert _correr(db).returncode == 0

    r = _correr(db)

    assert r.returncode == 0, r.stderr
    assert "Ya hay una licencia vigente" in r.stdout
    assert len(_licencias(db)) == 1


def test_reemplazar_desactiva_la_anterior(tmp_path):
    db = tmp_path / "cliente.db"
    assert _correr(db).returncode == 0

    r = _correr(db, "--plan", "pro", "--dias", "365", "--reemplazar")

    assert r.returncode == 0, r.stderr
    filas = _licencias(db)
    assert len(filas) == 2
    assert filas[0][3] == 0, "la licencia vieja debe quedar inactiva"
    assert filas[1][2] == "pro"
    assert filas[1][3] == 1
