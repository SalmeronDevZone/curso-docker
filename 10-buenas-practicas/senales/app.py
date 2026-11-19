"""
Programa mínimo para entender las SEÑALES y el PID 1 en Docker.

No hace nada útil: imprime su PID y espera para siempre. Lo interesante es
cuánto tarda en pararse con "docker stop" según cómo lo arranques.

Si la variable MANEJAR_SIGTERM=1, instala un "manejador" de SIGTERM.
"""
import os
import signal
import sys
import time


def al_recibir_sigterm(signum, frame):
    print("SIGTERM recibido -> cierro limpio (guardaría datos, cerraría conexiones...)", flush=True)
    sys.exit(0)


if os.environ.get("MANEJAR_SIGTERM") == "1":
    signal.signal(signal.SIGTERM, al_recibir_sigterm)
    print("Manejador de SIGTERM: INSTALADO", flush=True)
else:
    print("Manejador de SIGTERM: NO instalado", flush=True)

print(f"Soy el proceso con PID {os.getpid()}. Esperando... (prueba: time docker stop <nombre>)", flush=True)

while True:
    time.sleep(1)
