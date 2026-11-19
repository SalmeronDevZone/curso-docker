# 12 · Depuración y errores comunes

**Objetivo:** tener un método para cuando algo no funciona, y una tabla con los
errores que te vas a encontrar (seguro) y cómo resolverlos.

---

## 1. El método: de fuera hacia dentro

Cuando "no funciona", hazte estas preguntas **en orden**:

```text
1. ¿El contenedor está corriendo?        docker ps -a                 (¿Up? ¿Exited? ¿Restarting?)
2. ¿Qué dice la app?                     docker logs <c>              (¡SIEMPRE lo primero!)
3. ¿Está sano?                           docker inspect -f '{{json .State.Health}}' <c>
4. ¿Cómo se arrancó exactamente?         docker inspect <c>           (Cmd, Env, Mounts, Networks)
5. ¿Qué ve desde dentro?                 docker exec -it <c> sh
6. ¿Llega por red?                       docker exec <otro> wget -qO- http://<c>:<puerto>
7. ¿Recursos?                            docker stats
8. ¿Qué ha pasado en Docker?             docker events  (en otra terminal)
```

### Herramientas

```bash
docker logs --tail 50 -f <c>            # últimas 50 líneas y seguir
docker logs --since 10m <c>             # de los últimos 10 minutos
docker compose logs -f api web          # varios servicios a la vez

docker inspect -f '{{.State.Status}} {{.State.ExitCode}} {{.State.Error}}' <c>
docker inspect -f '{{json .Config.Env}}' <c> | jq
docker inspect -f '{{json .Mounts}}' <c> | jq
docker inspect -f '{{json .NetworkSettings.Networks}}' <c> | jq

docker exec -it <c> sh                  # (o bash si la imagen lo trae)
docker exec <c> env                     # variables reales dentro
docker exec <c> cat /etc/resolv.conf    # DNS que usa

docker run --rm -it --network <red> nicolaka/netshoot   # caja de herramientas de red
docker cp <c>:/ruta/fichero .           # sacar un fichero para mirarlo
docker diff <c>                         # qué ha cambiado en su sistema de ficheros
docker events --since 10m               # arranques, paradas, muertes, OOM...
docker system df                        # espacio en disco
```

### Depurar un contenedor que se para al instante

No puedes hacer `exec` en un contenedor parado. Arranca **otro** con la misma
imagen pero con una shell en vez de su comando normal:

```bash
docker run --rm -it --entrypoint sh mi-imagen        # explora: ¿están los ficheros? ¿las variables?
# (dentro) ls -la /app ; env ; python app.py   ← lánzala a mano y mira el error
```

Con Compose: `docker compose run --rm --entrypoint sh api`.

---

## 2. Errores frecuentes y soluciones

### Instalación y permisos

| Error | Causa | Solución |
|-------|-------|----------|
| `permission denied while trying to connect to the Docker daemon socket` | Tu usuario no está en el grupo `docker` | `sudo usermod -aG docker $USER` y **cerrar sesión** |
| `Cannot connect to the Docker daemon at unix:///var/run/docker.sock` | Servicio parado | `sudo systemctl start docker`; mira `sudo journalctl -u docker -n 50` |
| `docker-compose: command not found` | Sintaxis v1 antigua | `docker compose` (con espacio) |

### Arrancar contenedores

| Error / síntoma | Causa | Solución |
|-----------------|-------|----------|
| `port is already allocated` / `address already in use` | Otro contenedor u otro programa usa ese puerto del host | `docker ps` para ver quién; `sudo ss -tlnp \| grep 8080`; cambia el puerto del host |
| `Conflict. The container name "/web" is already in use` | Ya existe un contenedor (quizá parado) con ese nombre | `docker rm -f web` o usa otro nombre |
| El contenedor sale al instante (`Exited (0)`) | Su proceso principal terminó (no hay nada en primer plano) | Mira `docker logs`. La app debe correr en primer plano, sin `&` ni demonizarse |
| `Exited (1)` / `Exited (2)` | Error de la app | `docker logs <c>` |
| `Exited (137)` | SIGKILL: sin memoria (OOM) o no paró a tiempo | `docker inspect -f '{{.State.OOMKilled}}' <c>`; sube `--memory` o arregla la fuga |
| `Exited (127)` / `executable file not found in $PATH` | El comando no existe en la imagen | Revisa `CMD`; en alpine no hay `bash` (usa `sh`) |
| `exec /start.sh: no such file or directory` (¡y el fichero existe!) | Finales de línea **CRLF** de Windows en el script (el intérprete es `/bin/bash\r`) | `sed -i 's/\r$//' start.sh` o `dos2unix`; este repo lo evita con `.gitattributes` |
| `exec format error` | Imagen de **otra arquitectura** (ARM vs x86) o script sin `#!` | `docker image inspect -f '{{.Architecture}}' img`; construir con `--platform linux/amd64` |
| `Restarting (1) X seconds ago` en bucle | La app falla al arrancar y la política de reinicio la relanza | `docker logs <c>` para ver el error de arranque |
| `unhealthy` | El healthcheck falla | `docker inspect -f '{{json .State.Health}}' <c> \| jq` muestra la salida de los últimos intentos |

### Red

| Error / síntoma | Causa | Solución |
|-----------------|-------|----------|
| `ENOTFOUND` / `bad address` / `Name or service not known` / `could not translate host name` | El nombre no resuelve: **no están en la misma red** o el nombre está mal | `docker network inspect <red>`; usa redes propias (la `bridge` por defecto no tiene DNS); revisa el nombre del servicio |
| `ECONNREFUSED` / `Connection refused` | El nombre resuelve pero **nadie escucha** en ese puerto | ¿Puerto correcto (el **interno**, no el publicado)? ¿La app escucha en `0.0.0.0`? ¿Ha terminado de arrancar? |
| Desde el navegador no carga, pero `docker exec <c> wget localhost:PUERTO` sí | La app escucha en `127.0.0.1` dentro del contenedor, o el puerto no está publicado | Escucha en `0.0.0.0`; revisa `-p` / `ports:` con `docker port <c>` |
| Usas `localhost` para llamar a otro contenedor | `localhost` = el propio contenedor | Usa el **nombre del servicio** (`http://api:5000`) |
| `curl: (52) Empty reply from server` | Puerto publicado, pero la app escucha solo en `127.0.0.1` | `host="0.0.0.0"` en la app |
| Desde Windows no llego a la app de la VM | Red de la VM | Módulo 00, sección 7 (NAT + reenvío o adaptador puente) |
| nginx da `502 Bad Gateway` tras recrear un servicio | nginx guardó la IP antigua | `docker compose restart proxy` |
| `host not found in upstream "api"` al arrancar nginx | La API no existe aún o no está en la misma red | `depends_on` con `service_healthy`; revisa `networks:` |

### Volúmenes y datos

| Error / síntoma | Causa | Solución |
|-----------------|-------|----------|
| Los datos desaparecen | No había volumen, o usaste `docker compose down -v` | Volumen con nombre en la ruta de datos correcta (léela en la doc de la imagen) |
| Cambié `POSTGRES_PASSWORD` y ahora `password authentication failed` | Esas variables solo se usan al inicializar un volumen **vacío** | Vuelve a la contraseña antigua, cámbiala con SQL, o `down -v` si no te importan los datos |
| `Permission denied` al escribir en un bind mount | El UID del proceso del contenedor no tiene permisos en tu carpeta | `ls -ln` para ver UIDs; `-u $(id -u):$(id -g)` o ajusta permisos |
| Ficheros creados por el contenedor son de `root` en mi carpeta | El contenedor corre como root | `-u $(id -u):$(id -g)` o `USER` en el Dockerfile |
| Montaste tu código y "desaparece" lo de la imagen | El bind mount **tapa** el contenido de esa ruta | Es lo esperado; monta solo lo que necesites |
| `Read-only file system` | `read_only: true` o montaje `:ro` | Añade `tmpfs` para las rutas que necesiten escritura |

### Construir imágenes

| Error / síntoma | Causa | Solución |
|-----------------|-------|----------|
| `COPY failed: file not found in build context` | El fichero está fuera del contexto o en `.dockerignore` | Revisa el contexto (`docker build ... CONTEXTO`) y `.dockerignore` |
| Cambié el código y el contenedor sigue con el viejo | No reconstruiste, o no recreaste el contenedor | `docker compose up -d --build` |
| Cada build reinstala todas las dependencias | Orden de capas: `COPY . .` antes de instalar | Copia primero `requirements.txt`/`package*.json` (módulo 03) |
| `npm ci` falla: `package-lock.json` no existe | `npm ci` lo necesita | Genera el lock con `npm install` en local y súbelo a git |
| La imagen pesa muchísimo | Imagen base completa, cachés, herramientas de build | `-slim`/`-alpine`, `--no-cache-dir`, limpiar apt en el mismo `RUN`, multi-stage |
| `no space left on device` | Disco lleno de imágenes, capas, caché y logs | `docker system df`; `docker system prune`; `docker builder prune` |

### Compose

| Error / síntoma | Causa | Solución |
|-----------------|-------|----------|
| `yaml: line X: mapping values are not allowed` / `did not find expected key` | Indentación YAML (¡tabuladores!) | Solo espacios; `docker compose config` para validar |
| `required variable X is missing a value` | Falta la variable en `.env` | `cp .env.example .env` |
| `WARN: The "X" variable is not set. Defaulting to a blank string` | Igual, pero sin `:?` | Crea el `.env` o define la variable |
| `Found orphan containers` | Quitaste un servicio del YAML pero su contenedor sigue | `docker compose up -d --remove-orphans` |
| La API arranca antes que la BD y falla | `depends_on` simple no espera a que esté lista | `condition: service_healthy` + healthcheck en la BD (módulo 09) |
| `service "x" refers to undefined volume/network` | Falta declararlo en `volumes:` / `networks:` de nivel superior | Añádelo al final del fichero |

---

## 3. 🧪 Ejercicio: arregla lo roto

Cada uno de estos comandos tiene **un** error. Ejecútalo, lee el mensaje, y
arréglalo **usando el método de la sección 1**.

```bash
# 1
docker run -d --name roto1 -p 8080:80 nginx:1.27-alpine nginx
# 2
docker run -d --name roto2 -e POSTGRES_PASWORD=secreto postgres:17-alpine
# 3
docker network create r3
docker run -d --name servidor3 nginx:1.27-alpine
docker run --rm --network r3 alpine wget -qO- http://servidor3
# 4
docker run -d --name roto4 alpine
# 5
docker run --rm -p 8080:8000 python:3.12-slim python -m http.server 8000 --bind 127.0.0.1 &
sleep 3; curl localhost:8080
```

<details><summary>Ver soluciones</summary>

1. `docker ps -a` → `Exited (0)`. El comando `nginx` sin `-g "daemon off;"` se
   va a segundo plano, el proceso principal termina y el contenedor se para.
   Solución: no sustituir el `CMD` de la imagen (quitar el `nginx` final).
2. `docker logs roto2` → *superuser password is not specified*. La variable
   está mal escrita: `POSTGRES_PASSWORD` (con dos S).
3. `bad address 'servidor3'`: `servidor3` no está en la red `r3`. Solución:
   `docker network connect r3 servidor3` o arrancarlo con `--network r3`.
4. `Exited (0)` al instante: el `CMD` de alpine es `sh`, que sin `-it` termina.
   Para que viva, dale un proceso que no termine (`sleep infinity`) o `-it`.
5. `Empty reply from server`: la app escucha en `127.0.0.1` dentro del
   contenedor. Cambia a `--bind 0.0.0.0`. (Para el proceso con `docker ps` +
   `docker rm -f`.)

```bash
docker rm -f roto1 roto2 servidor3 roto4 2>/dev/null; docker network rm r3
```

</details>

---

➡️ Para repasar: [Chuleta de comandos](../CHULETA.md) · [Volver al índice](../README.md)
