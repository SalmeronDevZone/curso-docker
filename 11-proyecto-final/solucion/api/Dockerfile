# syntax=docker/dockerfile:1
# API de notas v2 (PostgreSQL) con Dockerfile de producción (ver módulo 10).

# ---------- Etapa 1: dependencias ----------
FROM python:3.12-slim AS dependencias
ENV PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
COPY requirements.txt .
RUN pip install -r requirements.txt

# ---------- Etapa 2: imagen final ----------
FROM python:3.12-slim
LABEL org.opencontainers.image.title="notas-api" \
      org.opencontainers.image.version="2.0"

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/venv/bin:$PATH"

RUN useradd --create-home --uid 10001 app
COPY --from=dependencias /venv /venv
WORKDIR /app
COPY --chown=app:app app.py .
USER app

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:5000/health', timeout=2).status == 200 else 1)"]

# Ahora el estado está en la BD -> podemos usar VARIOS procesos (workers).
# --preload: carga app.py UNA vez en el proceso maestro (así preparar_bd()
#            no se ejecuta a la vez en cada worker).
# --worker-tmp-dir /dev/shm: gunicorn necesita un directorio escribible y el
#            contenedor es de solo lectura (read_only en compose.yaml).
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--threads", "2", "--preload", "--worker-tmp-dir", "/dev/shm", "--access-logfile", "-", "app:app"]
