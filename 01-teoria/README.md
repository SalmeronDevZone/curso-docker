# 01 · Teoría: qué es Docker de verdad

**Objetivo:** entender qué es un contenedor, cómo funciona por dentro y el
vocabulario básico. Si este módulo te queda claro, el resto del curso es
"aplicar lo que ya entiendes". Al final hay experimentos para **ver** la teoría
en tu propia máquina.

---

## 1. El problema que resuelve Docker

Imagina una aplicación web en Python. Para que funcione necesita:

- una versión concreta de Python (3.12, no 3.8),
- unas librerías concretas (Flask 3.1, psycopg 3.2...),
- librerías del sistema (libpq, openssl...),
- variables de entorno, ficheros de configuración, un puerto libre...

En tu portátil funciona. En el servidor hay Python 3.8 y otra versión de
openssl. En el ordenador de tu compañera, otra app usa Flask 2. Resultado: el
famoso **"en mi máquina funciona"**.

**Docker empaqueta la aplicación JUNTO con todo lo que necesita para
ejecutarse** (su sistema de ficheros, librerías, runtime, configuración) en una
**imagen**. Esa imagen se ejecuta igual en cualquier máquina con Docker.

> 🧠 La analogía clásica es el **contenedor de mercancías**: al barco le da igual
> si dentro hay plátanos o coches; todos los contenedores tienen el mismo
> tamaño y los mismos enganches. A Docker le da igual si dentro hay Python,
> Node o Java: todos se arrancan, paran, conectan y mueven igual.

---

## 2. ¿Qué es un contenedor? (la respuesta corta y la de verdad)

**Respuesta corta:** un entorno aislado donde se ejecuta una aplicación con su
propio sistema de ficheros, su propia red y sus propios procesos.

**La respuesta de verdad, la importante:**

> 🧠 **Un contenedor es un PROCESO normal de Linux** al que el kernel le pone
> "anteojeras" para que crea que está solo en la máquina.

No es una máquina virtual pequeña. No arranca un sistema operativo. No hay un
kernel dentro. Es un proceso más de tu Ubuntu (lo verás con `ps` en el
experimento 1), pero:

- **ve** solo sus propios procesos, su propia red y su propio sistema de
  ficheros → gracias a los **namespaces**;
- **puede usar** solo los recursos que le dejemos (CPU, RAM) → gracias a los
  **cgroups**;
- **arranca** desde un sistema de ficheros empaquetado en capas → la **imagen**.

---

## 3. Contenedor vs máquina virtual

```text
        MÁQUINAS VIRTUALES                         CONTENEDORES
┌──────────┐ ┌──────────┐ ┌──────────┐   ┌──────────┐ ┌──────────┐ ┌──────────┐
│  App A   │ │  App B   │ │  App C   │   │  App A   │ │  App B   │ │  App C   │
│ Librerías│ │ Librerías│ │ Librerías│   │ Librerías│ │ Librerías│ │ Librerías│
│ SO       │ │ SO       │ │ SO       │   └──────────┘ └──────────┘ └──────────┘
│ invitado │ │ invitado │ │ invitado │   ┌──────────────────────────────────────┐
│ (kernel) │ │ (kernel) │ │ (kernel) │   │      Docker Engine (dockerd)         │
└──────────┘ └──────────┘ └──────────┘   └──────────────────────────────────────┘
┌──────────────────────────────────────┐ ┌──────────────────────────────────────┐
│ Hipervisor (VirtualBox, VMware, KVM) │ │ Sistema operativo anfitrión + KERNEL │
└──────────────────────────────────────┘ │       (UN SOLO kernel compartido)    │
┌──────────────────────────────────────┐ └──────────────────────────────────────┘
│     Sistema operativo anfitrión      │ ┌──────────────────────────────────────┐
└──────────────────────────────────────┘ │               Hardware               │
┌──────────────────────────────────────┐ └──────────────────────────────────────┘
│               Hardware               │
└──────────────────────────────────────┘
```

| | Máquina virtual | Contenedor |
|---|---|---|
| Qué virtualiza | El **hardware** (CPU, disco, red virtuales) | El **sistema operativo** (vistas aisladas del mismo kernel) |
| Kernel | Cada VM tiene **el suyo** | **Todos comparten** el del anfitrión |
| Tamaño típico | Gigabytes | Megabytes |
| Arranque | Minutos (arranca un SO entero) | Milisegundos/segundos (arranca un proceso) |
| Aislamiento | Muy fuerte | Fuerte, pero menor (el kernel es compartido) |
| Puede ejecutar otro SO | Sí (Windows dentro de Linux) | No: contenedores Linux necesitan kernel Linux |
| Uso típico | Aislar sistemas completos | Empaquetar y desplegar aplicaciones |

> 🧠 Por eso en Windows y Mac, Docker Desktop crea **una VM Linux** por debajo:
> los contenedores Linux necesitan un kernel Linux. En tu Ubuntu no hace falta.
>
> Y no son excluyentes: en tu caso tienes **contenedores dentro de una VM**,
> que es exactamente lo que pasa en la nube (AWS, Azure...).

---

## 4. Cómo funciona por dentro: los 3 ingredientes

Docker no inventó los contenedores: usa piezas que **ya existen en el kernel
Linux** y las hace fáciles de usar.

### 4.1 Namespaces → qué puede VER el proceso

Un *namespace* es una "vista" aislada de un recurso del sistema.

| Namespace | Aísla | Efecto dentro del contenedor |
|-----------|-------|------------------------------|
| `pid` | Los procesos | El contenedor ve solo sus procesos; el suyo es el **PID 1** |
| `net` | La red | Tiene su propia IP, sus propios puertos, su propia tabla de rutas |
| `mnt` | Los puntos de montaje | Ve su propio sistema de ficheros (`/`), no el del host |
| `uts` | El nombre de máquina | Tiene su propio `hostname` (el ID del contenedor) |
| `ipc` | Comunicación entre procesos | Memoria compartida separada |
| `user` | Los usuarios | (Opcional) root dentro ≠ root fuera |

### 4.2 Control groups (cgroups) → cuánto puede USAR el proceso

Los cgroups limitan y miden recursos: CPU, memoria, E/S de disco, número de
procesos... Cuando haces `docker run --memory 256m`, Docker crea un cgroup que
impide al contenedor usar más de 256 MB. Si se pasa, el kernel lo mata
(*OOM killer*, código de salida **137**).

### 4.3 Sistema de ficheros por capas (OverlayFS) → de dónde ARRANCA

La imagen es una pila de capas de **solo lectura**. Al crear un contenedor,
Docker pone encima una capa fina **escribible**. OverlayFS las "aplana" para
que el contenedor vea un único sistema de ficheros normal.

```text
 contenedor A          contenedor B
┌─────────────┐      ┌─────────────┐
│ capa R/W  A │      │ capa R/W  B │   ← cada contenedor tiene la SUYA (se borra con él)
└──────┬──────┘      └──────┬──────┘
       └──────────┬─────────┘
┌─────────────────▼──────────────────┐
│ capa 4: COPY . .        (tu código)│ ┐
│ capa 3: RUN pip install (librerías)│ │ IMAGEN: capas de SOLO LECTURA,
│ capa 2: COPY requirements.txt      │ │ compartidas entre todos los
│ capa 1: python:3.12-slim (Debian…) │ ┘ contenedores que la usan
└────────────────────────────────────┘
```

**Copy-on-write:** si el contenedor modifica un fichero de la imagen, ese
fichero se copia primero a su capa escribible y se modifica ahí. La imagen
original nunca cambia. Por eso 10 contenedores de la misma imagen de 200 MB no
ocupan 2 GB: comparten las capas y cada uno solo guarda sus diferencias.

> ⚠️ **Consecuencia importantísima:** la capa escribible **se borra cuando
> borras el contenedor**. Todo lo que tu app escriba ahí (subidas de usuarios,
> una base de datos...) desaparece. Para guardar datos de verdad se usan
> **volúmenes** (módulo 04).

---

## 5. Imagen vs contenedor

Es la distinción más importante del curso:

| Imagen | Contenedor |
|--------|------------|
| Plantilla **de solo lectura** | Instancia **en ejecución** (o parada) de una imagen |
| Se **construye** (`docker build`) o se **descarga** (`docker pull`) | Se **crea y arranca** (`docker run`) |
| Es como una **clase**, una **receta**, un **.iso** | Es como un **objeto**, un **plato cocinado**, un **PC instalado** |
| Una imagen → muchos contenedores | Cada contenedor viene de exactamente una imagen |
| No "se ejecuta" ni tiene estado | Tiene estado: procesos, capa escribible, IP... |

```text
   Dockerfile ──docker build──▶ IMAGEN ──docker run──▶ CONTENEDOR 1
   (receta)                    (plantilla)  ├──run──▶ CONTENEDOR 2
                                  ▲   │     └──run──▶ CONTENEDOR 3
                       docker pull│   │docker push
                                  │   ▼
                             REGISTRO (Docker Hub)
```

---

## 6. Registros y nombres de imágenes

Un **registro** es un almacén de imágenes. El público por defecto es
**Docker Hub** (hub.docker.com). Hay otros: GitHub Container Registry (ghcr.io),
los de AWS/Azure/Google, o uno privado de tu empresa.

El nombre completo de una imagen tiene esta forma:

```text
  registro/usuario/repositorio:etiqueta
  docker.io/library/nginx:1.27-alpine
  ─────────┬─────── ──┬── ─────┬─────
           │          │        └── etiqueta (tag): versión/variante. Por defecto "latest"
           │          └── repositorio
           └── registro + usuario. "docker.io/library/" se omite para imágenes oficiales
```

Ejemplos equivalentes: `nginx` = `nginx:latest` = `docker.io/library/nginx:latest`.

- **Etiqueta (tag):** nombre legible y **movible**. Hoy `nginx:latest` apunta a
  una versión y mañana a otra.
- **Digest:** huella SHA-256 **inmutable** del contenido:
  `nginx@sha256:1a2b3c...`. Siempre es exactamente la misma imagen.

> ⚠️ `latest` **no significa "la más reciente"**: es solo la etiqueta que se usa
> si no pones ninguna. En proyectos serios fija siempre la versión
> (`postgres:17-alpine`, no `postgres`).

**Variantes habituales** de las imágenes oficiales:

| Sufijo | Base | Tamaño | Cuándo |
|--------|------|--------|--------|
| (ninguno) `python:3.12` | Debian completo | ~1 GB | Si necesitas compilar cosas |
| `-slim` | Debian mínimo | ~130 MB | **Buena opción por defecto** |
| `-alpine` | Alpine Linux (musl) | ~50 MB | Muy pequeña; a veces da guerra con librerías en C |
| `distroless` / `scratch` | Casi nada / nada | 2-20 MB | Producción, binarios estáticos (módulo 10) |

---

## 7. Arquitectura de Docker

```text
 TÚ                                     MOTOR DE DOCKER (servicio en segundo plano)
┌─────────────┐   API REST sobre    ┌──────────────┐     ┌────────────┐     ┌──────┐
│ docker CLI  │──/var/run/docker.──▶│   dockerd    │────▶│ containerd │────▶│ runc │──▶ proceso del
│ (cliente)   │      sock           │ (daemon)     │     │            │     │      │    contenedor
└─────────────┘                     └──────┬───────┘     └────────────┘     └──────┘
                                           │ imágenes, redes, volúmenes, builds
                                           ▼
                                    /var/lib/docker
                                           │ pull / push
                                           ▼
                                    Registro (Docker Hub)
```

- **`docker` (CLI):** solo traduce tus comandos a peticiones HTTP a la API.
- **`dockerd`:** el demonio. Gestiona imágenes, redes, volúmenes y builds.
- **`containerd`:** gestiona el ciclo de vida de los contenedores.
- **`runc`:** crea los namespaces y cgroups y lanza el proceso. Luego se retira.

> 🧠 **OCI (Open Container Initiative)** es el estándar abierto de formato de
> imagen y de ejecución. Gracias a él, una imagen construida con Docker funciona
> con Podman, con Kubernetes, etc. Docker no es la única herramienta de
> contenedores; es la más popular para desarrollar.

---

## 8. El ciclo de vida de un contenedor

```text
               docker create            docker start
   IMAGEN ───────────────────▶ CREATED ──────────────▶ RUNNING ◀──┐
      │                                                 │  │  │    │ docker unpause
      └──── docker run = create + start ───────────────▶│  │  └──▶ PAUSED
                                                        │  │ docker pause
         el proceso principal termina / docker stop     │  │
                    ┌───────────────────────────────────┘  │ docker restart
                    ▼                                       │
                 EXITED ─────────── docker start ──────────┘
                    │
                    │ docker rm
                    ▼
                 (borrado: su capa escribible desaparece)
```

### La regla de oro: el contenedor vive lo que vive su proceso principal

> 🧠 Un contenedor **ejecuta UN proceso principal** (el `CMD`/`ENTRYPOINT` de la
> imagen), que dentro del contenedor es el **PID 1**. Cuando ese proceso
> termina, **el contenedor se para**. Siempre. No hay más.

Consecuencias que confunden mucho al principio:

- `docker run ubuntu` arranca y se para al instante. ¿Por qué? Su comando por
  defecto es `bash`, y bash sin terminal termina inmediatamente.
- Un servidor web se queda corriendo porque su proceso nunca termina (espera
  peticiones).
- Si tu app hace `nohup app &` y luego el script termina... el contenedor muere.
  La app debe correr **en primer plano**.
- Si el proceso principal no gestiona bien las señales, `docker stop` tarda en
  pararlo (módulo 10).

### Códigos de salida que verás

| Código | Significado |
|--------|-------------|
| `0` | Terminó bien |
| `1`, `2`... | Error de la aplicación |
| `125` | Error del propio `docker run` (opción mal escrita...) |
| `126` | El comando existe pero no se puede ejecutar (permisos) |
| `127` | Comando no encontrado |
| `137` | Matado con SIGKILL (128+9): `docker kill`, sin memoria (OOM) o no paró a tiempo con `docker stop` |
| `143` | Terminó por SIGTERM (128+15) sin gestionarlo |

---

## 9. Un proceso (una responsabilidad) por contenedor

Es la filosofía de Docker y la razón de los módulos 06-07:

- Cada contenedor hace **una cosa**: la API, la web, la base de datos.
- Así cada pieza se puede **actualizar, escalar, reiniciar y vigilar por
  separado**, y sus logs no se mezclan.
- Se comunican **por la red** (HTTP, TCP), no compartiendo memoria ni ficheros.

No es una ley física (se *puede* meter más de un proceso en un contenedor), es
una buena práctica con muchas ventajas. Lo veremos en el módulo 06.

---

## 10. Contenedores efímeros y "sin estado"

> 🧠 Trata los contenedores como **ganado, no como mascotas**: si uno se rompe,
> no lo curas, lo borras y creas otro idéntico desde la imagen.

Para que eso sea posible:

- **No modifiques contenedores a mano** (entrar con `exec` y hacer
  `apt install`): ese cambio se pierde. Cambia el **Dockerfile** y reconstruye.
- **Los datos importantes, fuera** del contenedor: en volúmenes o en una base
  de datos (módulos 04 y 09).
- **La configuración, por variables de entorno** (`-e`, `environment:`), no
  metida a fuego en la imagen. Así la misma imagen sirve para desarrollo y
  producción.

---

## 11. Redes y puertos (avance del módulo 05)

- Cada contenedor tiene su propia IP en una red virtual interna de Docker.
- Desde fuera (tu navegador) no se llega a esa IP: hay que **publicar** un
  puerto: `-p 8080:80` = "lo que llegue al puerto 8080 de mi Ubuntu, mándalo al
  puerto 80 del contenedor".
- En una red creada por ti, los contenedores se encuentran **por su nombre**
  (`http://api:5000`) gracias a un DNS interno de Docker.

---

## 12. El ecosistema en un vistazo

| Herramienta | Para qué |
|-------------|----------|
| **Docker Engine** | Ejecutar contenedores en una máquina |
| **Dockerfile** | Receta para construir una imagen |
| **Docker Compose** | Definir y arrancar apps de varios contenedores en **una** máquina |
| **Docker Hub** | Registro público de imágenes |
| **Docker Desktop** | Docker Engine + VM + interfaz gráfica para Windows/Mac |
| **Podman** | Alternativa a Docker, sin demonio, compatible con sus comandos |
| **Kubernetes** | Orquestar contenedores en **muchas** máquinas (siguiente nivel tras este curso) |

---

## 13. Glosario rápido

| Término | Definición |
|---------|-----------|
| **Imagen** | Plantilla de solo lectura con el sistema de ficheros y la configuración de una app |
| **Contenedor** | Proceso aislado que se ejecuta a partir de una imagen |
| **Capa (layer)** | Cada uno de los "pisos" de solo lectura que forman una imagen |
| **Dockerfile** | Fichero de texto con las instrucciones para construir una imagen |
| **Contexto de build** | Carpeta que se envía al motor al hacer `docker build` |
| **Registro** | Servidor que almacena imágenes (Docker Hub) |
| **Tag** | Etiqueta legible de una versión de imagen (`:1.0`, `:latest`) |
| **Volumen** | Almacenamiento persistente gestionado por Docker, independiente del contenedor |
| **Bind mount** | Carpeta de tu máquina montada dentro de un contenedor |
| **Red bridge** | Red virtual interna para que los contenedores se comuniquen |
| **Publicar un puerto** | Conectar un puerto del host con uno del contenedor (`-p`) |
| **PID 1** | El proceso principal de un contenedor |
| **Daemon** | Programa en segundo plano; aquí `dockerd` |
| **Compose** | Herramienta para definir apps multi-contenedor en YAML |
| **Healthcheck** | Comando que Docker ejecuta periódicamente para saber si la app está sana |

---

## 14. 🧪 Experimentos: ver la teoría con tus propios ojos

Haz estos experimentos después de instalar Docker (módulo 00). No te preocupes
si no entiendes todas las opciones: las veremos en el módulo 02.

### Experimento 1 — Un contenedor es un proceso del host

```bash
docker run -d --name dormilon alpine sleep 1000   # contenedor que "duerme" 1000 s
ps -ef | grep "sleep 1000"                       # ¡lo ves desde Ubuntu como un proceso más!
docker top dormilon                               # el mismo proceso, visto por Docker
```

El proceso `sleep 1000` aparece en el `ps` de tu Ubuntu con un PID normal
(p. ej. 12345). No hay ninguna máquina virtual: es un proceso.

### Experimento 2 — Namespace PID: dentro, es el PID 1

```bash
docker exec dormilon ps      # (ps dentro del contenedor)
```

Dentro, el mismo `sleep 1000` tiene **PID 1** y no ve ninguno de los cientos
de procesos de tu Ubuntu. Mismo proceso, dos "vistas" distintas.

### Experimento 3 — Namespace UTS y NET: otro hostname, otra red

```bash
hostname                                  # el nombre de tu Ubuntu
docker exec dormilon hostname             # el ID corto del contenedor
ip -4 addr | grep inet                    # las IPs de tu Ubuntu
docker exec dormilon ip -4 addr           # la IP del contenedor (172.17.x.x)
```

### Experimento 4 — Mismo kernel

```bash
uname -r                                  # versión del kernel de Ubuntu
docker run --rm alpine uname -r           # ¡la misma! Alpine usa TU kernel
docker run --rm alpine cat /etc/os-release   # pero el sistema de ficheros es de Alpine
```

Esto demuestra que un contenedor **no tiene kernel propio**: comparte el del
host, pero ve el sistema de ficheros de su imagen.

### Experimento 5 — cgroups: limitar la memoria

```bash
# Un contenedor con un límite de 50 MB de RAM
docker run -d --name limitado --memory 50m alpine sleep 300
docker stats --no-stream limitado      # columna "MEM USAGE / LIMIT": ... / 50MiB
docker rm -f limitado

# Un programa que intenta reservar 200 MB dentro de un límite de 50 MB
docker run --rm --memory 50m python:3.12-slim python -c "x = bytearray(200*1024*1024)"
echo "Código de salida: $?"            # 137 -> el kernel lo ha matado (OOM killer)
```

El límite no lo vigila Docker "a mano": lo impone **el kernel** a través del
cgroup del contenedor.

### Experimento 6 — Capas e imágenes compartidas

```bash
docker pull python:3.12-slim
docker image history python:3.12-slim    # cada línea es una capa
docker system df                          # cuánto ocupa todo
```

### Experimento 7 — La capa escribible es efímera

```bash
docker exec dormilon sh -c 'echo "dato importante" > /fichero.txt'
docker exec dormilon cat /fichero.txt     # ahí está
docker diff dormilon                      # A /fichero.txt  (A = añadido en la capa R/W)
docker rm -f dormilon                     # borramos el contenedor...
docker run --rm alpine cat /fichero.txt   # ...y en uno nuevo NO existe
```

### Limpieza

```bash
docker rm -f dormilon 2>/dev/null; docker container prune -f
```

---

## 15. ✍️ Autoevaluación

Responde sin mirar y luego comprueba.

1. ¿Un contenedor tiene su propio kernel?
2. ¿Qué diferencia hay entre una imagen y un contenedor?
3. ¿Qué pasa con los ficheros que crea una app dentro del contenedor cuando borras el contenedor?
4. ¿Por qué `docker run ubuntu` se para al instante?
5. ¿Qué componente del kernel limita la RAM de un contenedor? ¿Y cuál hace que solo vea sus procesos?
6. ¿Qué significa un código de salida 137?
7. ¿`nginx:latest` es siempre la versión más nueva de nginx?
8. ¿Por qué un contenedor Linux no puede ejecutarse directamente sobre Windows?

<details>
<summary>Ver respuestas</summary>

1. No. Comparte el kernel del host. Solo tiene su propio sistema de ficheros y sus propias "vistas" (namespaces).
2. La imagen es la plantilla de solo lectura; el contenedor es una instancia en ejecución de esa plantilla, con su propia capa escribible y su propio estado.
3. Se pierden: estaban en la capa escribible del contenedor, que se borra con él. Para conservarlos hay que usar volúmenes.
4. Porque su proceso principal es `bash`, que sin una terminal interactiva (`-it`) termina inmediatamente. Y el contenedor vive lo que vive su proceso principal.
5. Los **cgroups** limitan recursos (RAM, CPU). El **namespace PID** hace que solo vea sus procesos.
6. Que el proceso fue matado con SIGKILL (128 + 9): `docker kill`, falta de memoria (OOM) o no terminó a tiempo tras `docker stop`.
7. No. `latest` es solo la etiqueta por defecto; el mantenedor decide a qué apunta. Fija versiones concretas.
8. Porque necesita un kernel Linux, y Windows tiene otro kernel. Docker Desktop lo soluciona con una VM Linux.

</details>

---

➡️ Siguiente: [02 · Primeros pasos](../02-primeros-pasos/README.md)
