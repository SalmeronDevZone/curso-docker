# Forma EXEC (JSON con corchetes): Docker ejecuta python DIRECTAMENTE.
# -> python es el PID 1 y recibe las señales que manda Docker.
FROM python:3.12-slim
WORKDIR /app
COPY app.py .
CMD ["python", "-u", "app.py"]
