#!/usr/bin/env bash
# Actualiza la imagen de todos los clientes y guarda el .env anterior.
# Uso: ./actualizar_clientes.sh <imagen> [root]
#   ./actualizar_clientes.sh erp-comercio:abc1234
# Rollback: volver a correr con la imagen anterior (los .env.bak quedan al lado).
set -euo pipefail

IMAGEN="${1:?uso: actualizar_clientes.sh <imagen> [root]}"
ROOT="${2:-/srv/erp-clientes}"

if [ ! -d "$ROOT" ]; then
  echo "No existe $ROOT" >&2
  exit 1
fi

for dir in "$ROOT"/*/; do
  [ -f "${dir}docker-compose.yml" ] || continue
  slug="$(basename "$dir")"
  cp "${dir}.env" "${dir}.env.bak"
  sed -i "s|^IMAGEN=.*|IMAGEN=${IMAGEN}|" "${dir}.env"
  echo "== $slug"
  (cd "$dir" && docker compose up -d)
done

echo ""
echo "Listo. Rollback: ./actualizar_clientes.sh <imagen-anterior>"
echo "Si algo falla en un cliente: cd $ROOT/<slug> && docker compose logs --tail=100"
