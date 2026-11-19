# Imagen de la API (Python). Solo contiene lo que la API necesita: Python + Flask.
FROM python:3.12-slim

# PYTHONUNBUFFERED=1        -> los print() salen al momento en "docker logs"
#                              (sin esto Python los guarda en un búfer y "no ves nada")
# PYTHONDONTWRITEBYTECODE=1 -> no generar ficheros .pyc dentro de la imagen
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /app

# 1º las dependencias (cambian poco) -> esta capa se reutiliza de la caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 2º el código (cambia mucho) -> solo se rehace desde aquí hacia abajo
COPY . .

# Documenta el puerto en el que escucha la app (NO lo publica: eso lo hace -p)
EXPOSE 5000

# Forma "exec" (con corchetes): python será el PID 1 y recibirá las señales
CMD ["python", "app.py"]
