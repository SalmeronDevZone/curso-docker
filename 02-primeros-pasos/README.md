# 02 · Primeros pasos: manejar contenedores

**Objetivo:** dominar el ciclo de vida de un contenedor (crear, arrancar, mirar,
entrar, parar, borrar) usando imágenes ya hechas. Aquí todavía no construimos
nada nuestro.

> Escribe tú los comandos (no copies y pegues a ciegas). Después de cada uno,
> pregúntate: ¿qué ha pasado? ¿qué contenedores hay ahora? (`docker ps -a`)

---

## 1. Tu primer contenedor, paso a paso

```bash
docker run hello-world
```

¿Qué ha pasado exactamente?

1. El cliente `docker` le pide al motor (`dockerd`) que ejecute la imagen `hello-world`.
2. El motor busca la imagen **en local**. No la tiene → `Unable to find image locally`.
3. La **descarga** (*pull*) de Docker Hub.
4. **Crea** un contenedor a partir de ella (capa escribible + namespaces + cgroups).
5. **Arranca** su proceso principal, que imprime el mensaje en la salida estándar.
6. El proceso termina → **el contenedor se para** (estado `Exited`).
7. El contenedor **sigue existiendo** (parado) hasta que lo borres.

```bash
docker ps        # contenedores EN MARCHA -> vacío
docker ps -a     # TODOS, también los parados -> ahí está, "Exited (0)"
docker images    # la imagen hello-world se ha quedado descargada
```

Vuelve a ejecutar `docker run hello-world`: esta vez no descarga nada (ya la
tiene) y crea **otro** contenedor distinto. `docker ps -a` mostrará dos.

---

## 2. Anatomía de `docker run`

```text
docker run [OPCIONES] IMAGEN[:TAG] [COMANDO] [ARGUMENTOS...]
```

Las opciones que usarás el 90 % del tiempo:

| Opción | Qué hace | Ejemplo |
|--------|----------|---------|
| `-d` | *Detached*: en segundo plano, te devuelve la terminal | `docker run -d nginx` |
| `-it` | Interactivo + terminal (para usar una shell) | `docker run -it ubuntu bash` |
| `--rm` | Borra el contenedor automáticamente al pararse | `docker run --rm alpine echo hola` |
| `--name` | Le da un nombre (si no, Docker inventa uno tipo `happy_turing`) | `--name web` |
| `-p H:C` | Publica el puerto C del contenedor en el puerto H de tu máquina | `-p 8080:80` |
| `-e VAR=valor` | Variable de entorno | `-e SALUDO=hola` |
| `-v origen:destino` | Monta un volumen o una carpeta (módulo 04) | `-v datos:/data` |
| `--network` | Lo conecta a una red (módulo 05) | `--network mired` |
| `--restart` | Política de reinicio (`no`, `on-failure`, `unless-stopped`, `always`) | `--restart unless-stopped` |
| `--memory` / `--cpus` | Límites de recursos | `--memory 256m --cpus 0.5` |

> ⚠️ **El orden importa:** las opciones de Docker van **antes** del nombre de la
> imagen. Todo lo que va **después** de la imagen es el comando para el
> contenedor. `docker run alpine -d` no funciona como esperas.

---

## 3. Contenedores interactivos

```bash
docker run -it ubuntu bash
```

Ahora estás **dentro** de un contenedor Ubuntu. Explora:

```bash
# (dentro del contenedor)
cat /etc/os-release   # es Ubuntu... pero mínimo
ps aux                # solo ves bash (PID 1) y el propio ps
ls /home              # vacío: no es TU sistema de ficheros
apt-get update && apt-get install -y curl   # puedes instalar cosas...
exit                  # sales -> bash termina -> el contenedor se para
```

```bash
docker ps -a          # Exited
docker run -it ubuntu bash   # ¿sigue instalado curl? -> NO: es otro contenedor nuevo
# (dentro) which curl -> nada.  exit
```

> 🧠 Cada `docker run` crea un contenedor **nuevo** desde la imagen original.
> Lo que instalaste en el anterior se quedó en *su* capa escribible. Por eso los
> cambios se hacen en el Dockerfile (módulo 03), no a mano dentro.

Con Alpine (mucho más pequeña) la shell es `sh`, no `bash`:

```bash
docker run -it --rm alpine sh
# (dentro) exit  -> como pusimos --rm, el contenedor se borra solo
```

**Salir sin parar el contenedor:** pulsa `Ctrl+P` y luego `Ctrl+Q`. Para volver:
`docker attach <nombre>`.

---

## 4. Un servidor web en segundo plano

```bash
docker run -d --name miweb -p 8080:80 nginx:1.27-alpine
```

- `-d` → en segundo plano. Te devuelve el ID largo del contenedor.
- `--name miweb` → para referirnos a él por nombre.
- `-p 8080:80` → el puerto 8080 de tu Ubuntu lleva al puerto 80 del contenedor.

✅ **Comprueba:**

```bash
docker ps                         # Up X seconds   0.0.0.0:8080->80/tcp
curl http://localhost:8080        # HTML de "Welcome to nginx!"
```

(o abre `http://localhost:8080` en el navegador; desde Windows, ver módulo 00, sección 7)

### Ver qué está pasando dentro

```bash
docker logs miweb                 # la salida (stdout/stderr) del proceso principal
docker logs -f miweb              # en directo (como tail -f). Ctrl+C para salir
docker logs --tail 20 -t miweb    # últimas 20 líneas con fecha
docker top miweb                  # procesos que corren dentro
docker stats miweb                # CPU, RAM, red en tiempo real. Ctrl+C para salir
docker inspect miweb              # TODA la información en JSON
docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' miweb   # solo la IP
docker port miweb                 # puertos publicados
```

> 🧠 **Los logs de un contenedor son lo que su proceso principal escribe en
> stdout y stderr.** Por eso las apps en Docker deben escribir sus logs en la
> salida estándar, no en ficheros. (Lo verás en el Dockerfile de la API:
> `PYTHONUNBUFFERED=1`.)

### Entrar en un contenedor que ya está corriendo

```bash
docker exec -it miweb sh          # abre una shell DENTRO de miweb (un 2º proceso)
# (dentro del contenedor)
ls /usr/share/nginx/html
echo "<h1>Modificado a mano</h1>" > /usr/share/nginx/html/index.html
exit                              # sales de la shell; el contenedor SIGUE corriendo
```

```bash
curl http://localhost:8080        # <h1>Modificado a mano</h1>
docker exec miweb cat /etc/nginx/conf.d/default.conf   # exec sin -it para un comando suelto
```

> 🧠 **`run` vs `exec`:** `docker run` crea un contenedor **nuevo**.
> `docker exec` ejecuta un proceso **adicional** dentro de uno que **ya existe**
> y está en marcha.

### Copiar ficheros entre tu máquina y el contenedor

```bash
docker cp miweb:/etc/nginx/nginx.conf ./nginx.conf   # del contenedor a tu máquina
docker cp ./nginx.conf miweb:/tmp/                   # de tu máquina al contenedor
docker diff miweb       # qué ficheros han cambiado respecto a la imagen (A/C/D)
rm nginx.conf
```

---

## 5. Parar, arrancar, reiniciar, borrar

```bash
docker stop miweb       # para con educación: SIGTERM, espera, y si no SIGKILL
docker ps -a            # Exited (0)
docker start miweb      # lo vuelve a arrancar (EL MISMO contenedor, con sus cambios)
curl localhost:8080     # ¡sigue "Modificado a mano"! Parar no borra la capa escribible
docker restart miweb    # stop + start
docker kill miweb       # para a lo bruto (SIGKILL inmediato)
docker rm miweb         # BORRA el contenedor (tiene que estar parado)
docker rm -f miweb      # para y borra de una vez
```

Ahora crea uno nuevo con el mismo comando del principio y comprueba que la
modificación **ha desaparecido**: el contenedor nuevo parte de la imagen limpia.

| Acción | ¿Se pierden los cambios de la capa escribible? |
|--------|----------------------------------------------|
| `stop` / `start` / `restart` | No |
| Reiniciar la VM (con `--restart`) | No |
| `rm` y volver a hacer `run` | **Sí** |

---

## 6. Gestionar imágenes

```bash
docker pull redis:7-alpine          # descargar sin ejecutar
docker images                       # listar (también: docker image ls)
docker image history redis:7-alpine # sus capas
docker image inspect redis:7-alpine # metadatos: CMD, ENV, puertos expuestos...
docker tag redis:7-alpine mi-redis:pruebas   # otro NOMBRE para la MISMA imagen (mismo ID)
docker images                       # fíjate: mismo IMAGE ID
docker rmi mi-redis:pruebas         # borra solo la etiqueta
docker rmi redis:7-alpine           # borra la imagen
```

> ⚠️ No puedes borrar una imagen que usa algún contenedor (aunque esté parado).
> Primero borra el contenedor.

### Buscar imágenes

En [hub.docker.com](https://hub.docker.com). Fíjate en las insignias:
**Docker Official Image** y **Verified Publisher** son de confianza. Lee
siempre la documentación de la imagen: explica sus variables de entorno,
puertos y volúmenes (p. ej. la de `postgres`).

---

## 7. Variables de entorno

Muchas imágenes se configuran con variables:

```bash
docker run --rm -e NOMBRE=Ana alpine sh -c 'echo "Hola $NOMBRE"'
docker run --rm alpine env                  # variables que trae el contenedor

# Ejemplo real: PostgreSQL EXIGE una contraseña por variable
docker run -d --name pg -e POSTGRES_PASSWORD=secreto postgres:17-alpine
docker logs pg | tail -3                    # "database system is ready to accept connections"
docker exec -it pg psql -U postgres -c 'SELECT version();'
docker rm -f pg
```

¿Y si no pasas `POSTGRES_PASSWORD`? Pruébalo: el contenedor se para al
instante. `docker logs` te dirá por qué. **Ese es el primer reflejo ante
cualquier contenedor que no arranca: mirar sus logs.**

---

## 8. Limpieza: no llenes el disco

Los contenedores parados, las imágenes viejas y la caché de builds se acumulan.

```bash
docker system df                 # cuánto ocupa cada cosa
docker container prune           # borra contenedores PARADOS
docker image prune               # borra imágenes "colgantes" (<none>)
docker image prune -a            # borra TODAS las imágenes que no use ningún contenedor
docker volume prune              # borra volúmenes sin usar ⚠️ (¡datos!)
docker builder prune             # borra la caché de construcción
docker system prune              # contenedores parados + redes sin usar + imágenes colgantes + caché
```

Todos piden confirmación (sáltala con `-f`, con cuidado).

---

## 9. Referenciar contenedores

Puedes usar el **nombre** o el **ID**, y del ID basta con el principio, siempre
que no sea ambiguo:

```bash
docker ps -a                 # CONTAINER ID: 3f9a1c2b7d4e
docker logs 3f9              # funciona si ningún otro ID empieza por 3f9
docker ps -aq                # solo los IDs (útil para scripts)
docker rm $(docker ps -aq -f status=exited)   # borra todos los parados
```

---

## 10. ✍️ Ejercicios

**Ejercicio 1.** Arranca un contenedor `nginx:1.27-alpine` en segundo plano,
llamado `ej1`, accesible en el puerto **9090** de tu máquina. Comprueba con
`curl` que responde y mira sus logs: ¿aparece tu petición?

<details><summary>Ver solución</summary>

```bash
docker run -d --name ej1 -p 9090:80 nginx:1.27-alpine
curl -s localhost:9090 | head -5
docker logs ej1          # última línea: "GET / HTTP/1.1" 200 ... "curl/..."
docker rm -f ej1
```

</details>

**Ejercicio 2.** Ejecuta, en un contenedor que se borre solo al acabar, el
comando `cat /etc/os-release` en las imágenes `alpine`, `ubuntu` y `debian`.
¿Qué te dice esto sobre el kernel y el sistema de ficheros?

<details><summary>Ver solución</summary>

```bash
for img in alpine ubuntu debian; do docker run --rm $img cat /etc/os-release | head -2; done
for img in alpine ubuntu debian; do docker run --rm $img uname -r; done
```

Cada uno tiene el sistema de ficheros de su distribución, pero `uname -r`
devuelve **el mismo kernel** en los tres: el de tu Ubuntu.

</details>

**Ejercicio 3.** Arranca `alpine` con el comando `sleep 5` en segundo plano.
Mira `docker ps` inmediatamente y otra vez a los 10 segundos. Explica qué ha
pasado y qué código de salida tiene.

<details><summary>Ver solución</summary>

```bash
docker run -d --name ej3 alpine sleep 5
docker ps            # aparece
sleep 10; docker ps  # ya no aparece
docker ps -a         # Exited (0)
docker rm ej3
```

El proceso principal (`sleep 5`) terminó a los 5 segundos, así que el
contenedor se paró. Código 0: terminó sin errores.

</details>

**Ejercicio 4.** Arranca un `redis:7-alpine` llamado `cache` en segundo plano.
Usa `docker exec` para ejecutar `redis-cli` dentro y guarda la clave
`curso` con valor `docker`. Para y arranca el contenedor: ¿sigue la clave?
Ahora bórralo y crea otro: ¿y ahora?

<details><summary>Ver solución</summary>

```bash
docker run -d --name cache redis:7-alpine
docker exec cache redis-cli SET curso docker
docker exec cache redis-cli GET curso          # "docker"
docker restart cache
docker exec cache redis-cli GET curso          # sigue ahí: Redis guarda a disco al pararse, y es el MISMO contenedor
docker rm -f cache
docker run -d --name cache redis:7-alpine
docker exec cache redis-cli GET curso          # (nil): contenedor nuevo = datos perdidos
docker rm -f cache
```

Para que sobrevivan al borrado necesitas un volumen **con nombre** → módulo 04.
(Curiosidad: la imagen de Redis declara `VOLUME /data`, así que Docker le crea
un volumen *anónimo* a cada contenedor. Lo verás con `docker volume ls`.)

</details>

**Ejercicio 5.** Sin mirar la documentación, averigua con `docker image inspect`
qué comando ejecuta por defecto la imagen `nginx:1.27-alpine` y qué puerto expone.

<details><summary>Ver solución</summary>

```bash
docker image inspect -f '{{.Config.Cmd}} {{.Config.ExposedPorts}}' nginx:1.27-alpine
# [nginx -g daemon off;] map[80/tcp:{}]
```

Fíjate en `daemon off;`: le dice a nginx que **no** se vaya a segundo plano,
porque si lo hiciera el proceso principal terminaría y el contenedor se pararía.

</details>

### Limpieza del módulo

```bash
docker rm -f miweb ej1 cache 2>/dev/null
docker container prune -f
```

---

➡️ Siguiente: [03 · Imágenes y Dockerfile](../03-imagenes-y-dockerfile/README.md)
