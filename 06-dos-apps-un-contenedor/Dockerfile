# =============================================================================
#  ⚠️  ANTI-PATRÓN DIDÁCTICO: DOS aplicaciones (Python + Node) en UNA imagen.
#      Funciona, pero lo hacemos para ver sus problemas y luego arreglarlo
#      en el módulo 07 separándolas en dos contenedores.
# =============================================================================
FROM python:3.12-slim

# Como la imagen base es de Python, para la web tenemos que instalar Node "a mano".
# Primer síntoma: la imagen mezcla dos mundos y engorda.
# (procps solo está para que puedas usar "ps" dentro y ver los 2 procesos)
RUN apt-get update \
    && apt-get install -y --no-install-recommends nodejs npm procps \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NODE_ENV=production

WORKDIR /app

# ---------- App 1: API (Python) ----------
COPY api/requirements.txt api/
RUN pip install --no-cache-dir -r api/requirements.txt
COPY api/ api/

# ---------- App 2: WEB (Node) ----------
COPY web/package*.json web/
RUN cd web && npm ci --omit=dev
COPY web/ web/

# ---------- El "arrancador" de los dos procesos ----------
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Como están en el MISMO contenedor, comparten la red: la web llega a la API
# por "localhost". (Cuando las separemos, esto cambiará a http://api:5000)
ENV API_URL=http://localhost:5000

EXPOSE 3000 5000

# El PID 1 ya no es nuestra app, sino un script de bash que hace de "niñera".
CMD ["/start.sh"]
