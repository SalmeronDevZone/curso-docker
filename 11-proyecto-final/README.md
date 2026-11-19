# 11 · Proyecto final: la aplicación "de producción"

**Objetivo:** juntar todo lo aprendido. Partiendo del módulo 09, construirás tú
una versión de la aplicación de notas lista para un servidor real. Hay una
solución completa y probada en [solucion/](solucion/), pero **inténtalo antes
por tu cuenta**: es donde de verdad se aprende.

---

## 1. Lo que hay que construir

```text
                       ┌──────────────── red "frontend" ────────────────┐
  navegador ──:8080──▶ │ [ proxy: nginx ] ──/──────▶ [ web ] ──▶ [ api ] │
                       │        └─────────/api/──────────────────▶ [ api ] │
                       └─────────────────────────────────────────── │ ───┘
                       ┌──────────── red "backend" (internal) ───── │ ───┐
                       │                                          [ api ] ──▶ [ db ] ── volumen
                       └───────────────────────────────────────────────────┘

  [ adminer ]  ← opcional, solo si arrancas con el perfil "debug"
```

### Requisitos

**R1 — Proxy inverso (4º contenedor).** Un `nginx` es la **única** puerta de
entrada, en el puerto 8080 del host:
- `/` → servicio `web` (puerto 3000)
- `/api/...` → servicio `api` (puerto 5000)
- `/salud` → responde `ok` (para su propio healthcheck)
- Ningún otro servicio publica puertos.

**R2 — Redes separadas.**
- `frontend`: proxy, web y api.
- `backend`: api y db. Marcada como `internal` (sin salida a internet).
- La web **no** debe poder conectar con la base de datos.

**R3 — Imágenes de producción** (módulo 10) para `api` y `web`:
- usuario no-root, healthcheck, multi-stage en la API;
- la API servida con `gunicorn` y **2 workers** (ahora se puede: el estado está en la BD).

**R4 — Salud y orden de arranque.** Todos los servicios con healthcheck, y cada
uno espera a que sus dependencias estén **sanas**: `db` → `api` → `web` → `proxy`.

**R5 — Endurecimiento.**
- `web` y `api` con sistema de ficheros de solo lectura.
- Límites de memoria y CPU en todos los servicios.
- Rotación de logs en todos los servicios (sin repetir el bloque 4 veces).

**R6 — Datos.** Volumen para la BD y un **script de copia de seguridad** que
genere un `.sql.gz` con fecha en el nombre.

**R7 (opcional) — Herramienta de depuración.** Un `adminer` que **solo** arranque
cuando se pida explícitamente, accesible solo desde la propia máquina.

---

## 2. Cómo empezar

```bash
cd 11-proyecto-final
mkdir mi-solucion
cp -r ../09-anadir-base-de-datos/{api,web,compose.yaml,.env.example} mi-solucion/
cd mi-solucion
cp .env.example .env
```

Y ve requisito a requisito. Después de cada uno: `docker compose up -d --build`,
comprueba, y sigue. **No intentes hacerlo todo de golpe.**

---

## 3. Pistas (ábrelas solo si te atascas)

<details><summary>Pista R1 — configuración de nginx</summary>

La imagen `nginx:1.27-alpine` lee la configuración de
`/etc/nginx/conf.d/default.conf`. Crea tu fichero `nginx/default.conf` y
móntalo encima con un bind mount de solo lectura:

```yaml
    volumes:
      - ./nginx/default.conf:/etc/nginx/conf.d/default.conf:ro
```

Dentro, un bloque `server { listen 80; ... }` con un `location` por ruta y
`proxy_pass http://NOMBRE_SERVICIO:PUERTO;`.

</details>

<details><summary>Pista R2 — redes</summary>

```yaml
services:
  servicio:
    networks: [frontend, backend]

networks:
  frontend: {}
  backend:
    internal: true
```

En cuanto declaras `networks:` en un servicio, deja de estar en la red
`default`. Comprueba el aislamiento con:
`docker compose exec web wget -qO- -T 2 http://db:5432` → `bad address`.

</details>

<details><summary>Pista R3 — gunicorn con varios workers</summary>

`preparar_bd()` se ejecuta al importar `app.py`. Con 2 workers se importaría 2
veces **a la vez** y los dos `CREATE TABLE` podrían chocar. La opción
`--preload` de gunicorn importa la app **una sola vez** en el proceso maestro
antes de crear los workers.

</details>

<details><summary>Pista R4 — healthcheck de nginx</summary>

La imagen alpine de nginx trae `wget`:

```yaml
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1/salud"]
```

Y para depender de servicios sanos:

```yaml
    depends_on:
      web: { condition: service_healthy }
```

Si `web` tiene el `HEALTHCHECK` en su Dockerfile, Compose lo usa igualmente.

</details>

<details><summary>Pista R5 — no repetir el bloque de logs</summary>

Los campos que empiezan por `x-` los ignora Compose, y YAML permite anclas
(`&nombre`) y referencias (`*nombre`):

```yaml
x-logging: &logging
  driver: json-file
  options: { max-size: "10m", max-file: "3" }

services:
  web:
    logging: *logging
```

Y para solo lectura: `read_only: true`. Si algo necesita escribir en `/tmp`:
`tmpfs: [/tmp]`.

</details>

<details><summary>Pista R7 — perfiles</summary>

```yaml
  adminer:
    profiles: [debug]
    ports: ["127.0.0.1:8081:8080"]
```

Solo arranca con `docker compose --profile debug up -d`. Ojo: si solo está en la
red `backend` (que es `internal`) no podrás publicar su puerto.

</details>

---

## 4. Criterios de aceptación

Tu solución está terminada cuando **todas** estas comprobaciones pasan:

```bash
# Todo sano
docker compose ps                         # 4 servicios "(healthy)"

# Solo el proxy publica puertos
docker compose ps --format '{{.Service}} {{.Ports}}'   # solo proxy tiene 0.0.0.0:8080->80/tcp

# Funciona a través del proxy
curl -s -X POST -d 'texto=final' localhost:8080/notas -o /dev/null -w '%{http_code}\n'   # 302
curl -s localhost:8080/api/notas | jq                  # la nota, servida por la API vía nginx
curl -s localhost:8080/salud                           # ok

# Aislamiento de redes
docker compose exec web wget -qO- -T 2 http://db:5432     # bad address  ✅ (web no ve la BD)
docker compose exec db wget -qO- -T 3 http://example.com  # bad address  ✅ (BD sin internet)

# No-root y solo lectura
docker compose exec api whoami            # app
docker compose exec web whoami            # node
docker compose exec web touch /app/x      # Read-only file system

# Límites
docker stats --no-stream                  # columna LIMIT con tus límites

# Persistencia y backup
bash scripts/backup-db.sh                 # crea backups/notas-FECHA.sql.gz
docker compose down && docker compose up -d   # las notas siguen

# Perfil de depuración
docker compose --profile debug up -d      # aparece adminer en 127.0.0.1:8081
```

---

## 5. La solución explicada

Ficheros en [solucion/](solucion/):

```text
solucion/
├── compose.yaml          ← los 5 servicios, 2 redes, 1 volumen
├── .env.example
├── nginx/default.conf    ← reglas del proxy inverso
├── api/                  ← app.py del módulo 09 + Dockerfile de producción + gunicorn
├── web/                  ← server.js de siempre + Dockerfile con USER node y HEALTHCHECK
└── scripts/backup-db.sh  ← copia de seguridad con pg_dump
```

```bash
cd solucion
cp .env.example .env
docker compose up -d --build
docker compose ps
```

Detalles que merece la pena entender:

- **Orden de arranque en cadena.** Verás en la salida de `up` cómo cada servicio
  espera al anterior: `db Healthy` → `api Healthy` → `web Healthy` → `proxy Started`.
- **La API es el "puente".** Es el único servicio en las dos redes: habla con
  la BD por `backend` y recibe peticiones por `frontend`.
- **`internal: true`** quita la salida a internet de la red `backend`. Un
  atacante que comprometa la BD no puede "llamar a casa".
- **`read_only` + `tmpfs`.** La API y la web no pueden modificar su propio código.
  gunicorn usa `--worker-tmp-dir /dev/shm` (memoria) y además tiene `/tmp` en tmpfs.
- **`adminer` en dos redes** y publicado en `127.0.0.1`: necesita `backend` para
  ver la BD y `frontend` porque una red `internal` no puede publicar puertos.
- **nginx resuelve los nombres al arrancar.** Si recreas la API (`up -d --build`
  con cambios en la API), su IP puede cambiar; si el proxy da `502`, ejecuta
  `docker compose restart proxy`. (En configuraciones avanzadas se usa
  `resolver 127.0.0.11` con variables para resolver en cada petición.)

### Restaurar una copia

```bash
gunzip -c backups/notas-FECHA.sql.gz | docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" "$POSTGRES_DB"'
```

El script usa `pg_dump --clean --if-exists` (como en el módulo 09), así que la
copia se puede restaurar encima de una BD que ya tenga la tabla.

---

## 6. Retos extra (para seguir aprendiendo)

1. **HTTPS:** genera un certificado autofirmado con `openssl` y haz que nginx
   sirva en el 8443 con TLS.
2. **Redis como caché:** añade `redis` a la red `backend` y haz que la API cachee
   `GET /api/notas` 10 segundos.
3. **Escalar detrás de nginx:** `docker compose up -d --scale api=3`. ¿Reparte
   nginx la carga entre las tres? (Pista: no, resuelve una sola vez. Investiga
   `resolver 127.0.0.11 valid=10s;` y `set $upstream http://api:5000;`.)
4. **Publicar tus imágenes** en Docker Hub (módulo 03) y cambiar el
   `compose.yaml` para usar `image: TU_USUARIO/notas-api:2.0` en lugar de `build:`.
   Luego despliégalo en otra máquina solo con el `compose.yaml` y el `.env`.
5. **Integración continua:** crea un workflow de GitHub Actions que construya
   las imágenes en cada `git push`.
6. **Siguiente nivel:** pasa esta misma aplicación a Kubernetes (con
   `minikube` o `kind`). Verás que los conceptos (imágenes, servicios, redes,
   volúmenes, healthchecks → *probes*) son los mismos.

### Limpieza

```bash
docker compose --profile debug down -v     # ⚠️ -v borra la BD
rm -rf backups .env
```

---

➡️ Siguiente: [12 · Depuración y errores comunes](../12-depuracion-y-errores/README.md)
