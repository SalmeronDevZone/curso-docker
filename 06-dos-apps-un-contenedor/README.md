# 06 · Dos aplicaciones en UN contenedor (el anti-patrón)

**Objetivo:** ver con tus propios ojos qué pasa cuando metes dos aplicaciones
en un solo contenedor, para entender **por qué** se separan. Esto es lo que te
encontrarás a menudo en proyectos heredados: "lo metimos todo en una imagen y
funciona... más o menos".

---

## 1. El escenario

Heredas un proyecto de **notas** con dos aplicaciones:

| App | Lenguaje | Puerto | Qué hace |
|-----|----------|--------|----------|
| **API** ([api/app.py](api/app.py)) | Python + Flask | 5000 | Guarda y devuelve notas en JSON |
| **WEB** ([web/server.js](web/server.js)) | Node + Express | 3000 | Página HTML; pide las notas a la API por HTTP |

Alguien lo "dockerizó" así:

```text
  navegador ──:8080──▶ ┌───────────────── contenedor "mono" ─────────────────┐
                       │  PID 1: /start.sh  (bash, hace de "niñera")          │
                       │    ├── PID 7: python /app/api/app.py   (:5000)       │
                       │    └── PID 8: node /app/web/server.js  (:3000)       │
                       │                                                      │
                       │  la WEB llama a la API en http://localhost:5000      │
                       │  (comparten red, así que "localhost" es el mismo)     │
                       └──────────────────────────────────────────────────────┘
```

Archivos:

```text
06-dos-apps-un-contenedor/
├── Dockerfile      ← UNA imagen con Python + Node
├── start.sh        ← arranca los 2 procesos y los vigila
├── .dockerignore
├── api/            ← app Python
└── web/            ← app Node
```

Lee primero el [Dockerfile](Dockerfile) y el [start.sh](start.sh). Fíjate en:

- `FROM python:3.12-slim` y luego **instala Node a mano** con `apt-get`.
- `ENV API_URL=http://localhost:5000`.
- `CMD ["/start.sh"]`: el proceso principal ya no es tu app, es un script.
- Todo lo que tiene que hacer `start.sh`: arrancar en segundo plano, capturar
  señales con `trap`, esperar con `wait -n`, decidir qué hacer si uno muere...

---

## 2. Construir y arrancar

```bash
cd 06-dos-apps-un-contenedor
docker build -t notas-mono:1.0 .
docker run -d --name mono -p 8080:3000 notas-mono:1.0
```

Abre `http://localhost:8080` (o `curl localhost:8080`) y **crea un par de notas**.

En la caja gris de la página verás:

```text
Página servida por WEB desde el contenedor  c05d7fa70a24
Datos servidos por la API desde el contenedor c05d7fa70a24   ← ¡el MISMO!
API_URL = http://localhost:5000
```

Mira los procesos dentro:

```bash
docker exec mono ps -eo pid,ppid,cmd
#  PID  PPID CMD
#    1     0 /bin/bash /start.sh
#    7     1 python /app/api/app.py
#    8     1 node /app/web/server.js
```

Funciona. Ahora vamos a ver sus problemas.

---

## 3. Los problemas, uno a uno (con experimentos)

### Problema 1 — Una imagen grande que mezcla dos mundos

```bash
docker images notas-mono
```

Unos **600 MB**. Contiene Python, pip, Node, npm, y todas las dependencias de
las dos apps. Consecuencias:

- Una vulnerabilidad en Node obliga a reconstruir y redesplegar **también** la API.
- No puedes usar la imagen base óptima para cada app (`node:22-alpine` para
  la web, `python:3.12-slim` para la API).
- Las versiones de Node las decide el `apt` de Debian, no tú.

(Apunta el tamaño: lo compararemos en el módulo 07.)

### Problema 2 — Los logs mezclados

```bash
docker logs mono
```

Los mensajes de `[start.sh]`, `[api]` y `[web]` salen **intercalados en un
único flujo**. Con dos apps es molesto; con tráfico real es ilegible. No
puedes pedir "solo los logs de la API" ni "solo los errores de la web".

### Problema 3 — Actualizar UNA app reinicia LAS DOS

Imagina que solo quieres cambiar el título de la web.

1. Asegúrate de tener notas creadas.
2. Edita [web/server.js](web/server.js): cambia `<h1>📝 Notas</h1>` por
   `<h1>📝 Mis notas</h1>`.
3. Despliega la nueva versión:

   ```bash
   docker build -t notas-mono:1.1 .
   docker rm -f mono
   docker run -d --name mono -p 8080:3000 notas-mono:1.1
   ```

4. Recarga la página: el título ha cambiado... **y las notas han desaparecido**.

Para actualizar la web has tenido que reiniciar también la API, que guardaba
las notas en memoria. En el mundo real: cada despliegue de la web provoca una
caída de la API (y de todo lo que dependa de ella).

### Problema 4 — Si una app muere, ¿qué hacemos con la otra?

Arranca con una política de reinicio y simula que la API **se cuelga** (la
matamos con `kill -9`):

```bash
docker rm -f mono
docker run -d --name mono --restart unless-stopped -p 8080:3000 notas-mono:1.1
curl -s -X POST -d 'texto=antes del fallo' localhost:8080/notas -o /dev/null

docker exec mono sh -c 'kill -9 $(pgrep -f app.py)'   # "crash" de la API
sleep 3
docker ps --filter name=mono                    # Up 2 seconds   ← se ha reiniciado ENTERO
docker inspect -f '{{.RestartCount}}' mono      # 1
docker logs mono | grep start.sh
# [start.sh] Uno de los procesos ha terminado (código 137). Paro el otro y salgo.
```

La WEB estaba perfecta, pero se ha reiniciado igualmente porque Docker solo
sabe reiniciar **contenedores**, no procesos sueltos dentro de ellos.

Y la alternativa es peor. Muchos `start.sh` de la vida real son así:

```bash
python app.py &
node server.js          # sin wait -n ni trap
```

Con ese script, si la API muere **el contenedor sigue "Up"** (porque el proceso
principal, node, vive), Docker no se entera, no lo reinicia, y tienes una web
que muestra errores indefinidamente. Un contenedor *medio muerto* es el peor
estado posible: parece sano y no lo está.

### Problema 5 — No se puede escalar por separado

La API recibe mucha carga y quieres **3 copias de la API**. Con este diseño
solo puedes arrancar 3 contenedores `mono`... que traen 3 WEBs que no
necesitas, cada una hablando con *su* API por `localhost`. No hay forma de
escalar una pieza sin la otra.

### Problema 6 — Señales y PID 1: complejidad que no te toca

`docker stop` envía SIGTERM **solo al PID 1**. Aquí el PID 1 es `start.sh`,
así que el script tiene que reenviar la señal a los hijos (`trap`), esperar a
que terminen (`wait`), propagar códigos de salida... Todo ese código existe
**solo** porque hay dos procesos. Con un proceso por contenedor, Docker lo
hace por ti.

### Problema 7 — Recursos y salud compartidos

- `--memory 256m` limita **la suma** de las dos apps. Si la web tiene una fuga
  de memoria, el kernel mata el contenedor y **se lleva por delante a la API**.
- `docker stats` te da el consumo **conjunto**: no sabes cuál de las dos gasta.
- Un `HEALTHCHECK` solo puede comprobar una cosa: ¿miras la web o la API?

### Problema 8 — Seguridad

Las dos apps comparten sistema de ficheros, usuario y red. Si alguien explota
un fallo de la web, tiene acceso directo al código, configuración y secretos
de la API.

---

## 4. Resumen

| Aspecto | 2 apps en 1 contenedor | 1 app por contenedor |
|---------|-----------------------|---------------------|
| Imagen | Una, grande, mezclada | Una por app, pequeña y especializada |
| Logs | Mezclados | Separados (`docker logs api`) |
| Desplegar una app | Reinicia las dos | Solo la que cambia |
| Si una falla | Se reinician las dos (o peor: medio-muerto) | Docker reinicia solo la que falla |
| Escalar | Todo o nada | Cada pieza por separado |
| Señales/PID 1 | Script casero | Docker lo gestiona |
| Recursos / salud | Compartidos | Por app |
| Seguridad | Todo junto | Aislado |

---

## 5. ¿Nunca es aceptable?

A veces sí, con criterio:

- Procesos **íntimamente acoplados** que no tienen sentido por separado
  (p. ej. imágenes antiguas de `nginx + php-fpm`).
- Imágenes de **desarrollo** o demos donde la comodidad pesa más.
- Software heredado que no se puede modificar.

Si lo haces, usa un gestor de procesos de verdad (`supervisord`, `s6-overlay`,
`tini`) en lugar de un `start.sh` casero.

> 🧠 En Kubernetes existe el concepto de **Pod**: un grupo de contenedores que
> se despliegan juntos y comparten red (`localhost`). Es la forma "correcta" de
> tener piezas muy acopladas: siguen siendo contenedores separados, con su
> imagen, logs y reinicios propios, pero viajan juntos.

---

## 6. ✍️ Ejercicios

**Ejercicio 1.** Con el contenedor `mono` en marcha, demuestra que la API está
accesible desde **dentro** del contenedor en `localhost:5000`, pero no desde tu
Ubuntu. Después arráncalo publicando **también** el 5000 y vuelve a probar.

<details><summary>Ver solución</summary>

```bash
docker exec mono python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/api/notas').read().decode())"
curl localhost:5000/api/notas            # ❌ no publicado
docker rm -f mono
docker run -d --name mono -p 8080:3000 -p 5000:5000 notas-mono:1.1
curl localhost:5000/api/notas            # ✅
```

</details>

**Ejercicio 2.** Usa `docker exec` para matar el proceso de la **web** con
`kill -9` (sin `--restart`). ¿En qué estado queda el contenedor? ¿Qué código de
salida tiene? ¿Por qué?

<details><summary>Ver solución</summary>

```bash
docker rm -f mono; docker run -d --name mono -p 8080:3000 notas-mono:1.1
docker exec mono sh -c 'kill -9 $(pgrep -f server.js)'
docker ps -a --filter name=mono          # Exited (137)
```

`wait -n` detecta que la web terminó con 137 (128+9, SIGKILL); el script mata
la API y sale con ese mismo código. Como no hay política de reinicio, se queda
parado. **Se cayó toda la aplicación por el fallo de una parte.**

</details>

**Ejercicio 3 (reflexión).** Antes de pasar al módulo 07, apunta en un papel:
para separar estas dos apps en dos contenedores, ¿qué cosas concretas habría que
cambiar? Pista: piensa en `localhost`, en el Dockerfile y en cómo arrancar.

<details><summary>Ver solución</summary>

1. Un **Dockerfile por app**, cada uno con su imagen base.
2. Eliminar `start.sh`: cada contenedor ejecuta directamente su app.
3. La web ya no puede usar `localhost:5000` → hay que darle la dirección de la
   API por **variable de entorno** (`API_URL=http://api:5000`).
4. Una **red** común para que se encuentren por nombre.
5. Publicar solo el puerto de la web.

Es justo lo que hacemos en el siguiente módulo.

</details>

### Limpieza del módulo

```bash
docker rm -f mono
docker rmi notas-mono:1.0 notas-mono:1.1
# Si modificaste web/server.js, puedes deshacer el cambio con: git checkout web/server.js
```

---

➡️ Siguiente: [07 · Separar en dos contenedores](../07-separar-en-dos-contenedores/README.md)
