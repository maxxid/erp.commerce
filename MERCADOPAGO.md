# MercadoPago QR - Integración

## Estado Actual (Jul 2026)

**Funcionando:**
- Creación de orden QR dinámico ✅
- Webhook recibe notificaciones ✅
- Confirmación de venta vía webhook ✅
- Frontend polling para detectar pago ✅

**Pendiente:**
- Modo híbrido (QR fijo + dinámico)
- Validación de firma webhook (NO disponible para QR Code según docs)

---

## Credenciales Sandbox Argentina

```
Access Token:  APP_USR-5955167151715353-070316-d60a8b9ca001869914a4eabac88aff66-3517052704
App ID:         5955167151715353
User ID:        3517052704
```

**Test Buyer:**
```
Usuario: TESTUSER504932320538588265
Clave:   qatest7
```

---

## Configuración en DB

```sql
mercadopago_enabled=true
mercadopago_access_token=APP_USR-...  (sandbox = APP_USR-, prod = APP_PROD-)
mercadopago_user_id=3517052704
mercadopago_store_id=84383614
mercadopago_external_store_id=SUC0001
mercadopago_external_pos_id=CAJA001
mercadopago_pos_id_qr= (se completa al crear caja)
mercadopago_mode=sandbox
mercadopago_qr_fijo_modo=dinamico (o hibrido)
mercadopago_webhook_secret= (opcional para QR Code)
```

---

## IMPORTANTE: Webhooks para QR Code

**Según documentación oficial de MercadoPago:**

> "QR Code notifications cannot be verified using the secret signature. Therefore, you should proceed directly to the Simulate receiving notifications step."

**Fuentes:**
- `https://www.mercadopago.com.ar/developers/es/docs/qr-code/notifications`
- `https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks`

**Esto significa:**
- NO se puede validar la firma del webhook para QR Code
- El webhook llega sin header `X-Signature` o con firma no verificable
- Hay que procesar el webhook directamente usando `external_reference`

---

## Endpoints de la API

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/pagos/mercadopago/crear-orden` | Crea orden QR |
| GET | `/api/pagos/mercadopago/orden/{order_id}` | Consulta estado de orden |
| POST | `/api/pagos/mercadopago/crear-sucursal` | Crea sucursal en MP |
| POST | `/api/pagos/mercadopago/crear-caja` | Crea caja/POS en MP |
| POST | `/api/pagos/mercadopago/webhook` | Recibe webhooks de MP |

---

## Flujo de un pago QR

1. Cajero crea venta en POS
2. Se llama `/crear-orden` con `external_reference=venta_{id}`
3. MP devuelve `order_id` y `qr_data`
4. Se muestra QR en pantalla
5. Cliente paga con app de MP
6. MP envía webhook a `/webhook` con:
   - `action: "order.processed"`
   - `data.external_reference: "venta_{id}"`
   - `data.id: order_id`
7. Backend confirma la venta automáticamente

---

## Webhook - Datos que llegan

**URL Query Params:**
- `data.id` - ID de la orden
- `data.external_reference` - `venta_{id}`
- `type` - `order` o `payment`

**Body JSON:**
```json
{
  "action": "order.processed",
  "type": "order",
  "data": {
    "external_reference": "venta_101",
    "id": "ORD01K..."
  }
}
```

---

## Troubleshooting

### Error 404 al consultar orden
- El `order_id` puede ser de testing y no existir en MP
- **Solución**: Usar `external_reference` para confirmar directamente

### Webhook llega pero no procesa
- Verificar que `external_reference` empiece con `venta_`
- Ver logs: `sudo journalctl -u erp-comercio -n 100 | grep -i webhook`

### Webhook con 404 al consultar orden
- Si el log muestra `MP API error: 404 - resource not found` cuando llegas webhooks, puede ser porque:
  - La simulación de MP no incluye `external_reference` válido
  - El `order_id` de test no existe en la API de MP
- **Fix aplicado**: Si el webhook no tiene `external_reference` válido, se ignora silenciosamente
- Esto es normal en simulaciones - los webhooks reales con pago incluyen el `external_reference`

### Polling da 400
- El order_id puede haber expirado (15 min)
- Ver logs de error: `sudo journalctl -u erp-comercio -n 50 | grep -i error`

---

## Comandos de Debug

```bash
# Ver webhooks recibidos
sudo journalctl -u erp-comercio -n 100 | grep -i webhook

# Ver errores
sudo journalctl -u erp-comercio -n 50 | grep -i error

# Reiniciar backend
sudo systemctl restart erp-comercio

# Ver config MP en DB
sudo sqlite3 /data/erp/erp_comercio.db "SELECT * FROM configuraciones WHERE clave LIKE 'mercadopago%'"

# Test webhook manualmente
curl -X POST https://erp.imprenta.store/api/pagos/mercadopago/webhook \
  -H "Content-Type: application/json" \
  -d '{"action":"order.processed","data":{"external_reference":"venta_101","id":"ORDTEST"}}'
```

---

## Deploy

```bash
cd /opt/erp-comercio
sudo git pull
sudo systemctl restart erp-comercio
```

**Build frontend (desde Windows local):**
```bash
cd frontend
node scripts/prebuild.cjs
node ./node_modules/vite/bin/vite.js build
git add -A && git commit -m "mensaje" && git push
```

---

## Links Importantes

- [Docs QR Code](https://www.mercadopago.com.ar/developers/es/docs/qr-code/overview)
- [Docs Webhooks](https://www.mercadopago.com.ar/developers/es/docs/your-integrations/notifications/webhooks)
- [Portal Developers](https://www.mercadopago.com.ar/developers/panel/app)
- [Probar webhooks](https://www.mercadopago.com.ar/developers/panel/app) > Webhooks > Simulate notification
