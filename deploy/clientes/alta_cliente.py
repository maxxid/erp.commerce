#!/usr/bin/env python3
"""Alta de un cliente en la VM (Docker multi-instance).

Crea la carpeta, genera los secretos, siembra la licencia, levanta el
contenedor, configura nginx, pide el certificado y hace un smoke test.

Se corre en el servidor, como root:

    python3 deploy/clientes/alta_cliente.py \
        --slug cliente1 \
        --nombre "Almacén Don José" \
        --dominio cliente1.erp.imprenta.store \
        --plan trial --dias 30 \
        --imagen erp-comercio:<git-sha> \
        --certbot-email dueno@imprenta.store

El diseño y los runbooks están en `MULTITENANT.md`.
"""

import argparse
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT_POR_DEFECTO = Path("/srv/erp-clientes")
UID_CLIENTE = 10001
PUERTO_MIN, PUERTO_MAX = 5101, 5199
SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9-]{1,28}[a-z0-9]$")


def _correr(cmd, cwd=None, obligatorio=True):
    print("  $ " + " ".join(str(c) for c in cmd))
    r = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if r.stdout.strip():
        print(r.stdout.strip())
    if r.returncode != 0:
        if r.stderr.strip():
            print(r.stderr.strip(), file=sys.stderr)
        if obligatorio:
            raise SystemExit(f"Falló: {' '.join(str(c) for c in cmd)}")
        print("AVISO: el comando falló, se continúa.", file=sys.stderr)
    return r


def _render(nombre, valores):
    texto = (BASE / nombre).read_text(encoding="utf-8").replace("\r\n", "\n")
    for clave, valor in valores.items():
        texto = texto.replace("{{" + clave + "}}", str(valor))
    return texto


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
    os.replace(temporal, path)


def _puerto_libre(puerto):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            s.bind(("127.0.0.1", puerto))
            return True
        except OSError:
            return False


def _asignar_puerto(registro):
    usados = {c.get("puerto") for c in registro["clientes"]}
    for puerto in range(PUERTO_MIN, PUERTO_MAX + 1):
        if puerto in usados:
            continue
        if _puerto_libre(puerto):
            return puerto
    raise SystemExit(f"No hay puertos libres entre {PUERTO_MIN} y {PUERTO_MAX}")


def _secreto_maestro(root, argumento):
    if argumento:
        return argumento
    if os.environ.get("LICENCIA_SECRET"):
        return os.environ["LICENCIA_SECRET"]
    path = root / ".licencia_secret"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    secreto = secrets.token_hex(32)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(secreto + "\n")
    print(f"  Secreto maestro generado en {path} (guardalo: renueva todas las licencias)")
    return secreto


def _escribir_env(path, valores):
    lineas = [f"{clave}={valor}" for clave, valor in valores.items()]
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")


def _chown_cliente(cliente_dir):
    if os.geteuid() != 0:
        print("  AVISO: no sos root; no se pudo ajustar el dueño de los datos.")
        return
    for p in [cliente_dir, *cliente_dir.rglob("*")]:
        os.chown(p, UID_CLIENTE, UID_CLIENTE)


def _esperar_salud(puerto, segundos=90):
    limite = time.time() + segundos
    url = f"http://127.0.0.1:{puerto}/health"
    while time.time() < limite:
        try:
            with urllib.request.urlopen(url, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("status") == "ok":
                return
        except Exception:
            pass
        time.sleep(2)
    raise SystemExit(f"El contenedor no respondió {url} a tiempo")


def _get_json(url):
    with urllib.request.urlopen(url, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _post_json(url, payload):
    cuerpo = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=cuerpo, headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _smoke(puerto, admin_password):
    _get_json(f"http://127.0.0.1:{puerto}/health")
    estado = _get_json(f"http://127.0.0.1:{puerto}/api/licencia/estado")
    if not estado.get("data", {}).get("valida"):
        raise SystemExit("La licencia no quedó válida en la instancia nueva")
    login = _post_json(
        f"http://127.0.0.1:{puerto}/api/auth/login",
        {"username": "admin", "password": admin_password},
    )
    if not login.get("data", {}).get("access_token"):
        raise SystemExit("El login de admin falló en la instancia nueva")
    return estado["data"]


def _configurar_nginx(slug, dominio, puerto):
    if os.geteuid() != 0:
        print("  AVISO: no sos root; salteo nginx.")
        return False
    contenido = _render("nginx.template.conf", {"DOMINIO": dominio, "PUERTO": puerto})
    disponible = Path("/etc/nginx/sites-available") / f"erp-{slug}"
    disponible.write_text(contenido, encoding="utf-8")
    habilitado = Path("/etc/nginx/sites-enabled") / f"erp-{slug}"
    if habilitado.exists() or habilitado.is_symlink():
        habilitado.unlink()
    habilitado.symlink_to(disponible)
    _correr(["nginx", "-t"])
    _correr(["systemctl", "reload", "nginx"])
    return True


def _certificado(dominio, email):
    if not email:
        print(f"  Sin --certbot-email: queda en HTTP. Después: certbot --nginx -d {dominio}")
        return
    _correr(
        ["certbot", "--nginx", "-d", dominio, "--non-interactive",
         "--agree-tos", "-m", email, "--redirect"],
        obligatorio=False,
    )


def main():
    parser = argparse.ArgumentParser(description="Alta de un cliente del ERP")
    parser.add_argument("--slug", required=True)
    parser.add_argument("--nombre", required=True)
    parser.add_argument("--dominio", default=None,
                        help="Por defecto <slug>.erp.imprenta.store")
    parser.add_argument("--plan", default="trial",
                        choices=["trial", "basico", "pro", "enterprise"])
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--imagen", default="erp-comercio:latest")
    parser.add_argument("--memoria", default="512m",
                        help="Límite de RAM del contenedor (ej. 256m, 512m)")
    parser.add_argument("--root", default=str(ROOT_POR_DEFECTO))
    parser.add_argument("--licencia-secret", default=None)
    parser.add_argument("--admin-password", default=None,
                        help="Por defecto se genera uno aleatorio")
    parser.add_argument("--certbot-email", default=None)
    parser.add_argument("--sin-nginx", action="store_true")
    args = parser.parse_args()

    if not SLUG_RE.match(args.slug):
        raise SystemExit("Slug inválido: usá minúsculas, números y guiones (3 a 30 caracteres)")
    if args.dias <= 0:
        raise SystemExit("--dias tiene que ser mayor a 0")

    root = Path(args.root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    registro = _cargar_registro(root)

    if any(c.get("slug") == args.slug for c in registro["clientes"]):
        raise SystemExit(f"El cliente '{args.slug}' ya está en {root / 'clientes.json'}")
    cliente_dir = root / args.slug
    if cliente_dir.exists():
        raise SystemExit(f"Ya existe {cliente_dir}")

    dominio = args.dominio or f"{args.slug}.erp.imprenta.store"
    puerto = _asignar_puerto(registro)
    admin_password = args.admin_password or secrets.token_urlsafe(12)

    print(f"Alta de {args.slug}")
    print(f"  Dominio: {dominio}")
    print(f"  Puerto:  {puerto}")
    print(f"  Imagen:  {args.imagen}")

    data_dir = cliente_dir / "data"
    backups_dir = data_dir / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    env = {
        "SLUG": args.slug,
        "PUERTO": puerto,
        "IMAGEN": args.imagen,
        "MEMORIA": args.memoria,
        "JWT_SECRET": secrets.token_hex(32),
        "LICENCIA_SECRET": _secreto_maestro(root, args.licencia_secret),
        "ADMIN_PASSWORD_INICIAL": admin_password,
        "R2_ENDPOINT": os.environ.get("R2_ENDPOINT", ""),
        "R2_ACCESS_KEY": os.environ.get("R2_ACCESS_KEY", ""),
        "R2_SECRET_KEY": os.environ.get("R2_SECRET_KEY", ""),
        "R2_BUCKET": os.environ.get("R2_BUCKET", "erp-backups"),
    }
    _escribir_env(cliente_dir / ".env", env)
    (cliente_dir / "docker-compose.yml").write_text(
        (BASE / "docker-compose.template.yml").read_text(encoding="utf-8").replace("\r\n", "\n"),
        encoding="utf-8",
    )
    _chown_cliente(cliente_dir)

    if not env["R2_ACCESS_KEY"]:
        print("  AVISO: sin R2_* en el entorno, los respaldos quedan sólo locales.")

    print("Sembrando licencia...")
    _correr(
        ["docker", "compose", "run", "--rm", "--entrypoint", "python", "erp",
         "scripts/seed_licencia_cliente.py",
         "--db", "/data/erp_comercio.db",
         "--machine-id", args.slug,
         "--cliente", args.nombre,
         "--plan", args.plan,
         "--dias", str(args.dias)],
        cwd=cliente_dir,
    )

    print("Levantando contenedor...")
    _correr(["docker", "compose", "up", "-d"], cwd=cliente_dir)
    _esperar_salud(puerto)

    if not args.sin_nginx:
        print("Configurando nginx...")
        _configurar_nginx(args.slug, dominio, puerto)
        _certificado(dominio, args.certbot_email)

    print("Smoke test...")
    licencia = _smoke(puerto, admin_password)

    vence = (datetime.now(timezone.utc) + timedelta(days=args.dias)).date().isoformat()
    registro["clientes"].append({
        "slug": args.slug,
        "nombre": args.nombre,
        "dominio": dominio,
        "puerto": puerto,
        "plan": args.plan,
        "vence": vence,
        "imagen": args.imagen,
        "creado": datetime.now(timezone.utc).isoformat(),
        "estado": "activo",
    })
    _guardar_registro(root, registro)

    print("")
    print("=" * 60)
    print(f"Cliente {args.slug} listo")
    print(f"  URL:       https://{dominio}/app")
    print(f"  Usuario:   admin")
    print(f"  Password:  {admin_password}   (cambiala al entrar)")
    print(f"  Plan:      {licencia.get('plan')} — vence {vence}")
    print(f"  Datos:     {data_dir}")
    print(f"  Registro:  {root / 'clientes.json'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
