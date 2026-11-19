# 03 · Imágenes propias y Dockerfile

**Objetivo:** construir tus propias imágenes, entender qué hace cada instrucción
del Dockerfile, aprovechar la caché de capas y publicar una imagen en Docker Hub.

```text
03-imagenes-y-dockerfile/
├── ejemplo/
│   ├── app.py               ← app Flask mínima
│   ├── requirements.txt
│   ├── Dockerfile           ← comentado línea a línea
│   ├── Dockerfile.mal-orden ← para ver el efecto de la caché
│   └── .dockerignore
└── ejemplo-entrypoint/
    └── Dockerfile           ← CMD vs ENTRYPOINT
```

---

## 1. Qué es un Dockerfile

Un fichero de texto con **instrucciones** que Docker ejecuta en orden para
fabricar una imagen. Es la **receta**: reproducible, versionable en git y
legible por cualquiera.

```text
Dockerfile + contexto ──docker build──▶ imagen ──docker run──▶ contenedor
```

> 🧠 **El contexto de build** es la carpeta que le pasas a `docker build`
> (normalmente `.`). Docker empaqueta esa carpeta y se la envía al motor. Las
> instrucciones `COPY` solo pueden copiar ficheros **de dentro del contexto**.
> El fichero `.dockerignore` excluye cosas del contexto (como `.gitignore`).

---

## 2. Las instrucciones

| Instrucción | Cuándo actúa | Qué hace |
|-------------|--------------|----------|
| `FROM imagen:tag` | build | Imagen de partida. Siempre la primera |
| `WORKDIR /ruta` | build | Carpeta de trabajo (la crea si no existe). Evita `RUN cd ...` |
| `COPY origen destino` | build | Copia ficheros del contexto a la imagen |
| `ADD origen destino` | build | Como COPY pero además descomprime `.tar` y acepta URLs. **Usa COPY** salvo que necesites eso |
| `RUN comando` | build | Ejecuta un comando y guarda el resultado como capa (instalar paquetes...) |
| `ENV CLAVE=valor` | build **y** ejecución | Variable de entorno que existe también en el contenedor |
| `ARG CLAVE=valor` | **solo** build | Variable para la construcción (`--build-arg`). No existe en el contenedor |
| `EXPOSE 5000` | (documentación) | Indica el puerto de la app. **No publica nada** |
| `USER nombre` | build y ejecución | Usuario con el que se ejecutan las instrucciones siguientes y el contenedor |
| `VOLUME /ruta` | ejecución | Declara una carpeta para datos (crea un volumen anónimo) |
| `LABEL clave=valor` | (metadatos) | Información: autor, versión, descripción |
| `HEALTHCHECK CMD ...` | ejecución | Comando para comprobar si la app está sana (módulo 10) |
| `CMD [...]` | **ejecución** | Comando por defecto al arrancar el contenedor |
| `ENTRYPOINT [...]` | **ejecución** | Programa que siempre se ejecuta; `CMD` pasa a ser sus argumentos |

> ⚠️ **Confusión típica:** `RUN` se ejecuta **al construir** la imagen (una vez).
> `CMD` se ejecuta **al arrancar** cada contenedor. `RUN python app.py` dejaría
> el build colgado para siempre.

---

## 3. Construir y ejecutar el ejemplo

Abre [ejemplo/Dockerfile](ejemplo/Dockerfile) y léelo entero: cada línea está
comentada.

```bash
cd 03-imagenes-y-dockerfile/ejemplo
docker build -t saludo:1.0 .
```

- `-t saludo:1.0` → nombre (`saludo`) y etiqueta (`1.0`) de la imagen.
- `.` → el contexto: la carpeta actual. Busca `Dockerfile` en ella.

Verás cada paso numerado: `[1/5] FROM ...`, `[2/5] WORKDIR /app`... Cada
paso que modifica el sistema de ficheros es una **capa**.

```bash
docker images saludo                         # tu imagen, con su tamaño
docker image history saludo:1.0              # sus capas (las de arriba son las tuyas)
docker run -d --name saludo -p 5000:5000 saludo:1.0
curl localhost:5000                          # Hola desde el contenedor 3f9a... (versión 1.0)
docker rm -f saludo
```

### Configurar con variables de entorno

```bash
docker run --rm -d --name saludo -p 5000:5000 -e SALUDO="Buenos días" saludo:1.0
curl localhost:5000                          # Buenos días desde el contenedor ...
docker rm -f saludo
```

La **misma imagen** se comporta distinto según la configuración que le des al
arrancar. Este principio es la base de los módulos 07-09.

### ARG: parámetros de construcción

```bash
docker build -t saludo:2.0 --build-arg VERSION=2.0 .
docker run --rm saludo:2.0 printenv APP_VERSION     # 2.0
```

`ARG VERSION` solo existía durante el build; lo copiamos a `ENV APP_VERSION`
para que la app lo vea al ejecutarse.

> 🧠 Fíjate en el último comando: `docker run ... saludo:2.0 printenv APP_VERSION`.
> Lo que pones detrás del nombre de la imagen **sustituye al `CMD`**. En vez de
> arrancar la app, el contenedor ejecuta `printenv` y termina.

---

## 4. La caché de capas (importantísimo)

Docker guarda cada capa construida. En el siguiente build, para cada
instrucción se pregunta: *"¿ya tengo una capa hecha con esta misma instrucción,
encima de esta misma capa anterior y con los mismos ficheros?"*. Si sí, la
reutiliza (`CACHED`) y no la vuelve a ejecutar.

**Regla:** en cuanto una capa cambia, **todas las de debajo se rehacen**.

### 🧪 Experimento: buen orden vs mal orden

1. Cambia algo en `app.py` (por ejemplo, el texto del saludo) y reconstruye:

   ```bash
   docker build -t saludo:1.1 .
   ```

   ```text
   [2/5] WORKDIR /app                         CACHED
   [3/5] COPY requirements.txt .              CACHED
   [4/5] RUN pip install -r requirements.txt  CACHED   ← ¡no reinstala!
   [5/5] COPY . .                                      ← solo esto se rehace
   ```

2. Ahora con el Dockerfile mal ordenado. Constrúyelo dos veces cambiando
   `app.py` entre medias:

   ```bash
   docker build -t saludo:mal -f Dockerfile.mal-orden .
   # cambia app.py otra vez
   docker build -t saludo:mal -f Dockerfile.mal-orden .
   ```

   `COPY . .` va **antes** de `pip install`: como `app.py` cambió, esa capa
   cambia... y `pip install` **se ejecuta otra vez**. Con 3 librerías no se
   nota; con 200 librerías son minutos en cada build.

> ✅ **Orden correcto:** lo que cambia **poco** arriba (sistema, dependencias),
> lo que cambia **mucho** abajo (tu código).

```dockerfile
COPY requirements.txt .      # (o package.json + package-lock.json en Node)
RUN pip install -r requirements.txt
COPY . .
```

Forzar un build sin caché: `docker build --no-cache -t saludo:1.0 .`

---

## 5. `.dockerignore`

Sin él, `COPY . .` copiaría **todo**: `.git`, `node_modules` de tu máquina,
`.env` con contraseñas, `__pycache__`... Mira [ejemplo/.dockerignore](ejemplo/.dockerignore).

Ventajas:

- builds más rápidos (contexto más pequeño),
- imágenes más pequeñas,
- no metes secretos sin querer,
- no invalidas la caché por ficheros que no importan.

---

## 6. `CMD` vs `ENTRYPOINT`

| | `CMD` | `ENTRYPOINT` |
|---|---|---|
| Qué es | Comando **por defecto** | Programa **fijo** |
| `docker run imagen otra cosa` | `otra cosa` **sustituye** al CMD | `otra cosa` se **añade como argumentos** |
| Uso típico | Apps normales | Imágenes que son "una herramienta" |

Juntos: `ENTRYPOINT` es el programa y `CMD` sus argumentos por defecto.

```bash
cd ../ejemplo-entrypoint
cat Dockerfile
docker build -t ping-demo .
docker run --rm ping-demo              # ping -c 3 localhost
docker run --rm ping-demo 8.8.8.8      # ping -c 3 8.8.8.8   (sustituye solo al CMD)
docker run --rm --entrypoint echo ping-demo hola   # sustituir el ENTRYPOINT: echo hola
```

### Forma exec vs forma shell

```dockerfile
CMD ["python", "app.py"]    # ✅ forma EXEC (JSON): python es el proceso principal (PID 1)
CMD python app.py           # ⚠️ forma SHELL: se ejecuta /bin/sh -c "python app.py"
```

Con la forma shell, el proceso principal puede acabar siendo `sh` en lugar de
tu app, y `sh` **no reenvía las señales**: `docker stop` no consigue parar
tu app con educación. **Usa siempre la forma exec.** Lo demostramos en el
módulo 10.

---

## 7. Etiquetas y versiones

```bash
docker tag saludo:1.0 saludo:latest    # una imagen puede tener varias etiquetas
docker images saludo                   # mismo IMAGE ID para 1.0 y latest
```

Buenas prácticas:

- Etiqueta con versiones (`1.0`, `1.1`, `2.0`) o con el commit de git (`saludo:3f9a1c2`).
- En el `FROM`, fija versión: `python:3.12-slim`, **no** `python` ni `python:latest`.
- Nunca reutilices una etiqueta de versión para otra cosa distinta.

---

## 8. Publicar en Docker Hub

1. Crea una cuenta gratis en [hub.docker.com](https://hub.docker.com).
2. Inicia sesión desde la terminal (mejor con un *Access Token*: Account
   Settings → Personal access tokens):

   ```bash
   docker login -u TU_USUARIO
   ```

3. La imagen debe llamarse `TU_USUARIO/nombre:tag`:

   ```bash
   docker tag saludo:1.0 TU_USUARIO/saludo:1.0
   docker push TU_USUARIO/saludo:1.0
   ```

4. Ahora, desde **cualquier** máquina con Docker:

   ```bash
   docker run -p 5000:5000 TU_USUARIO/saludo:1.0
   ```

> ⚠️ Los repositorios gratuitos de Docker Hub son **públicos**: no subas
> imágenes con contraseñas o código privado dentro.

---

## 9. ¿Y `docker commit`?

Existe `docker commit <contenedor> <imagen>`, que convierte un contenedor
modificado a mano en una imagen. **Evítalo**: nadie sabe qué se hizo dentro, no
se puede reproducir ni revisar. El Dockerfile es la fuente de la verdad.

---

## 10. ✍️ Ejercicios

**Ejercicio 1.** Sin tocar el Dockerfile, arranca la imagen `saludo:1.0` en el
puerto **7000** de tu máquina con el saludo `"Qué pasa"`.

<details><summary>Ver solución</summary>

```bash
docker run --rm -d --name ej1 -p 7000:5000 -e SALUDO="Qué pasa" saludo:1.0
curl localhost:7000
docker rm -f ej1
```

El puerto **interno** sigue siendo 5000 (es donde escucha la app); solo cambia
el puerto publicado en tu máquina.

</details>

**Ejercicio 2.** Escribe un Dockerfile desde cero para una imagen basada en
`alpine:3.20` que, al arrancar, muestre la fecha y el hostname. Constrúyela
como `quien-soy:1.0`.

<details><summary>Ver solución</summary>

```dockerfile
FROM alpine:3.20
CMD ["sh", "-c", "echo \"Son las $(date) y soy $(hostname)\""]
```

```bash
mkdir /tmp/quien && cd /tmp/quien   # crea ahí el Dockerfile
docker build -t quien-soy:1.0 .
docker run --rm quien-soy:1.0
```

(Aquí usamos `sh -c` explícitamente en forma exec porque necesitamos que una
shell expanda `$(date)`.)

</details>

**Ejercicio 3.** Modifica el Dockerfile del ejemplo para que instale además el
paquete `curl` del sistema (con `apt-get`) en la capa correcta, limpiando la
caché de apt para no engordar la imagen. Compara el tamaño antes y después.

<details><summary>Ver solución</summary>

Justo después de `FROM`, antes de copiar nada (cambia muy poco):

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*
```

Todo en **un solo `RUN`**: si `rm -rf` fuera en otro `RUN`, la caché de apt ya
habría quedado grabada en la capa anterior y la imagen no adelgazaría (las
capas solo suman, nunca restan).

```bash
docker build -t saludo:curl .
docker images saludo
```

</details>

**Ejercicio 4.** ¿Por qué esto es mala idea? ¿Qué verá cualquiera que tenga la imagen?

```dockerfile
ENV DB_PASSWORD=supersecreta
```

<details><summary>Ver solución</summary>

Queda grabado en la imagen. Cualquiera puede verlo con
`docker image inspect` o `docker history`, y también desde dentro del contenedor
con `env`. Los secretos se pasan **al arrancar** (`-e`, ficheros `.env` que no
se suben a git, o *secrets* de Docker/Compose), nunca dentro de la imagen.

</details>

### Limpieza del módulo

```bash
docker rmi saludo:1.0 saludo:1.1 saludo:2.0 saludo:mal saludo:latest saludo:curl ping-demo quien-soy:1.0 2>/dev/null
docker image prune -f
```

---

➡️ Siguiente: [04 · Volúmenes](../04-volumenes/README.md)
