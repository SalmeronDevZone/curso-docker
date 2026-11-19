"""
API de NOTAS  (versión 1: guarda las notas EN MEMORIA)

Endpoints:
  GET  /health      -> comprobar que la API está viva
  GET  /api/notas   -> listar notas
  POST /api/notas   -> crear una nota   (JSON: {"texto": "..."})

OJO: las notas viven en una lista de Python. Si el proceso se reinicia
(por ejemplo, al reiniciar el contenedor) SE PIERDEN. Lo arreglaremos en el
módulo 09 añadiendo una base de datos en OTRO contenedor.
"""
import os
import signal
import socket
import sys
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

NOTAS = []

# Dentro de Docker, el hostname es el ID corto del contenedor.
# Lo devolvemos en cada respuesta para que VEAS qué contenedor te contesta.
CONTENEDOR = socket.gethostname()


@app.get("/health")
def health():
    return jsonify(estado="ok", servicio="api", contenedor=CONTENEDOR)


@app.get("/api/notas")
def listar_notas():
    return jsonify(notas=NOTAS, contenedor=CONTENEDOR)


@app.post("/api/notas")
def crear_nota():
    datos = request.get_json(silent=True) or {}
    texto = str(datos.get("texto", "")).strip()
    if not texto:
        return jsonify(error="El campo 'texto' es obligatorio"), 400

    nota = {
        "id": len(NOTAS) + 1,
        "texto": texto,
        "creada": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    NOTAS.append(nota)
    print(f"[api] Nota creada: {nota}")
    return jsonify(nota), 201


def parar(signum, frame):
    # "docker stop" envía la señal SIGTERM al proceso principal (PID 1).
    # Un PID 1 que NO captura SIGTERM la ignora, y Docker acaba matándolo
    # con SIGKILL a los 10 segundos. Lo explicamos a fondo en el módulo 10.
    print("[api] SIGTERM recibido: cerrando la API.")
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, parar)
    puerto = int(os.environ.get("PORT", "5000"))
    # host="0.0.0.0" -> escuchar en TODAS las interfaces de red del contenedor.
    # Con "127.0.0.1" solo se podría llamar a la API desde DENTRO de su propio
    # contenedor: ni otros contenedores ni tu navegador llegarían a ella.
    print(f"[api] Escuchando en el puerto {puerto} (contenedor {CONTENEDOR})")
    app.run(host="0.0.0.0", port=puerto)
