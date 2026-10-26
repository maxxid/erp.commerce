"""Siembra la licencia de un cliente antes del primer arranque.

El login exige una licencia válida, y en una instancia vendida a un cliente
`LICENCIA_AUTO=false` para que no se auto-renueve. Por eso la licencia se crea
antes de levantar el contenedor.

Uso (dentro de la imagen o con el venv activado):

    python scripts/seed_licencia_cliente.py \
        --db /data/erp_comercio.db \
        --machine-id cliente1 \
        --cliente "Almacén Don José" \
        --plan trial --dias 30

  Para renovar una licencia existente, agregar --reemplazar.

`LICENCIA_SECRET` tiene que venir del entorno y ser el mismo secreto maestro en
todas las instancias; si falta, se usa el JWT_SECRET de esta instalación y la
clave sólo podrá emitirse/validarse acá.
"""

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_pre = argparse.ArgumentParser(add_help=False)
_pre.add_argument("--db", default=None)
_db_args, _ = _pre.parse_known_args()
if not _db_args.db:
    sys.exit("ERROR: falta --db (ruta al archivo SQLite del cliente)")
os.environ["DATABASE_URL"] = f"sqlite:///{Path(_db_args.db).resolve().as_posix()}"

from app.config import settings  # noqa: E402
from app.database import Base, SessionLocal, engine  # noqa: E402
import app.models as _models  # noqa: E402,F401  registra todos los modelos
from app.models.licencia import Licencia  # noqa: E402
from app.services import licencia_service, planes_service  # noqa: E402


def _ahora():
    return datetime.now(timezone.utc)


def _vigente_para(db, machine_id):
    for lic in db.query(Licencia).filter(
        Licencia.machine_id == machine_id, Licencia.activa == True
    ).all():
        exp = lic.fecha_expiracion
        if exp and exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        if exp and exp > _ahora():
            return lic
    return None


def main():
    parser = argparse.ArgumentParser(description="Siembra la licencia de un cliente")
    parser.add_argument("--db", required=True, help="Archivo SQLite de la instancia")
    parser.add_argument("--machine-id", required=True, help="Slug del cliente")
    parser.add_argument("--cliente", required=True, help="Nombre comercial")
    parser.add_argument("--plan", default="trial", choices=sorted(planes_service.PLANES))
    parser.add_argument("--dias", type=int, default=30)
    parser.add_argument("--no-activar", action="store_true", help="Crear la licencia inactiva")
    parser.add_argument("--reemplazar", action="store_true", help="Reemplazar la vigente")
    args = parser.parse_args()

    if args.dias <= 0:
        sys.exit("ERROR: --dias tiene que ser mayor a 0")

    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        vigente = _vigente_para(db, args.machine_id)
        if vigente and not args.reemplazar:
            print(f"Ya hay una licencia vigente para {args.machine_id}: {vigente.clave}")
            print(f"Vence: {vigente.fecha_expiracion.isoformat()}")
            print("Usá --reemplazar para emitir una nueva.")
            return

        if vigente:
            vigente.activa = False
            db.commit()

        expiracion = _ahora() + timedelta(days=args.dias)
        clave = licencia_service.generar_clave(args.cliente, args.machine_id, expiracion)
        lic = Licencia(
            clave=clave,
            cliente=args.cliente,
            machine_id=args.machine_id,
            plan=args.plan,
            fecha_expiracion=expiracion,
            activa=not args.no_activar,
        )
        db.add(lic)
        db.commit()
        db.refresh(lic)

        print(f"DB:         {os.environ['DATABASE_URL']}")
        print(f"Cliente:    {lic.cliente}")
        print(f"Machine ID: {lic.machine_id}")
        print(f"Plan:       {lic.plan}")
        print(f"Vence:      {lic.fecha_expiracion.isoformat()}")
        print(f"Clave:      {lic.clave}")
        print(f"Activa:     {'sí' if lic.activa else 'no'}")
        if not settings.LICENCIA_SECRET:
            print("AVISO: LICENCIA_SECRET no está seteado; se usó JWT_SECRET.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
