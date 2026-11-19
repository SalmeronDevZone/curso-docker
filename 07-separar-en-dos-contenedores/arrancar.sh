#!/usr/bin/env bash
# Arranca las dos aplicaciones en DOS contenedores, a mano (sin Docker Compose).
# Úsalo como referencia: lo ideal es que escribas tú los comandos uno a uno
# siguiendo el README para entender qué hace cada uno.
set -euo pipefail
cd "$(dirname "$0")"

echo "1) Creando la red 'notas-red' (si no existe)..."
docker network create notas-red 2>/dev/null || echo "   (ya existía)"

echo "2) Construyendo las dos imágenes..."
docker build -t notas-api:1.0 ./api
docker build -t notas-web:1.0 ./web

echo "3) Arrancando la API (sin publicar puertos: solo accesible dentro de la red)..."
docker run -d --name api --network notas-red notas-api:1.0

echo "4) Arrancando la WEB (publicada en el puerto 8080 de tu máquina)..."
docker run -d --name web --network notas-red \
  -p 8080:3000 \
  -e API_URL=http://api:5000 \
  notas-web:1.0

echo
docker ps --filter name=api --filter name=web
echo
echo "Listo. Abre http://localhost:8080  (o: curl http://localhost:8080)"
