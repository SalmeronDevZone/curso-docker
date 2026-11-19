# syntax=docker/dockerfile:1
# =============================================================================
#  La MISMA API del módulo 07, pero con un Dockerfile "de producción".
#  Compara este fichero con 07-separar-en-dos-contenedores/api/Dockerfile.
# =============================================================================

# ---------- Etapa 1: instalar dependencias en un entorno virtual ----------
# Versión FIJADA de la imagen base (nunca "latest" en producción)
FROM python:3.12-slim AS dependencias

ENV PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install -r requirements.txt


# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim

# Metadatos estándar (los ves con: docker inspect notas-api:prod)
LABEL org.opencontainers.image.title="notas-api" \
      org.opencontainers.image.description="API de notas del curso de Docker" \
      org.opencontainers.image.version="1.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

# Usuario SIN privilegios. Si alguien explota un fallo de la app, no será root.
RUN useradd --create-home --uid 10001 app

# Solo copiamos el entorno virtual ya construido (sin pip, cachés, etc.)
COPY --from=dependencias /venv /venv

WORKDIR /app
COPY --chown=app:app app.py .

USER app

EXPOSE 5000

# Docker comprobará la salud de la app cada 10 s.
# (python:slim no trae curl/wget, así que usamos el propio Python)
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status == 200 else 1)"]

# gunicorn = servidor de producción. Gestiona bien SIGTERM (cierre ordenado).
# --workers 1: las notas están EN MEMORIA; con 2+ procesos cada uno tendría su
#              propia lista de notas (¡otra razón para usar una base de datos!).
# --threads 4: atiende varias peticiones a la vez dentro de ese único proceso.
# --access-logfile - : logs de acceso a stdout -> visibles con "docker logs"
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "1", "--threads", "4", "--access-logfile", "-", "app:app"]
