"""Barrido de reconciliación stock cache vs lotes.

Uso (en el server):
    cd /opt/erp-comercio && sudo -u erp bash -c 'source venv/bin/activate && python scripts/resync_stock_lotes.py'

Reconcilia `productos.stock_actual` (la verdad, cargada desde el panel/migración)
contra la suma de `lotes.cantidad_actual` de lotes activos, usando la misma
lógica FEFO del sistema:
- Si stock_actual > lotes: crea/refuerza un lote "AJUSTE" con la diferencia.
- Si stock_actual < lotes: descuenta via FEFO la diferencia (expira primero).
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.models.producto import Producto
from app.models.usuario import Usuario

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger("resync")


def main():
    db = SessionLocal()
    try:
        admin = (
            db.query(Usuario)
            .filter(Usuario.rol == "admin")
            .order_by(Usuario.id.asc())
            .first()
        )
        if not admin:
            print("ERROR: no hay usuarios admin para registrar los movimientos")
            return
        usuario_id = admin.id

        from app.services import stock_service
        from app.services.producto_service import _suma_lotes_activos

        productos = db.query(Producto).filter(Producto.activo == True).all()
        corregidos = 0
        sin_cambio = 0
        errores = 0

        for p in productos:
            suma = _suma_lotes_activos(db, p.id)
            diff = round(p.stock_actual - suma, 4)
            if abs(diff) < 0.0001:
                sin_cambio += 1
                continue

            tipo = "entrada" if diff > 0 else "salida"
            try:
                mov, consumos = stock_service.ajustar_stock_por_lote(
                    db, p.id, diff, tipo, usuario_id,
                    referencia_tipo="ajuste_masivo",
                    notas="Resync stock cache vs lotes",
                )
                detalle = ", ".join(f"lote{l}-{c}" for l, c in consumos)
                log.info(
                    "P#%-4d %-45s cache=%-10s lotes=%-10s diff=%+8.2f -> lotes: %s",
                    p.id, (p.nombre or "?")[:45], p.stock_actual, suma, diff, detalle,
                )
                corregidos += 1
            except Exception as e:
                log.warning("P#%s %s ERROR: %s", p.id, p.nombre, e)
                errores += 1

        print(f"\nResumen: {corregidos} corregidos, {sin_cambio} ya consistentes, {errores} errores")
    finally:
        db.close()


if __name__ == "__main__":
    main()