# Taste
- En el bot de Telegram, los mensajes destinados a compartirse con el cajero deben ser detallados y autocontenidos (producto, código, precio original/oferta, vigencia, lote, margen) para poder reenviarlos sin explicación adicional. No enviar una segunda versión con formato WhatsApp para copiar/pegar; mostrar solo la versión Telegram. Confidence: 0.9
- Comunicarse en español en las interacciones con el usuario. Confidence: 0.9
- Cuando falte contexto, inspeccionar los archivos relevantes antes de actuar en lugar de asumir. Confidence: 0.85
- Tratar los archivos base/fundamentales (p. ej. CONTEXTO.md) como de alto riesgo: verificar minuciosamente antes de finalizar cambios para evitar errores. Confidence: 0.8
- En los listados del bot de Telegram, preferir salidas compactas: colocar info secundaria (como la marca) en la misma línea que el nombre, evitando líneas adicionales. Confidence: 0.85
- En el /help del bot de Telegram, preferir segmentar/agrupar los comandos por categoría (con encabezados), en lugar de una lista plana mezclada. Confidence: 0.75
- Las acciones destructivas/administrativas (p. ej. anular ventas) deben restringirse al rol dueño/admin, no a los cajeros. Confidence: 0.8
- Las acciones destructivas requieren confirmación inline antes de ejecutarse. Confidence: 0.75
- Prefiere implementar todas las funcionalidades solicitadas en una sola fase/pass en lugar de despliegues incrementales. Confidence: 0.7
- Valora y acepta sugerencias proactivas de nuevas funcionalidades y mejoras. Confidence: 0.75
- Prefiere alertas/notificaciones proactivas solo para eventos relevantes (p. ej. stock agotado en el día, vencimientos próximos), evitando exceso de alertas y con toggle para desactivarlas. Confidence: 0.7
- Prefiere que las funcionalidades y alertas sean configurables mediante toggles en Ajustes, desactivadas por defecto si pueden generar ruido. Confidence: 0.75
- En el reporte de vencimientos del bot, prefiere agrupar por urgencia en tres tramos de 7 días: urgentes (≤7 días), 8-14 días y 15-21 días. Confidence: 0.75
- En el bot de Telegram, cuando se crean ofertas o se consultan reportes comerciales, prefiere mostrar precio de costo junto al precio de venta (y cantidad) como referencia para decidir descuentos/acciones. Confidence: 0.8
- Prefiere crear ofertas/promociones desde el reporte de vencimientos del bot con flujo ágil y botones: listar vencimientos y ofrecer botón "Crear oferta" (junto con "Cerrar"); al elegirlo, mostrar listado de productos con lotes por vencer (días y cantidad), elegir producto, luego elegir tipo de oferta (% o importe fijo) y cantidad de unidades con default la del lote más próximo a vencer; mantener la misma secuencia al portarlo a la web. Confidence: 0.9
- El stock se gestiona por lotes (vencimiento); las funcionalidades de stock y ofertas deben considerar lotes y vencimiento. Confidence: 0.85
- Primero terminar/completar bien una funcionalidad en Telegram antes de portarla a la versión web. Confidence: 0.9

antes de portarla a la versión web. Confidence: 0.8
- En mensajes del bot de Telegram con parseo HTML, evitar placeholders entre ángulos (<...>) porque Telegram los interpreta como tags; usar paréntesis o texto plano. Confidence: 0.7
