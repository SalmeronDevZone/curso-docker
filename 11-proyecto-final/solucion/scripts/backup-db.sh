#!/usr/bin/env bash
# Copia de seguridad de la base de datos a un fichero .sql.gz en ./backups
#
# Uso (desde la carpeta "solucion"):   bash scripts/backup-db.sh
# Restaurar una copia:
#   gunzip -c backups/FICHERO.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
set -euo pipefail
cd "$(dirname "$0")/.."

mkdir -p backups
FICHERO="backups/notas-$(date +%Y%m%d-%H%M%S).sql.gz"

# -T: sin terminal interactiva (necesario al redirigir la salida a un fichero)
# Las comillas simples hacen que $POSTGRES_USER se expanda DENTRO del contenedor
# --clean --if-exists: la copia borra y recrea las tablas al restaurarla
docker compose exec -T db sh -c 'pg_dump --clean --if-exists -U "$POSTGRES_USER" "$POSTGRES_DB"' | gzip > "$FICHERO"

echo "Copia guardada en $FICHERO ($(du -h "$FICHERO" | cut -f1))"
