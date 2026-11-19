#!/bin/bash
# =============================================================================
# Arranca DOS procesos dentro del MISMO contenedor.
#
# Un contenedor vive mientras vive su proceso principal (PID 1). Aquí el PID 1
# es ESTE script, así que le toca hacer el trabajo sucio que Docker haría por
# nosotros si hubiera un proceso por contenedor:
#   - arrancar los dos procesos en segundo plano
#   - reenviarles las señales (docker stop -> SIGTERM)
#   - decidir qué hacer si uno de los dos muere
# =============================================================================

echo "[start.sh] Arrancando la API (Python) en segundo plano..."
python /app/api/app.py &
API_PID=$!

echo "[start.sh] Arrancando la WEB (Node) en segundo plano..."
node /app/web/server.js &
WEB_PID=$!

echo "[start.sh] API con PID $API_PID, WEB con PID $WEB_PID. Yo soy el PID $$."

# Cuando Docker nos pida parar (SIGTERM), se lo pasamos a los dos hijos.
# Sin esto, "docker stop" tardaría 10 s y acabaría con un SIGKILL a lo bruto.
parar() {
  echo "[start.sh] Señal recibida: parando la API y la WEB..."
  kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null
  wait
  exit 0
}
trap parar TERM INT

# Esperamos a que termine CUALQUIERA de los dos procesos.
wait -n
CODIGO=$?

# Si llegamos aquí, uno de los dos ha muerto. ¿Qué hacemos con el otro?
# Opción elegida: matar también al otro y salir, para que el contenedor se pare
# y Docker (con --restart) lo vuelva a arrancar ENTERO. Fíjate en el problema:
# si se cae la API, también se reinicia la WEB aunque estuviera perfecta.
echo "[start.sh] Uno de los procesos ha terminado (código $CODIGO). Paro el otro y salgo."
kill -TERM "$API_PID" "$WEB_PID" 2>/dev/null
wait
exit "$CODIGO"
