# 04 · Volúmenes: que los datos sobrevivan

**Objetivo:** entender por qué los datos de un contenedor se pierden, y los
tres mecanismos para evitarlo: volúmenes con nombre, bind mounts y tmpfs.

---

## 1. El problema

Recuerda la teoría: cada contenedor escribe en su **capa escribible**, que se
**borra** con el contenedor.

### 🧪 Experimento: perder datos

```bash
docker run --name temporal alpine sh -c 'echo "mis datos" > /datos.txt'
docker diff temporal            # A /datos.txt  -> está en la capa escribible del contenedor
docker cp temporal:/datos.txt . && cat datos.txt && rm datos.txt   # (aún se puede sacar: el contenedor parado existe)
docker rm temporal              # borramos el contenedor...
# ...y el fichero ya no existe en ningún sitio
```

Para una base de datos, unas fotos subidas por usuarios o unos logs que quieras
guardar, esto no vale.

---

## 2. Los tres tipos de montaje

```text
                   ┌──────────── TU UBUNTU (host) ────────────┐
                   │                                          │
                   │  /var/lib/docker/volumes/datos/_data ◀─┐ │   VOLUMEN CON NOMBRE
                   │                                        │ │   (lo gestiona Docker)
                   │  /home/tu/proyecto/html ◀───────────┐  │ │   BIND MOUNT
                   │                                     │  │ │   (una carpeta tuya)
                   │  RAM ◀──────────────────────────┐   │  │ │   TMPFS
                   │                                 │   │  │ │   (memoria, se borra)
                   │   ┌──── contenedor ───────────┐ │   │  │ │
                   │   │  /tmp/cache  ─────────────┼─┘   │  │ │
                   │   │  /usr/share/nginx/html ───┼─────┘  │ │
                   │   │  /var/lib/postgresql/data ┼────────┘ │
                   │   └───────────────────────────┘          │
                   └──────────────────────────────────────────┘
```

| | Volumen con nombre | Bind mount | tmpfs |
|---|---|---|---|
| Dónde vive | `/var/lib/docker/volumes/...` (gestionado por Docker) | Una ruta que **tú eliges** del host | En memoria RAM |
| Sintaxis `-v` | `-v datos:/ruta` | `-v /ruta/absoluta:/ruta` o `-v ./carpeta:/ruta` | `--tmpfs /ruta` |
| Sobrevive al `rm` del contenedor | ✅ Sí | ✅ Sí (es tu carpeta) | ❌ No |
| Uso típico | **Datos de producción**: bases de datos, ficheros subidos | **Desarrollo**: editar código en tu máquina y verlo en el contenedor; ficheros de configuración | Datos temporales o sensibles que no deben tocar disco |
| Portabilidad | Alta (no depende de rutas del host) | Baja (depende de la estructura de carpetas del host) | — |

> 🧠 **Cómo distingue Docker un volumen de un bind mount en `-v`:** si lo que va
> antes de `:` es un **nombre** (`datos`), es un volumen. Si es una **ruta**
> (empieza por `/` o `./`), es un bind mount.

---

## 3. Volúmenes con nombre

```bash
docker volume create misdatos
docker volume ls
docker volume inspect misdatos      # "Mountpoint": "/var/lib/docker/volumes/misdatos/_data"
```

### 🧪 Experimento: los datos sobreviven al contenedor

```bash
# Contenedor 1 escribe en el volumen y se borra solo (--rm)
docker run --rm -v misdatos:/datos alpine sh -c 'echo "Escrito a las $(date)" >> /datos/log.txt'

# Contenedor 2 (otro distinto, otra imagen incluso) lee el mismo volumen
docker run --rm -v misdatos:/datos ubuntu cat /datos/log.txt

# Repite el primer comando un par de veces y vuelve a leer: se van acumulando
```

El volumen es independiente de cualquier contenedor. Puedes conectarlo a uno,
borrarlo, y conectarlo a otro.

```bash
sudo ls -l /var/lib/docker/volumes/misdatos/_data   # los ficheros están en tu disco
```

> 💡 Si el volumen no existe, `docker run -v nombre:/ruta` lo crea solo.
> Y si el volumen está vacío y la imagen ya tenía ficheros en esa ruta, Docker
> los copia al volumen la primera vez.

### 🧪 Experimento: una base de datos que no pierde datos

```bash
docker run -d --name pg -e POSTGRES_PASSWORD=secreto \
  -v pgdatos:/var/lib/postgresql/data postgres:17-alpine
sleep 5
docker exec pg psql -U postgres -c "CREATE TABLE amigos (nombre text);"
docker exec pg psql -U postgres -c "INSERT INTO amigos VALUES ('Ana'), ('Luis');"

docker rm -f pg          # ¡adiós contenedor!

docker run -d --name pg -e POSTGRES_PASSWORD=secreto \
  -v pgdatos:/var/lib/postgresql/data postgres:17-alpine
sleep 3
docker exec pg psql -U postgres -c "SELECT * FROM amigos;"   # Ana, Luis: siguen ahí ✅
docker rm -f pg
```

¿Cómo sabes en qué ruta guarda los datos una imagen? **Leyendo su
documentación** en Docker Hub (o buscando `VOLUME` con `docker image inspect`).

> ⚠️ **PostgreSQL 18 o superior** cambió la ruta recomendada a
> `/var/lib/postgresql`. En este curso usamos la 17 con la ruta clásica. Si
> algún día subes de versión, lee las notas de la imagen.

---

## 4. Bind mounts: tu carpeta dentro del contenedor

Ideal para **desarrollo**: editas en tu máquina, el contenedor lo ve al instante.

```bash
cd 04-volumenes
docker run -d --name estatica -p 8080:80 \
  -v "$(pwd)/web-estatica:/usr/share/nginx/html:ro" \
  nginx:1.27-alpine
curl localhost:8080
```

- `$(pwd)/web-estatica` → ruta **absoluta** de tu carpeta (bind mount).
- `/usr/share/nginx/html` → donde nginx busca las páginas.
- `:ro` → **solo lectura**: el contenedor no puede modificar tu carpeta.

### 🧪 Experimento: cambios en vivo

```bash
nano web-estatica/index.html     # cambia el <h1>, guarda (Ctrl+O, Enter, Ctrl+X)
curl localhost:8080              # ¡el cambio ya está! Sin reconstruir nada
docker exec estatica touch /usr/share/nginx/html/x   # Read-only file system (por el :ro)
docker rm -f estatica
```

> 🧠 **Bind mount vs COPY en el Dockerfile:**
> - `COPY` mete los ficheros **dentro de la imagen** → para producción: la
>   imagen es autosuficiente.
> - Bind mount los **enlaza en tiempo de ejecución** → para desarrollo o para
>   inyectar configuración (lo usamos en el proyecto final con `nginx.conf`).
>
> ⚠️ Un bind mount **tapa** lo que hubiera en esa ruta de la imagen. Si montas
> una carpeta vacía en `/app`, tu código desaparece dentro del contenedor.

### Sintaxis larga: `--mount`

Equivalente a `-v`, más explícita (y da error si la ruta del host no existe,
en lugar de crear una carpeta vacía):

```bash
docker run --rm --mount type=bind,source="$(pwd)/web-estatica",target=/datos,readonly alpine ls /datos
docker run --rm --mount type=volume,source=misdatos,target=/datos alpine ls /datos
docker run --rm --mount type=tmpfs,target=/datos alpine df -h /datos
```

### ⚠️ Permisos con bind mounts

Dentro del contenedor, los ficheros conservan el **UID/GID numérico** del host.
Si el contenedor corre como root y crea ficheros en tu carpeta, en tu Ubuntu
aparecerán como propiedad de `root`:

```bash
mkdir -p /tmp/prueba
docker run --rm -v /tmp/prueba:/out alpine touch /out/creado-por-root
ls -l /tmp/prueba                 # propietario: root
docker run --rm -u "$(id -u):$(id -g)" -v /tmp/prueba:/out alpine touch /out/creado-por-mi
ls -l /tmp/prueba                 # propietario: tú
```

---

## 5. tmpfs: en memoria

```bash
docker run --rm --tmpfs /cache alpine sh -c 'echo hola > /cache/x && df -h /cache'
```

Útil para ficheros temporales o con datos sensibles, o para dar una carpeta
escribible a un contenedor de solo lectura (lo haremos en el proyecto final).

---

## 6. Copias de seguridad de un volumen

Truco clásico: un contenedor temporal que monta **el volumen** y **una carpeta
tuya**, y empaqueta uno en la otra.

```bash
# BACKUP: volumen misdatos -> ./misdatos-backup.tgz
docker run --rm -v misdatos:/origen:ro -v "$(pwd)":/backup alpine \
  tar czf /backup/misdatos-backup.tgz -C /origen .

# RESTAURAR en un volumen nuevo
docker volume create misdatos-restaurado
docker run --rm -v misdatos-restaurado:/destino -v "$(pwd)":/backup alpine \
  tar xzf /backup/misdatos-backup.tgz -C /destino
docker run --rm -v misdatos-restaurado:/datos alpine cat /datos/log.txt
```

> ⚠️ Para bases de datos **en marcha** es mejor usar su herramienta propia
> (`pg_dump`, `mysqldump`): copiar los ficheros mientras se escriben puede
> dar una copia corrupta. Lo hacemos en el proyecto final.

---

## 7. Gestionar volúmenes

```bash
docker volume ls                        # listar
docker volume ls -f dangling=true       # los que no usa ningún contenedor
docker volume inspect misdatos          # detalles
docker volume rm misdatos               # borrar uno (no puede estar en uso)
docker volume prune                     # borrar los anónimos que no se usan
docker volume prune -a                  # borrar TODOS los que no se usan ⚠️ (también con nombre)
docker rm -v contenedor                 # borra el contenedor y SUS volúmenes anónimos
```

> ⚠️ `docker volume prune -a` y `docker compose down -v` **borran datos**. Antes
> de ejecutarlos, piensa si hay algo que quieras conservar.

---

## 8. ✍️ Ejercicios

**Ejercicio 1.** Crea un volumen `contador`. Ejecuta 3 veces un contenedor
`alpine` efímero (`--rm`) que añada una línea a `/datos/visitas.txt` en ese
volumen. Al final, muestra el fichero con un cuarto contenedor y cuenta las líneas.

<details><summary>Ver solución</summary>

```bash
docker volume create contador
for i in 1 2 3; do
  docker run --rm -v contador:/datos alpine sh -c 'echo "visita $(date +%T)" >> /datos/visitas.txt'
done
docker run --rm -v contador:/datos alpine sh -c 'cat /datos/visitas.txt; wc -l < /datos/visitas.txt'
docker volume rm contador
```

</details>

**Ejercicio 2.** Sirve con `nginx:1.27-alpine` en el puerto 8080 una carpeta
`~/miweb` con un `index.html` que escribas tú. Comprueba que si editas el HTML
el cambio se ve sin reiniciar nada. ¿Qué pasa si montas una carpeta que no existe?

<details><summary>Ver solución</summary>

```bash
mkdir -p ~/miweb && echo '<h1>Mi web</h1>' > ~/miweb/index.html
docker run -d --name ej2 -p 8080:80 -v ~/miweb:/usr/share/nginx/html:ro nginx:1.27-alpine
curl localhost:8080
echo '<h1>Mi web v2</h1>' > ~/miweb/index.html && curl localhost:8080
docker rm -f ej2
```

Con `-v` y una ruta inexistente, Docker **crea una carpeta vacía** (propiedad de
root) y nginx da 403. Con `--mount type=bind` daría error claro.

</details>

**Ejercicio 3.** Haz una copia de seguridad del volumen `pgdatos` del
experimento de PostgreSQL en un `.tgz`, borra el volumen, restáuralo y comprueba
que la tabla `amigos` sigue ahí.

<details><summary>Ver solución</summary>

```bash
# (el contenedor pg debe estar parado/borrado para copiar ficheros de forma segura)
docker run --rm -v pgdatos:/origen:ro -v "$(pwd)":/backup alpine tar czf /backup/pg.tgz -C /origen .
docker volume rm pgdatos
docker volume create pgdatos
docker run --rm -v pgdatos:/destino -v "$(pwd)":/backup alpine tar xzf /backup/pg.tgz -C /destino
docker run -d --name pg -e POSTGRES_PASSWORD=secreto -v pgdatos:/var/lib/postgresql/data postgres:17-alpine
sleep 3; docker exec pg psql -U postgres -c "SELECT * FROM amigos;"
docker rm -f pg
```

</details>

### Limpieza del módulo

```bash
docker rm -f pg estatica ej2 2>/dev/null
docker volume rm misdatos misdatos-restaurado pgdatos 2>/dev/null
rm -f misdatos-backup.tgz pg.tgz
```

---

➡️ Siguiente: [05 · Redes](../05-redes/README.md)
