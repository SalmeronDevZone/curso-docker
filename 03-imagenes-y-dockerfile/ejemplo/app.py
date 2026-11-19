"""
App mínima para practicar con Dockerfile.
Devuelve un saludo configurable con la variable de entorno SALUDO.
"""
import os
import socket

from flask import Flask

app = Flask(__name__)


@app.get("/")
def inicio():
    saludo = os.environ.get("SALUDO", "Hola")
    version = os.environ.get("APP_VERSION", "desconocida")
    return f"{saludo} desde el contenedor {socket.gethostname()} (versión {version})\n"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
