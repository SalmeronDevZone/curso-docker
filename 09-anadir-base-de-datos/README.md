# 09 · Meter otro contenedor: una base de datos

**Objetivo:** añadir un **tercer servicio** (PostgreSQL) a la aplicación, y de
paso aprender las piezas que necesita cualquier servicio con datos: volúmenes,
variables de entorno con secretos, *healthchecks* y orden de arranque real.

```text
módulo 08:   navegador ──▶ [ web ] ──▶ [ api ]  (notas en memoria: se pierden, no escala)

módulo 09:   navegador ──▶ [ web ] ──▶ [ api ] ──▶ [ db: PostgreSQL ]
                :8080                                     │
                                                    volumen datos-db
```

---

## 1. Por qué un tercer contenedor

En el módulo 08 vimos dos problemas de guardar las notas en la memoria de la API:

1. **Se pierden** cada vez que la API se reinicia o se actualiza.
2. **No se puede escalar**: cada réplica tiene sus propias notas.

La solución es sacar el **estado** a un servicio especializado, compartido por
todas las réplicas y con almacenamiento persistente: una base de datos.

> 🧠 ¿Por qué la base de datos en **su propio contenedor** y no dentro del de la
> API? Por todo lo que vimos en el módulo 06: se actualiza a otro ritmo (nunca
> reinicias la BD al desplegar la API), tiene otros recursos, otros backups,
> otra imagen (la oficial de PostgreSQL, mantenida por expertos). Y para eso no
> hace falta ni escribir un Dockerfile: usamos la imagen oficial tal cual.

---

## 2. Checklist: cómo añadir CUALQUIER servicio nuevo

Guarda esta lista: vale para PostgreSQL, Redis, RabbitMQ, Elasticsearch...

1. **Imagen**: ¿hay imagen oficial? Elige versión **fijada** (`postgres:17-alpine`).
2. **Documentación de la imagen** (Docker Hub): qué **variables** necesita, qué
   **puerto** usa, dónde guarda los **datos**.
3. **Datos**: volumen con nombre en la ruta de datos.
4. **Configuración y secretos**: variables de entorno desde un `.env` que no se
   sube a git.
5. **Red**: ¿quién necesita hablar con él? ¿Hace falta publicar puertos? (casi
   nunca para una BD).
6. **Salud**: un `healthcheck` para saber cuándo está realmente listo.
7. **Dependencias**: los servicios que lo usan deben esperar a que esté sano
   (`depends_on` con `condition: service_healthy`).
8. **Conectar la app**: la app recibe la dirección del servicio por variable de
   entorno (como `API_URL` en la web). Aquí: `DATABASE_URL`.

---

## 3. Qué cambia en el código de la API

Compara [api/app.py](api/app.py) con la versión del módulo 08. Los cambios:

```python
# ANTES: NOTAS = []   (lista en memoria)

# AHORA: la dirección de la BD viene de FUERA, por variable de entorno
DATABASE_URL = os.environ.get("DATABASE_URL")   # postgresql://usuario:clave@db:5432/notas

def preparar_bd():
    # Reintenta hasta que PostgreSQL acepte conexiones y crea la tabla si no existe
    ...

@app.get("/api/notas")
def listar_notas():
    with conectar() as conn:
        filas = conn.execute("SELECT id, texto, creada FROM notas ORDER BY id").fetchall()
```

Y en [api/requirements.txt](api/requirements.txt) se añade el driver `psycopg`.

Fíjate en la dirección: **`@db:5432`**. `db` es el nombre del servicio en
`compose.yaml`: el mismo truco de DNS que usa la web para encontrar a `api`.

**La web no cambia nada.** Ni una línea. Sigue hablando con la API igual que
antes; no sabe ni le importa dónde guarda la API los datos. Eso es un buen
diseño por capas.

---

## 4. El nuevo `compose.yaml`, por partes

Abre [compose.yaml](compose.yaml). Lo nuevo es el servicio `db` y la sección
`volumes`.

### 4.1 El servicio `db`

```yaml
  db:
    image: postgres:17-alpine         # imagen oficial, sin Dockerfile propio
    environment:
      POSTGRES_USER: ${POSTGRES_USER:?Falta POSTGRES_USER...}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?...}
      POSTGRES_DB: ${POSTGRES_DB:?...}
    volumes:
      - datos-db:/var/lib/postgresql/data
```

- La imagen de `postgres` lee esas variables **la primera vez** que arranca con
  el volumen vacío, y crea el usuario y la base de datos.
- `${POSTGRES_USER}` → Compose sustituye el valor desde el fichero **`.env`**.
- `${VAR:?mensaje}` → si la variable no existe, Compose **se niega a arrancar**
  y muestra el mensaje. Mejor un error claro que una BD sin contraseña.
- **Sin `ports`**: la base de datos no es accesible desde fuera, solo desde la
  red interna. Menos superficie de ataque.

### 4.2 El volumen

```yaml
volumes:
  datos-db:
```

Declara un volumen con nombre (Docker lo crea como `notas-09_datos-db`).
`docker compose down` **no** lo borra; `docker compose down -v` **sí**.

### 4.3 Healthcheck: ¿está listo de verdad?

```yaml
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s       # cada cuánto se comprueba
      timeout: 3s        # cuánto se espera la respuesta
      retries: 10        # fallos seguidos para marcarlo "unhealthy"
      start_period: 10s  # margen inicial en el que los fallos no cuentan
```

Docker ejecuta `pg_isready` **dentro** del contenedor periódicamente. Según el
resultado, el contenedor está `starting`, `healthy` o `unhealthy` (lo ves en
`docker compose ps`).

> 💡 `$$` = un `$` literal. Con `$$` le decimos a Compose "no sustituyas esto
> tú; que lo expanda la shell del contenedor", que tiene esas variables.

### 4.4 depends_on con condición

```yaml
  api:
    depends_on:
      db:
        condition: service_healthy
```

Ahora la API **no se arranca hasta que el healthcheck de la BD diga `healthy`**.
Es la solución al problema que vimos en el módulo 08: `depends_on` a secas
solo espera a que el contenedor exista, no a que esté listo.

| Condición | Espera a que... |
|-----------|-----------------|
| (lista simple) / `service_started` | el contenedor se haya arrancado |
| `service_healthy` | su healthcheck diga `healthy` |
| `service_completed_successfully` | haya **terminado** con código 0 (tareas de inicialización, migraciones) |

> 🧠 **Defensa en profundidad:** aun así, la API tiene su propio bucle de
> reintentos (`preparar_bd`). En producción la BD puede reiniciarse mientras la
> API corre; la app debe tolerarlo, no confiar solo en el orden de arranque.

### 4.5 La API recibe la dirección de la BD

```yaml
    environment:
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
```

> ⚠️ Si tu contraseña tiene caracteres especiales (`@`, `:`, `/`, `#`...),
> rompen el formato de la URL. Para aprender, usa letras, números y `_`.

---

## 5. Secretos: el fichero `.env`

```bash
cd 09-anadir-base-de-datos
cp .env.example .env
nano .env               # cambia la contraseña
```

- [.env.example](.env.example) → **plantilla** sin secretos reales. **Sí** se sube a git.
- `.env` → tus valores reales. **No** se sube a git (está en `.gitignore`).
- Compose lee automáticamente el `.env` de la carpeta donde ejecutas el comando.

Prueba a arrancar **sin** `.env` para ver la protección:

```bash
mv .env .env.bak
docker compose config
# required variable POSTGRES_PASSWORD is missing a value: Falta POSTGRES_PASSWORD. Copia .env.example a .env
mv .env.bak .env
```

> 🧠 Las variables de entorno son la forma más sencilla de pasar secretos, y
> suficiente para aprender. Ten en cuenta que cualquiera que pueda hacer
> `docker inspect` las ve. En producción se usan *Docker secrets*, gestores de
> secretos (Vault, los de AWS/Azure...) o ficheros montados de solo lectura.

---

## 6. Arrancar

```bash
docker compose up -d --build
```

```text
 ✔ Network notas-09_default    Created
 ✔ Volume  notas-09_datos-db   Created
 ✔ Container notas-09-db-1     Healthy     ← espera a que esté sano...
 ✔ Container notas-09-api-1    Started     ← ...y solo entonces arranca la API
 ✔ Container notas-09-web-1    Started
```

```bash
docker compose ps                 # db: Up (healthy)
docker compose logs api           # [api] Base de datos lista.
```

Abre `http://localhost:8080` y crea notas.

---

## 7. 🧪 Experimentos

### Los datos sobreviven a todo (menos a `-v`)

```bash
docker compose restart api         # reiniciar la API      -> notas intactas
docker compose down                # borrar TODOS los contenedores y la red
docker compose up -d               # volver a crearlos
# -> las notas siguen ahí: estaban en el volumen, no en los contenedores
docker volume ls | grep notas-09
```

### Ahora SÍ se puede escalar

```bash
docker compose up -d --scale api=3
for i in 1 2 3 4 5 6; do docker compose exec web wget -qO- http://api:5000/api/notas; echo; done
```

Cambia el `contenedor` que responde, pero **las notas son siempre las mismas**:
las tres réplicas leen de la misma base de datos. La API se ha vuelto
*stateless*, y por eso se puede escalar.

```bash
docker compose up -d --scale api=1
```

### Entrar en la base de datos

```bash
docker compose exec db psql -U notas -d notas
```

```sql
-- (dentro de psql)
\dt                                   -- tablas
SELECT * FROM notas;
INSERT INTO notas (texto) VALUES ('Escrita directamente en SQL');
\q
```

Recarga la web: la nota insertada a mano aparece. (Si cambiaste el usuario en
`.env`, usa ese en `-U` y `-d`.)

### ¿Qué pasa si la BD se cae?

```bash
docker compose stop db
curl -s localhost:8080 | grep error      # la web muestra el error de la API (502)
docker compose exec web wget -qO- http://api:5000/health   # la API responde 503: bd con error
docker compose start db
sleep 5; curl -s localhost:8080 | grep -c '<li>'   # vuelve a funcionar solo
```

La API no se ha caído: sigue viva y se recupera sola cuando vuelve la BD
(abre una conexión nueva en cada petición).

### Copia de seguridad y restauración

```bash
# Backup con pg_dump, la herramienta de PostgreSQL.
#   -T                    -> sin terminal (necesario para redirigir la salida a un fichero)
#   --clean --if-exists   -> el backup incluye "DROP TABLE IF EXISTS" antes de crear,
#                            así se puede restaurar encima de una BD que ya tenga la tabla
docker compose exec -T db pg_dump --clean --if-exists -U notas notas > backup.sql
less backup.sql                            # es SQL normal y legible (sal con q)

# Desastre: borramos TODO, incluido el volumen
docker compose down -v
docker compose up -d                       # BD vacía (ve a la web: no hay notas)

# Restaurar
docker compose exec -T db psql -U notas -d notas < backup.sql
# Recarga la web: las notas han vuelto
```

### El error clásico: "cambié la contraseña y no funciona"

1. Con todo arrancado, cambia `POSTGRES_PASSWORD` en `.env`.
2. `docker compose up -d` → la API no puede conectar: `password authentication failed`.

¿Por qué? Las variables `POSTGRES_*` **solo se usan la primera vez**, para
inicializar un volumen vacío. El volumen ya existe con la contraseña antigua.
Soluciones: volver a poner la contraseña antigua, cambiarla con SQL
(`ALTER USER notas PASSWORD '...'`), o, si no te importan los datos,
`docker compose down -v` y empezar de cero.

---

## 8. ✍️ Ejercicios

**Ejercicio 1 — Un cuarto contenedor: Adminer.** Añade un servicio con la
imagen `adminer:4.8.1` (una interfaz web para bases de datos) publicado en el
puerto 8081. Entra en `http://localhost:8081` y conéctate a la BD.

<details><summary>Ver solución</summary>

```yaml
  adminer:
    image: adminer:4.8.1
    ports:
      - "8081:8080"
    environment:
      ADMINER_DEFAULT_SERVER: db
    depends_on:
      - db
```

```bash
docker compose up -d
```

En el formulario: Sistema `PostgreSQL`, Servidor `db`, y el usuario, contraseña
y base de datos de tu `.env`. Fíjate: Adminer usa el nombre `db` porque está
en la misma red de Compose. Has metido un 4º contenedor en 6 líneas.

</details>

**Ejercicio 2.** Quieres conectarte a PostgreSQL con un programa instalado en tu
Ubuntu (por ejemplo `psql` o DBeaver), pero sin exponer la BD a toda la red.
¿Qué añades al servicio `db`?

<details><summary>Ver solución</summary>

```yaml
    ports:
      - "127.0.0.1:5432:5432"
```

Solo escucha en la interfaz local de tu Ubuntu. Conecta a `localhost:5432`.

</details>

**Ejercicio 3.** Añade un servicio `redis` (imagen `redis:7-alpine`) con un
volumen `datos-redis` en `/data` y un healthcheck que use `redis-cli ping`.
Haz que la API dependa de él estando sano (aunque la API no lo use todavía).

<details><summary>Ver solución</summary>

```yaml
  redis:
    image: redis:7-alpine
    restart: unless-stopped
    volumes:
      - datos-redis:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 5

  api:
    # ...
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy

volumes:
  datos-db:
  datos-redis:
```

</details>

### Limpieza del módulo

```bash
docker compose down        # conserva los datos
docker compose down -v     # ⚠️ borra también el volumen con las notas
rm -f backup.sql
```

---

➡️ Siguiente: [10 · Buenas prácticas](../10-buenas-practicas/README.md)
