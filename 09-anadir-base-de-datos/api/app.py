"""
API de NOTAS  (versión 2: guarda las notas en PostgreSQL)

Qué cambia respecto a la versión 1 (módulos 06-08):
  - Las notas ya NO viven en memoria, sino en una base de datos que corre en
    OTRO contenedor (el servicio "db").
  - La dirección de la base de datos llega por la variable DATABASE_URL.
    (Mismo truco que API_URL en la web: la configuración viene de FUERA.)
  - Al arrancar, la API espera a que la BD acepte conexiones y crea la tabla.
  - /health comprueba también que la BD responde.

Como la API ya no guarda estado propio, podemos tener VARIAS copias de ella
(docker compose up --scale api=3) y todas verán las mismas notas.
"""
import os
import signal
import socket
import sys
import time

import psycopg
from flask import Flask, jsonify, request
from psycopg.rows import dict_row

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("Falta la variable DATABASE_URL (ej: postgresql://usuario:clave@db:5432/notas)")

CONTENEDOR = socket.gethostname()
app = Flask(__name__)


def conectar():
    # Una conexión nueva por petición: sencillo y suficiente para aprender.
    # (En producción se usaría un "pool" de conexiones.)
    return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=3)


def preparar_bd(intentos=15, espera=2):
    """Espera a que PostgreSQL acepte conexiones y crea la tabla si no existe."""
    for intento in range(1, intentos + 1):
        try:
            with conectar() as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS notas (
                        id      SERIAL PRIMARY KEY,
                        texto   TEXT        NOT NULL,
                        creada  TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
            print("[api] Base de datos lista.", flush=True)
            return
        except psycopg.OperationalError as err:
            print(f"[api] BD no disponible todavía (intento {intento}/{intentos}): {err}", flush=True)
            time.sleep(espera)
    sys.exit("[api] No he podido conectar con la base de datos. ¿Está arrancado el servicio 'db'?")


def a_json(fila):
    return {
        "id": fila["id"],
        "texto": fila["texto"],
        "creada": fila["creada"].isoformat(timespec="seconds"),
    }


@app.get("/health")
def health():
    try:
        with conectar() as conn:
            conn.execute("SELECT 1")
        return jsonify(estado="ok", servicio="api", bd="ok", contenedor=CONTENEDOR)
    except psycopg.Error as err:
        return jsonify(estado="error", servicio="api", bd=str(err), contenedor=CONTENEDOR), 503


@app.get("/api/notas")
def listar_notas():
    with conectar() as conn:
        filas = conn.execute("SELECT id, texto, creada FROM notas ORDER BY id").fetchall()
    return jsonify(notas=[a_json(f) for f in filas], contenedor=CONTENEDOR)


@app.post("/api/notas")
def crear_nota():
    datos = request.get_json(silent=True) or {}
    texto = str(datos.get("texto", "")).strip()
    if not texto:
        return jsonify(error="El campo 'texto' es obligatorio"), 400

    with conectar() as conn:  # al salir del "with" se hace COMMIT automáticamente
        fila = conn.execute(
            # %s = parámetro: psycopg lo escapa (nunca concatenes texto en SQL)
            "INSERT INTO notas (texto) VALUES (%s) RETURNING id, texto, creada",
            (texto,),
        ).fetchone()
    print(f"[api] Nota #{fila['id']} guardada en la BD", flush=True)
    return jsonify(a_json(fila)), 201


# Se ejecuta al cargar el módulo: así funciona igual con "python app.py"
# que con un servidor de producción como gunicorn (módulo 11).
preparar_bd()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # ver módulo 10
    puerto = int(os.environ.get("PORT", "5000"))
    print(f"[api] Escuchando en el puerto {puerto} (contenedor {CONTENEDOR})", flush=True)
    app.run(host="0.0.0.0", port=puerto)
