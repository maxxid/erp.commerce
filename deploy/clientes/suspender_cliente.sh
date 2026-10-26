#!/usr/bin/env bash
# Detiene un cliente sin borrar datos ni configuración.
# Uso: ./suspender_cliente.sh <slug> [root]
set -euo pipefail

SLUG="${1:?uso: suspender_cliente.sh <slug> [root]}"
ROOT="${2:-/srv/erp-clientes}"

if [ ! -d "$ROOT/$SLUG" ]; then
  echo "No existe $ROOT/$SLUG" >&2
  exit 1
fi

cd "$ROOT/$SLUG"
docker compose stop
echo "Cliente $SLUG detenido. Datos en $ROOT/$SLUG/data"
echo "Para reactivarlo: cd $ROOT/$SLUG && docker compose start"
