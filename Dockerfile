FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# curl y openssl los usa AFIP por subprocess (WSAA/WSFE y CSR); sin ellos la
# facturación electrónica falla arriba en la nube aunque ande en la PC.
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl openssl ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN useradd -r -u 10001 erp \
    && mkdir -p /data/backups \
    && chown -R erp:erp /app /data

COPY --chown=erp:erp . .

USER erp

ENV DATABASE_URL=sqlite:////data/erp_comercio.db \
    BACKUP_DIR=/data/backups

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=25s --retries=3 \
    CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
