# 08 · Docker Compose: toda la aplicación en un fichero

**Objetivo:** describir la aplicación de dos contenedores del módulo 07 en un
fichero `compose.yaml` y gestionarla entera con un solo comando. Además,
escalar la API y descubrir un problema que nos llevará al módulo 09.

---

## 1. Qué es Compose y qué problema resuelve

En el módulo 07 necesitaste esto:

```bash
docker network create notas-red
docker build -t notas-api:1.0 ./api
docker build -t notas-web:1.0 ./web
docker run -d --name api --network notas-red notas-api:1.0
docker run -d --name web --network notas-red -p 8080:3000 -e API_URL=http://api:5000 notas-web:1.0
```

Con Compose lo escribes **una vez**, de forma **declarativa** (describes *qué*
quieres, no *los pasos*), en un fichero que se guarda en git con el código:

```bash
docker compose up -d
```

> 🧠 **Declarativo vs imperativo.** Con `docker run` das órdenes ("crea esto,
> arranca aquello"). Con Compose describes el **estado deseado** ("quiero estos
> servicios con esta configuración") y Compose calcula qué hay que crear,
> recrear o dejar como está. Si ejecutas `up` dos veces, la segunda no hace
> nada porque ya está todo como pediste.

> ⚠️ **`docker compose` vs `docker-compose`.** La versión antigua (v1) era un
> programa aparte en Python que se escribía con guion. Está obsoleta. Usa
> `docker compose` (con espacio, plugin v2). El fichero puede llamarse
> `compose.yaml` (nombre recomendado) o `docker-compose.yml` (antiguo). La
> línea `version: "3.8"` que verás en tutoriales antiguos ya no hace falta.

---

## 2. El fichero `compose.yaml`, línea a línea

Abre [compose.yaml](compose.yaml). La estructura general:

```yaml
name: notas-08            # nombre del proyecto

services:                 # ← los contenedores (cada servicio = 1 o más contenedores iguales)
  api:
    build: ./api          # construir la imagen desde ./api/Dockerfile
    image: notas-api:1.0  # ...y llamarla así
    restart: unless-stopped

  web:
    build: ./web
    image: notas-web:1.0
    ports:
      - "8080:3000"       # = docker run -p 8080:3000
    environment:
      API_URL: http://api:5000   # = docker run -e API_URL=...
    depends_on:
      - api               # orden de arranque
    restart: unless-stopped

# networks:  ← no hace falta: Compose crea una red "notas-08_default" automáticamente
# volumes:   ← (lo usaremos en el módulo 09)
```

### Equivalencias con `docker run`

| `docker run` | `compose.yaml` |
|--------------|----------------|
| `--name api` | la clave del servicio (`api:`) |
| `-p 8080:3000` | `ports: ["8080:3000"]` |
| `-e VAR=valor` | `environment: { VAR: valor }` |
| `--env-file fichero` | `env_file: fichero` |
| `-v datos:/ruta` | `volumes: ["datos:/ruta"]` |
| `--network red` | `networks: [red]` (o la red por defecto) |
| `--restart unless-stopped` | `restart: unless-stopped` |
| `--memory 256m --cpus 0.5` | `deploy: { resources: { limits: { memory: 256M, cpus: "0.5" } } }` |
| `docker build -t img ./dir` | `build: ./dir` + `image: img` |
| `imagen comando args` | `command: ["comando", "args"]` |

### Claves más usadas

| Clave | Para qué |
|-------|----------|
| `image` | Imagen a usar (o nombre para la que se construya) |
| `build` | Carpeta (contexto) con el Dockerfile. Forma larga: `build: { context: ./api, dockerfile: Dockerfile.prod, args: {...} }` |
| `ports` | Puertos publicados |
| `environment` / `env_file` | Variables de entorno |
| `volumes` | Volúmenes y bind mounts |
| `networks` | Redes a las que se conecta |
| `depends_on` | Dependencias de arranque (y con condiciones, módulo 09) |
| `restart` | Política de reinicio |
| `command` / `entrypoint` | Sustituir `CMD` / `ENTRYPOINT` de la imagen |
| `healthcheck` | Comprobación de salud (módulo 09) |
| `profiles` | Servicios opcionales que solo arrancan si los pides (módulo 11) |

---

## 3. Arrancar y gestionar

```bash
cd 08-docker-compose
docker compose up -d --build
```

- `up` → crea red, construye imágenes si hace falta, crea y arranca contenedores.
- `-d` → en segundo plano (sin `-d` verías los logs de todos y Ctrl+C lo pararía).
- `--build` → reconstruye las imágenes aunque ya existan (útil si cambiaste código).

```text
 ✔ Network notas-08_default  Created
 ✔ Container notas-08-api-1  Started
 ✔ Container notas-08-web-1  Started
```

Fíjate en los nombres: **`proyecto-servicio-número`**. Abre
`http://localhost:8080`: es la misma app que en el módulo 07.

### Comandos del día a día

Siempre desde la carpeta donde está el `compose.yaml`:

| Comando | Qué hace |
|---------|----------|
| `docker compose up -d` | Crear/actualizar y arrancar todo |
| `docker compose up -d --build` | Igual, reconstruyendo imágenes |
| `docker compose ps` | Estado de los servicios del proyecto |
| `docker compose logs` | Logs de todos (con colores por servicio) |
| `docker compose logs -f api` | Logs en directo de un servicio |
| `docker compose exec api sh` | Shell dentro del servicio `api` |
| `docker compose exec web wget -qO- http://api:5000/health` | Comando suelto |
| `docker compose run --rm api python -V` | Contenedor **nuevo** y temporal del servicio |
| `docker compose restart web` | Reiniciar un servicio |
| `docker compose stop` / `start` | Parar / arrancar sin borrar |
| `docker compose down` | Parar y **borrar** contenedores y red (los volúmenes se quedan) |
| `docker compose down -v` | Igual, **borrando también los volúmenes** ⚠️ |
| `docker compose down --rmi local` | ...y las imágenes construidas por Compose |
| `docker compose build` | Solo construir |
| `docker compose pull` | Descargar las imágenes nuevas |
| `docker compose config` | Ver el fichero final ya procesado (y validarlo) |
| `docker compose top` | Procesos de cada contenedor |
| `docker compose images` | Imágenes que usa el proyecto |

```bash
docker compose ps
docker compose logs
docker network ls | grep notas-08      # la red que ha creado Compose
docker compose exec web wget -qO- http://api:5000/health
```

> 🧠 Dentro de la red de Compose, **cada servicio es accesible por su nombre de
> servicio** (`api`, `web`). Por eso `API_URL: http://api:5000` funciona sin
> poner `container_name`.

---

## 4. 🧪 Experimentos

### Actualizar solo un servicio

Cambia el título en [web/server.js](web/server.js) y:

```bash
docker compose up -d --build
```

```text
 ✔ Container notas-08-api-1  Running      ← sin cambios: no la toca
 ✔ Container notas-08-web-1  Started      ← recreada con la imagen nueva
```

Compose compara el estado deseado con el actual y **solo recrea lo que ha
cambiado**. Las notas siguen ahí.

### Ver el fichero "resuelto"

```bash
docker compose config
```

Muestra el YAML completo con todos los valores por defecto y variables ya
sustituidas. Muy útil para detectar errores de indentación.

### Escalar la API... y descubrir un problema

```bash
docker compose up -d --scale api=3
docker compose ps                     # notas-08-api-1, api-2, api-3
```

> ⚠️ Esto funciona porque la API **no** publica puertos. Si tuviera
> `ports: ["5000:5000"]`, las réplicas 2 y 3 fallarían: el puerto 5000 del host
> solo puede tenerlo una.

El DNS de Docker devuelve las IPs de **las 3 réplicas** para el nombre `api`:

```bash
docker compose exec web nslookup api
for i in 1 2 3 4 5 6; do docker compose exec web wget -qO- http://api:5000/health; echo; done
# {"contenedor":"75485139c9da",...}
# {"contenedor":"7feaae4cc525",...}   ← distintos contenedores responden
# {"contenedor":"ae53242e7399",...}
```

Ahora crea unas notas desde el navegador y pide la lista varias veces:

```bash
for i in 1 2 3 4 5 6; do docker compose exec web wget -qO- http://api:5000/api/notas; echo; done
```

**Cada réplica tiene SUS PROPIAS notas** (o ninguna). Según qué réplica te
toque, ves unas notas u otras. ¿Por qué? Porque cada API guarda las notas **en
su memoria**. Tres procesos = tres listas distintas.

> 🧠 **Lección clave: para poder escalar un servicio, tiene que ser *stateless*
> (sin estado).** El estado (los datos) debe vivir **fuera**, en un servicio
> compartido: una base de datos. Eso es lo que hacemos en el módulo 09
> añadiendo un tercer contenedor.

(La web, por cierto, reutiliza conexiones HTTP, así que desde el navegador
puede que te "pegues" a una réplica y no lo notes. Los `wget` abren conexión
nueva cada vez y por eso se ve claro.)

```bash
docker compose up -d --scale api=1    # volver a una réplica
```

### `depends_on` no espera a que el servicio esté LISTO

`depends_on: [api]` solo garantiza que el contenedor de la API **se arranca
antes** que el de la web. **No** espera a que la API esté preparada para
recibir peticiones. Con una API que arranca en 1 segundo no se nota; con una
base de datos que tarda 5 segundos, sí. Lo resolvemos con *healthchecks* en el
módulo 09.

---

## 5. Varios ficheros Compose: desarrollo vs producción

Compose fusiona automáticamente `compose.yaml` con `compose.override.yaml` si
existe. Se usa para añadir cosas de **desarrollo** sin tocar el fichero base.
Por ejemplo, este `compose.override.yaml` montaría el código de la web en vivo:

```yaml
services:
  web:
    volumes:
      - ./web/server.js:/app/server.js   # bind mount: editas y reinicias sin rebuild
```

```bash
docker compose up -d                                        # base + override (desarrollo)
docker compose -f compose.yaml up -d                        # solo el base
docker compose -f compose.yaml -f compose.prod.yaml up -d   # base + otro fichero
```

---

## 6. ✍️ Ejercicios

**Ejercicio 1.** Cambia el `compose.yaml` para que la web se publique en el
puerto **9000** y aplica el cambio. ¿Qué servicios se recrean?

<details><summary>Ver solución</summary>

```yaml
    ports:
      - "9000:3000"
```

```bash
docker compose up -d       # solo se recrea "web"; "api" sigue Running
curl localhost:9000
```

</details>

**Ejercicio 2.** Añade un **tercer servicio** llamado `curioso`, con la imagen
`alpine`, que cada 5 segundos consulte la salud de la API e imprima el
resultado. Mira sus logs con `docker compose logs -f curioso`.

<details><summary>Ver solución</summary>

```yaml
  curioso:
    image: alpine:3.20
    command: ["sh", "-c", "while true; do wget -qO- http://api:5000/health; echo; sleep 5; done"]
    depends_on:
      - api
```

```bash
docker compose up -d
docker compose logs -f curioso
```

Acabas de "meter otro contenedor" en la aplicación sin tocar los demás. El
módulo 09 hace lo mismo con algo útil: una base de datos.

</details>

**Ejercicio 3.** Arranca el proyecto **dos veces a la vez** con nombres de
proyecto distintos (uno en el 8080 y otro en el 8081). Pista: `-p` en
`docker compose` es el nombre del proyecto, y los puertos se pueden sacar a una
variable `${PUERTO:-8080}`.

<details><summary>Ver solución</summary>

En `compose.yaml`:

```yaml
    ports:
      - "${PUERTO:-8080}:3000"
```

```bash
docker compose -p notas-a up -d
PUERTO=8081 docker compose -p notas-b up -d
docker ps          # 4 contenedores: notas-a-api-1, notas-a-web-1, notas-b-api-1, notas-b-web-1
docker compose -p notas-a down; docker compose -p notas-b down
```

Cada proyecto tiene su propia red, así que las webs de uno no ven la API del
otro. Así se levantan entornos idénticos aislados (por ejemplo, uno por rama).

</details>

### Limpieza del módulo

```bash
docker compose down
# Si modificaste ficheros:  git checkout .
```

---

➡️ Siguiente: [09 · Añadir otro contenedor: base de datos](../09-anadir-base-de-datos/README.md)
