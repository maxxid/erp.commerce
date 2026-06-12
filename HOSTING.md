ESPECIFICACIONES DEL PROYECTO PARA HOSTING
==========================================

Requisitos técnicos:
  - Python 3.11+
  - Servidor: Uvicorn (ASGI) + FastAPI
  - Puerto: 8000 (configurable por PORT)
  - Base de datos: SQLite (1 archivo, requiere disco con escritura)
  - RAM: ~100 MB mínimo, ~200 MB cómodo
  - CPU: Mínimo (solo API REST + scraping ocasional)
  - Sin dependencias externas (no Redis, no PostgreSQL)

Dependencias pip (requirements.txt):
  fastapi, uvicorn, sqlalchemy, pydantic,
  python-jose[cryptography], passlib[bcrypt],
  requests, beautifulsoup4, python-multipart

Restricción clave:
  SQLite necesita DISCO PERSISTENTE con LECTURA/ESCRITURA.
  Esto descarta Vercel, Netlify, AWS Lambda y cualquier serverless.


PLATAFORMAS GRATUITAS COMPATIBLES
==================================

A. Oracle Cloud Free Tier ⭐ (la mejor)
   - 4 cores ARM, 24 GB RAM, 200 GB disco
   - GRATIS DE POR VIDA, sin letra chica
   - Ubuntu VM → instalás Python y corrés uvicorn
   - Dominio: apuntás registro A a la IP pública
   - Contra: registro con tarjeta (no cobran, es verificación)

B. Fly.io
   - 3 VMs compartidas de 256 MB RAM cada una
   - 3 GB de disco persistente (volume)
   - No se duerme nunca
   - Deploy con: fly launch (autodetecta Dockerfile)
   - Dominio gratis: xxx.fly.dev

C. Koyeb
   - 512 MB RAM, 1 GB disco
   - No cold starts en free tier
   - Deploy desde GitHub o Docker
   - Dominio gratis: xxx.koyeb.app

D. Render
   - 512 MB RAM, disco incluido
   - Se duerme tras 15 min inactivo (despierta en ~30s)
   - Deploy desde GitHub
   - Dominio gratis: xxx.onrender.com

E. PythonAnywhere
   - 512 MB disco, siempre online (3 meses, luego renuevas)
   - Consola web, no Docker
   - Dominio: tunombre.pythonanywhere.com


RESUMEN: La mejor opción es Oracle Cloud (gratis de por vida,
la VM más potente) o Fly.io (más fácil de configurar, también gratis).