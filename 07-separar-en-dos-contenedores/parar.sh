#!/usr/bin/env bash
# Para y borra los contenedores y la red del módulo 07.
# (Las imágenes NO se borran; para eso: docker rmi notas-api:1.0 notas-web:1.0)
cd "$(dirname "$0")"

docker rm -f web api 2>/dev/null || true
docker network rm notas-red 2>/dev/null || true
echo "Contenedores 'web' y 'api' y red 'notas-red' eliminados."
