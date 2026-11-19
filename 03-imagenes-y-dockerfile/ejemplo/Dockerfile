# ---------------------------------------------------------------------------
# Cada instrucción crea una CAPA de la imagen. Lee los comentarios en orden.
# ---------------------------------------------------------------------------

# FROM: imagen de partida. Siempre la primera instrucción.
# "slim" = variante reducida de Debian con Python ya instalado.
FROM python:3.12-slim

# ARG: variable que SOLO existe mientras se construye la imagen.
#      Se puede cambiar con: docker build --build-arg VERSION=2.0 ...
ARG VERSION=1.0

# ENV: variable de entorno que existirá DENTRO del contenedor al ejecutarse.
#      Se puede sobrescribir con: docker run -e SALUDO=Buenas ...
ENV SALUDO="Hola" \
    APP_VERSION=${VERSION} \
    PYTHONUNBUFFERED=1

# LABEL: metadatos (autor, versión...). No afectan al funcionamiento.
LABEL descripcion="Ejemplo del módulo 03 del curso de Docker"

# WORKDIR: carpeta de trabajo. La crea si no existe y hace "cd" a ella.
#          Las instrucciones siguientes (COPY, RUN, CMD) parten de aquí.
WORKDIR /app

# COPY: copia ficheros de TU máquina (el "contexto") a la imagen.
#       Primero SOLO requirements.txt -> ver "caché de capas" en el README.
COPY requirements.txt .

# RUN: ejecuta un comando DURANTE LA CONSTRUCCIÓN y guarda el resultado
#      como una capa nueva. Aquí instalamos las dependencias.
RUN pip install --no-cache-dir -r requirements.txt

# Ahora sí, el resto del código.
COPY . .

# EXPOSE: DOCUMENTA el puerto en el que escucha la app. No publica nada
#         (para eso está "docker run -p").
EXPOSE 5000

# CMD: comando por defecto al ARRANCAR un contenedor (no al construir).
#      Forma exec (JSON) recomendada. Se puede sustituir en "docker run".
CMD ["python", "app.py"]
