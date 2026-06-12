@echo off
cd /d "C:\Users\Paula\Documents\erp-comercio"
echo Iniciando ERP Comercio...
echo Base de datos: erp_comercio.db (NO se borra - datos persistentes)
echo Frontend: http://localhost:8000/app
echo API Docs: http://localhost:8000/docs
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
