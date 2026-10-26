#!/usr/bin/env python3
"""Renueva (o cambia el plan de) la licencia de un cliente ya dado de alta.

    python3 deploy/clientes/renovar_licencia.py --slug cliente1 --dias 365 --plan pro

Corre el generador de licencias dentro del contenedor del cliente, con el
`LICENCIA_SECRET` que ya está en su `.env`, y verifica que la instancia la vea
válida. No hace falta reiniciar: la licencia se lee de la base en cada request.
"""

import argparse
import json
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

ROOT_POR_DEFECTO = Path("/srv/erp-clientes")


def _correr(cmd, cwd):
    print("  $ " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        if r.stderr.strip():
            print(r.stderr.strip(), file=sys.stderr)
        raise SystemExit(f"Falló: {' '.join(str(c) for c in cmd)}")


def _cargar_registro(root):
    path = root / "clientes.json"
    if not path.exists():
        return {"clientes": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {"clientes": data}
    data.setdefault("clientes", [])
    return data


def _guardar_registro(root, data):
    path = root / "clientes.json"
    temporal = path.with_suffix(".json.tmp")
    temporal.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporal.replace(path)


def _esperar_salud(puerto, segundos=60):
    limite = time.time() + segundos
    url = f"http://127.0.0.1:{puerto}/health"
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                if json.loads(resp.read().decode("utf-8")).get("status") == "ok":
                    return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit(f"El contenedor no respondió {url} a tiempo")


def _estado_licencia(puerto):
    url = f"http://127.0.0.1:{puerto}/api/licencia/estado"
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8")).get("data", {})


def main():
    parser = argparse.ArgumentParser(description="Renovar la licencia de un cliente")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--plan", default=None)
    parser.add_argument("--cliente", default=None)
    parser.add_argument("--root", default=str(ROOT_POR_DEFECTO))
    args = parser.parse_args()

    if args.dias <= 0:
        raise SystemExit("--dias tiene que ser mayor a 0")

    root = Path(args.root).resolve()
    registro = _cargar_registro(root)
    entrada = next((c for c in registro["clientes"] if c.get("slug") == args.slug), None)
    if not entrada:
        raise SystemExit(f"No está '{args.slug}' en {root / 'clientes.json'}")

    cliente_dir = root / args.slug
    if not (cliente_dir / "docker-compose.yml").exists():
        raise SystemExit(f"Falta {cliente_dir / 'docker-compose.yml'}")

    plan = args.plan or entrada.get("plan") or "trial"
    cliente = args.cliente or entrada.get("nombre") or args.slug

    print(f"Renovando {args.slug} — plan {plan}, {args.dias} días")
    _correr(
        ["docker", "compose", "run", "--rm", "--entrypoint", "python", "erp",
         "scripts/seed_licencia_cliente.py",
         "--db", "/data/erp_comercio.db",
         "--machine-id", args.slug,
         "--cliente", cliente,
         "--plan", plan,
         "--dias", str(args.dias),
         "--reemplazar"],
        cwd=cliente_dir,
    )

    _esperar_salud(entrada["puerto"])
    estado = _estado_licencia(entrada["puerto"])
    if not estado.get("valida"):
        raise SystemExit("La instancia no ve la licencia como válida")

    entrada["plan"] = plan
    entrada["vence"] = (estado.get("fecha_expiracion") or "")[:10]
    entrada["estado"] = "activo"
    _guardar_registro(root, registro)

    print("")
    print(f"Licencia de {args.slug} renovada hasta {entrada['vence']} (plan {plan})")


if __name__ == "__main__":
    main()
