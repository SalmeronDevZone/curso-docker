# 07 · Separar las aplicaciones en dos contenedores

**Objetivo:** aprender un **método** para separar aplicaciones que viven juntas
en un contenedor, y aplicarlo a la app de notas del módulo 06, usando solo
`docker build`, `docker network` y `docker run` (sin Compose todavía, para que
veas cada pieza).

```text
ANTES (módulo 06)                               DESPUÉS (este módulo)

┌──────── contenedor "mono" ────────┐           ┌─────── red "notas-red" ───────┐
│ start.sh                          │           │                               │
│  ├─ node  :3000 ─┐                │  ───▶     │ [ web ] ──http://api:5000──▶ [ api ]
│  └─ python:5000 ◀┘ localhost      │           │  :3000                  :5000 │
└───────────────────────────────────┘           └───┬───────────────────────────┘
        ▲ -p 8080:3000                              ▲ -p 8080:3000 (solo la web)
```

---

## 1. El método: 7 pasos para separar cualquier aplicación

Este método sirve para la app de notas y para cualquier proyecto real.

### Paso 1 — Inventario: ¿qué procesos hay y qué necesita cada uno?

| | API | WEB |
|---|---|---|
| Comando | `python app.py` | `node server.js` |
| Runtime | Python 3.12 | Node 22 |
| Dependencias | `requirements.txt` | `package.json` |
| Puerto en el que escucha | 5000 | 3000 |
| ¿Quién la usa? | La WEB | El navegador |
| ¿Guarda datos? | Sí, en memoria | No |

Fuentes: el `start.sh`, el Dockerfile, `ps` dentro del contenedor, el código.

### Paso 2 — Mapa de comunicaciones: ¿quién habla con quién y cómo?

```text
navegador ──HTTP :3000──▶ WEB ──HTTP :5000──▶ API
```

Busca **cómo** se comunican: ¿por red (HTTP, TCP)? ¿por ficheros compartidos?
¿por `localhost`? ¿por un socket Unix? Cada tipo de comunicación tiene su
solución:

| Comunicación en el monolito | Solución al separar |
|-----------------------------|---------------------|
| `localhost:PUERTO` | **Nombre del contenedor/servicio**: `api:5000`, vía red Docker |
| Ficheros en una carpeta compartida | **Volumen** montado en ambos contenedores, o mejor, cambiar a comunicación por red (API) |
| Socket Unix (`/tmp/app.sock`) | Volumen compartido para el socket, o pasar a TCP |
| Variables/memoria compartida | Rediseñar: base de datos, Redis, cola de mensajes |

### Paso 3 — Encontrar el acoplamiento "a fuego" y sacarlo a configuración

Busca en el código direcciones escritas a mano (`localhost`, `127.0.0.1`,
rutas absolutas). En nuestra web:

```js
const API_URL = process.env.API_URL || "http://localhost:5000";
```

¡Ya viene preparada! La dirección de la API se lee de la variable `API_URL`.
Si no fuera así, este sería el **único cambio de código** necesario: sustituir
la dirección fija por una variable de entorno.

> 🧠 Este es el principio **"config en el entorno"** (de *The Twelve-Factor
> App*): el código no sabe dónde está desplegado; se lo dicen desde fuera. La
> **misma imagen** de la web sirve para el monolito (`localhost:5000`), para
> dos contenedores (`api:5000`) o para producción (`https://api.miempresa.com`).

Comprueba también que cada app **escucha en `0.0.0.0`** y no en `127.0.0.1`
(módulo 05): si la API escuchara en `127.0.0.1`, la web, desde otro contenedor,
no podría llegar.

### Paso 4 — Un Dockerfile por aplicación

Cada app tiene ahora su carpeta con **su** Dockerfile y **su** imagen base:

```text
07-separar-en-dos-contenedores/
├── api/
│   ├── Dockerfile        ← FROM python:3.12-slim   (sin Node)
│   ├── .dockerignore
│   ├── app.py
│   └── requirements.txt
├── web/
│   ├── Dockerfile        ← FROM node:22-alpine     (sin Python)
│   ├── .dockerignore
│   ├── server.js
│   ├── package.json
│   └── package-lock.json
├── arrancar.sh           ← todos los comandos de este README en un script
└── parar.sh
```

Compara [api/Dockerfile](api/Dockerfile) y [web/Dockerfile](web/Dockerfile) con
el Dockerfile del módulo 06. Han desaparecido:

- la instalación de Node con `apt-get` en una imagen de Python,
- `start.sh` y toda su gestión de procesos y señales,
- `procps` y demás añadidos.

Cada `CMD` arranca directamente su app, que pasa a ser el PID 1.

### Paso 5 — Una red para que se encuentren

Una red propia (no la `bridge` por defecto) para tener DNS por nombre.

### Paso 6 — Arrancar cada contenedor exponiendo solo lo necesario

- **API:** en la red, **sin** `-p`. Solo la web necesita hablar con ella.
- **WEB:** en la red, **con** `-p 8080:3000`, y con `API_URL` apuntando al
  nombre del contenedor de la API.

### Paso 7 — Verificar y comparar

Que funciona igual que antes... y que los problemas del módulo 06 han desaparecido.

---

## 2. Hazlo tú: comando a comando

```bash
cd 07-separar-en-dos-contenedores
```

### 2.1 Construir las dos imágenes

```bash
docker build -t notas-api:1.0 ./api
docker build -t notas-web:1.0 ./web
docker images | grep notas
```

Fíjate en el último argumento: `./api` y `./web` son **contextos distintos**.
Cada imagen solo ve los ficheros de su carpeta.

### 2.2 Crear la red

```bash
docker network create notas-red
```

### 2.3 Arrancar la API

```bash
docker run -d --name api --network notas-red notas-api:1.0
docker logs api
```

- `--name api` → **este nombre es el que usará la web para encontrarla**.
- Sin `-p`: no es accesible desde fuera.

### 2.4 Arrancar la WEB

```bash
docker run -d --name web --network notas-red \
  -p 8080:3000 \
  -e API_URL=http://api:5000 \
  notas-web:1.0
docker logs web     # [web] Escuchando en el puerto 3000 ... API_URL=http://api:5000
```

### 2.5 Probar

Abre `http://localhost:8080` y crea notas. En la caja gris:

```text
Página servida por WEB desde el contenedor  9af69655d0ee
Datos servidos por la API desde el contenedor 0c9a7a97259c    ← ¡ahora son DISTINTOS!
API_URL = http://api:5000
```

> 💡 El script [arrancar.sh](arrancar.sh) hace estos pasos de golpe y
> [parar.sh](parar.sh) lo deshace. Úsalos cuando ya los hayas hecho a mano.

---

## 3. 🧪 Experimentos: los problemas del módulo 06, resueltos

### ✅ Imágenes pequeñas y especializadas

```bash
docker images | grep notas
```

Compara `notas-api` + `notas-web` con `notas-mono`. Cada una lleva solo lo suyo
y usa la imagen base óptima. Si sale un parche de seguridad de Node, solo
reconstruyes la web.

### ✅ Logs separados

```bash
docker logs -f api     # solo la API (en otra terminal: docker logs -f web)
```

### ✅ Actualizar la web SIN tocar la API (las notas sobreviven)

1. Crea un par de notas.
2. Cambia el título en [web/server.js](web/server.js) (`📝 Notas` → `📝 Mis notas`).
3. Reconstruye y sustituye **solo** la web:

   ```bash
   docker build -t notas-web:1.1 ./web
   docker rm -f web
   docker run -d --name web --network notas-red -p 8080:3000 \
     -e API_URL=http://api:5000 notas-web:1.1
   ```

4. Recarga: título nuevo **y las notas siguen ahí**. La API ni se ha enterado.

### ✅ Si una falla, solo se reinicia esa

```bash
# Añadimos una política de reinicio a los dos contenedores (sin recrearlos)
docker update --restart unless-stopped api web

# Simulamos que la API "se estrella": matamos su proceso DESDE EL HOST.
# (Recuerda la teoría: un contenedor es un proceso más de tu Ubuntu.)
PID_API=$(docker inspect -f '{{.State.Pid}}' api)
echo "La API es el proceso $PID_API de tu Ubuntu"
sudo kill -9 "$PID_API"

sleep 3
docker ps                                    # api: "Up 2 seconds" (reiniciada) · web: "Up 10 minutes" (intacta)
docker inspect -f '{{.RestartCount}}' api    # 1
```

Docker ha reiniciado **solo la API**. La web no se ha enterado (aunque la API
ha perdido sus notas porque las guarda en memoria: lo arreglamos en el módulo 09).

> ⚠️ ¿Por qué no simplemente `docker kill api`? Porque Docker lo considera una
> parada **manual** y respeta tu decisión: no la reinicia. Las políticas de
> reinicio son para los fallos, no para cuando tú paras algo a propósito.

### 🧪 ¿Qué pasa si la web NO está en la misma red?

```bash
docker run -d --name web-perdida -p 8081:3000 -e API_URL=http://api:5000 notas-web:1.0
curl -s localhost:8081 | grep error
# No puedo conectar con la API en http://api:5000 → ENOTFOUND (getaddrinfo ENOTFOUND api)
docker rm -f web-perdida
```

`ENOTFOUND` = "no sé quién es `api`": el DNS de Docker solo resuelve nombres
**dentro de la misma red**.

### 🧪 ¿Y si se nos olvida `API_URL`?

```bash
docker run -d --name web-sin-config --network notas-red -p 8082:3000 notas-web:1.0
curl -s localhost:8082 | grep error
# No puedo conectar con la API en http://localhost:5000 → ECONNREFUSED
docker rm -f web-sin-config
```

`ECONNREFUSED` en `localhost` = la web busca la API **dentro de su propio
contenedor**, y ahí no hay nadie escuchando en el 5000.

> 🧠 Aprende a leer estos dos errores; los verás mil veces:
> - **ENOTFOUND / bad address / Name or service not known** → problema de
>   **nombre/red** (¿misma red? ¿nombre bien escrito?).
> - **ECONNREFUSED / Connection refused** → el nombre resuelve pero **nadie
>   escucha** en ese puerto (¿app arrancada? ¿puerto correcto? ¿escucha en
>   0.0.0.0?).

### 🧪 Inspeccionar la red

```bash
docker network inspect notas-red --format '{{range .Containers}}{{.Name}} {{.IPv4Address}}{{"\n"}}{{end}}'
docker exec web wget -qO- http://api:5000/health    # la web puede llegar a la API
curl localhost:5000/health                          # tú (desde fuera) no: no está publicada
```

---

## 4. Lo que todavía es incómodo

Ha funcionado, pero piensa en lo que has tenido que teclear: crear la red, dos
`build`, dos `run` largos con opciones que hay que recordar, y repetirlo todo
igual cada vez. Y para parar, otros tres comandos. ¿Y si fueran 6 servicios?

Esa es exactamente la razón de existir de **Docker Compose** (módulo 08):
escribir todo esto **una vez** en un fichero y arrancarlo con un comando.

---

## 5. ✍️ Ejercicios

**Ejercicio 1.** Arranca una **segunda** web (`web2`) en el puerto 8081 que use
**la misma API**. Crea una nota desde cada web. ¿Qué ves en cada una? ¿Por qué
esto era imposible en el módulo 06?

<details><summary>Ver solución</summary>

```bash
docker run -d --name web2 --network notas-red -p 8081:3000 -e API_URL=http://api:5000 notas-web:1.0
```

Las dos webs muestran **las mismas notas**: comparten una única API. Cada web
tiene un ID de contenedor distinto, pero el de la API es el mismo. Has escalado
la web sin tocar la API; en el monolito cada web venía con su propia API.

```bash
docker rm -f web2
```

</details>

**Ejercicio 2.** Lanza la API con otro nombre (`backend`) y haz que la web
funcione con ella **sin reconstruir ninguna imagen**.

<details><summary>Ver solución</summary>

```bash
docker rm -f api web
docker run -d --name backend --network notas-red notas-api:1.0
docker run -d --name web --network notas-red -p 8080:3000 -e API_URL=http://backend:5000 notas-web:1.0
```

Solo cambia la configuración (`API_URL`), no la imagen. Ese es el poder de
sacar la configuración a variables de entorno.

```bash
docker rm -f backend web
```

</details>

**Ejercicio 3.** La API tiene que seguir siendo privada, pero quieres poder
consultarla **desde tu Ubuntu** para depurar, sin que sea accesible desde otros
equipos de la red. ¿Cómo la arrancas?

<details><summary>Ver solución</summary>

```bash
docker run -d --name api --network notas-red -p 127.0.0.1:5000:5000 notas-api:1.0
curl localhost:5000/api/notas       # ✅ desde la propia máquina
# desde otro equipo: http://IP_DE_LA_VM:5000 -> no conecta
```

</details>

**Ejercicio 4.** Escribe la lista de comandos para **parar y limpiar** todo lo
de este módulo sin mirar `parar.sh`, y luego compáralo.

<details><summary>Ver solución</summary>

```bash
docker rm -f web api              # primero los contenedores...
docker network rm notas-red       # ...luego la red (no se puede borrar con contenedores conectados)
docker rmi notas-web:1.1          # opcional: imágenes
```

</details>

### Limpieza del módulo

```bash
bash parar.sh     # (si le das permisos con chmod +x parar.sh, también vale ./parar.sh)
# Si modificaste web/server.js:  git checkout web/server.js
```

---

➡️ Siguiente: [08 · Docker Compose](../08-docker-compose/README.md)
