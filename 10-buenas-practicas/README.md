# 10 · Buenas prácticas: imágenes pequeñas, seguras y que se paran bien

**Objetivo:** pasar de "funciona" a "está bien hecho". Tres experimentos
prácticos (multi-stage, señales, imagen de producción) y una lista de
comprobación que podrás aplicar a cualquier Dockerfile.

```text
10-buenas-practicas/
├── multi-stage/        ← Go: de 1,3 GB a 7 MB con la misma app
├── senales/            ← PID 1, SIGTERM y por qué docker stop a veces tarda
└── api-produccion/     ← la API del módulo 07 con un Dockerfile de producción
```

---

## 1. Multi-stage builds: compilar en una imagen, ejecutar en otra

Muchas apps necesitan herramientas **para construirse** (compiladores, `npm`,
`pip`, cabeceras de C...) que **no hacen falta para ejecutarse**. Si todo va en
la misma imagen, la imagen final carga con todo eso: más tamaño, más tiempo de
descarga y más vulnerabilidades potenciales.

Un **build multi-etapa** tiene varios `FROM`. Cada uno empieza una etapa nueva;
con `COPY --from=etapa` te llevas solo lo que necesitas. **Solo la última etapa
forma la imagen final.**

```dockerfile
FROM golang:1.23 AS compilador          # etapa 1: herramientas completas
WORKDIR /src
COPY . .
RUN CGO_ENABLED=0 go build -o /hola .

FROM scratch                            # etapa 2: imagen VACÍA
COPY --from=compilador /hola /hola      # solo el binario
ENTRYPOINT ["/hola"]
```

### 🧪 Experimento: mismo programa, dos Dockerfiles

```bash
cd 10-buenas-practicas/multi-stage
docker build -t hola:una-etapa -f Dockerfile.una-etapa .
docker build -t hola:multi .
docker images hola
```

```text
REPOSITORY   TAG         SIZE
hola         una-etapa   1.34GB     ← compilador de Go + fuentes + cachés
hola         multi       7.3MB      ← solo el binario
```

Funcionan igual:

```bash
docker run -d --name hola -p 8081:8080 hola:multi
curl localhost:8081               # ¡Hola desde Go! Contenedor: ...
docker exec hola sh               # ❌ no hay shell: en scratch NO hay NADA más
docker rm -f hola
```

Que no haya shell es **bueno** para seguridad (un atacante no tiene
herramientas), aunque complica depurar. Alternativas intermedias: imágenes
*distroless* (`gcr.io/distroless/static`) o `alpine`.

> 🧠 El multi-stage no es solo para lenguajes compilados. En Node se usa para
> compilar el frontend (React, Vue...) con `npm run build` y servir solo los
> ficheros estáticos con nginx. En Python, para instalar dependencias con
> compiladores en una etapa y copiar solo el entorno virtual (lo hacemos en
> `api-produccion`).

---

## 2. PID 1 y las señales: por qué `docker stop` a veces tarda

### Cómo se para un contenedor

```text
docker stop  ──SIGTERM──▶ PID 1 del contenedor     "por favor, termina"
                 │
                 │   ...espera el periodo de gracia (configurable con -t)...
                 ▼
             ──SIGKILL──▶ PID 1                     "muere YA" (no se puede ignorar)
```

Una app bien hecha, al recibir **SIGTERM**, termina lo que está haciendo,
cierra conexiones, guarda lo pendiente y sale. Si no lo atiende, tras el
periodo de gracia Docker la mata con **SIGKILL**: se pueden perder datos o
dejar peticiones a medias.

### La trampa del PID 1

En Linux, el proceso con **PID 1** es especial: **el kernel no le aplica las
acciones por defecto de las señales**. Para un proceso normal, la acción por
defecto de SIGTERM es "terminar". Para el PID 1, si no ha instalado un
*manejador*, la señal **se ignora**.

Y en un contenedor, **tu app es el PID 1**.

### 🧪 Experimento: cuatro formas de arrancar el mismo programa

[senales/app.py](senales/app.py) solo espera. Con `MANEJAR_SIGTERM=1` instala
un manejador de SIGTERM.

```bash
cd ../senales
docker build -t senales .
docker build -t senales:shell -f Dockerfile.shell .

docker run -d --name s1 senales                           # A) sin manejador
docker run -d --name s2 -e MANEJAR_SIGTERM=1 senales      # B) con manejador
docker run -d --name s3 --init senales                    # C) sin manejador, pero con --init
docker run -d --name s4 -e MANEJAR_SIGTERM=1 senales:shell  # D) con manejador, pero CMD en forma shell

for c in s1 s2 s3 s4; do
  echo "== $c"; time docker stop -t 10 $c
  docker inspect -f 'Código de salida: {{.State.ExitCode}}' $c
done
```

| | Cómo | `docker stop` tarda | Código | Por qué |
|---|---|---|---|---|
| A | Python es PID 1, sin manejador | **~10 s** | **137** | SIGTERM ignorado (es PID 1) → SIGKILL |
| B | Python es PID 1, con manejador | < 1 s | 0 | Captura SIGTERM y sale limpio |
| C | `--init`: `tini` es PID 1, Python es hijo | < 1 s | 143 | tini reenvía SIGTERM; Python ya no es PID 1, aplica la acción por defecto |
| D | Forma shell: `sh` es PID 1 | **~10 s** | **137** | `sh` no reenvía la señal; Python nunca se entera |

Para ver el caso D:

```bash
docker run -d --name s5 senales:shell
docker top s5           # PID 1 (en el contenedor) = /bin/sh -c "echo ... ; python ..."; python es su hijo
docker rm -f s5 s1 s2 s3 s4
```

> ✅ **Reglas:**
> 1. `CMD` y `ENTRYPOINT` siempre en **forma exec** (`["python", "app.py"]`).
> 2. Tu app debe **gestionar SIGTERM** (los servidores de producción como
>    gunicorn, uvicorn, nginx o la mayoría de frameworks ya lo hacen).
> 3. Si no puedes controlar eso, usa **`--init`** (o `init: true` en Compose).
> 4. Si usas un script de arranque, termina con **`exec tu-app`** para que la
>    app sustituya a la shell como PID 1.
>
> Por eso la API y la web del curso capturan SIGTERM (mira el final de
> `app.py` y `server.js`), y por eso el `start.sh` del módulo 06 necesitaba un
> `trap`.

### El patrón del script de arranque con `exec`

```bash
#!/bin/sh
# entrypoint.sh: preparar cosas antes de arrancar la app
echo "Esperando configuración..."
./migrar-base-de-datos.sh
exec python app.py "$@"     # exec: python REEMPLAZA a sh y pasa a ser el PID 1
```

---

## 3. Una imagen de producción, pieza a pieza

Compara [api-produccion/Dockerfile](api-produccion/Dockerfile) con
[el del módulo 07](../07-separar-en-dos-contenedores/api/Dockerfile). Mismo
`app.py`, pero:

| Mejora | Cómo | Por qué |
|--------|------|---------|
| Versión fijada | `FROM python:3.12-slim` | Builds reproducibles |
| Multi-stage | Etapa `dependencias` crea un venv; la final solo lo copia | Sin pip, cachés ni herramientas de build |
| Usuario sin privilegios | `useradd ... app` + `USER app` | Si atacan la app, no son root |
| `--chown` | `COPY --chown=app:app app.py .` | Los ficheros pertenecen al usuario correcto |
| Servidor de producción | `gunicorn` en vez de `app.run()` | Rendimiento, concurrencia, SIGTERM bien gestionado |
| Healthcheck | `HEALTHCHECK CMD python -c ...` | Docker sabe si la app responde, no solo si el proceso vive |
| Logs a stdout | `--access-logfile -`, `PYTHONUNBUFFERED=1` | `docker logs` funciona |
| Metadatos | `LABEL org.opencontainers.image.*` | Saber qué es y de dónde viene la imagen |

```bash
cd ../api-produccion
docker build -t notas-api:prod .
docker run -d --name prod -p 5000:5000 notas-api:prod
sleep 12
docker ps --filter name=prod          # STATUS: Up 12 seconds (healthy)   ← el healthcheck
docker exec prod whoami               # app   (no root)
curl localhost:5000/health
time docker stop prod                 # rápido: gunicorn atiende SIGTERM
docker logs prod | tail -3            # Handling signal: term ... Shutting down: Master
docker rm prod
```

Consulta el historial de un healthcheck:

```bash
docker inspect -f '{{json .State.Health}}' prod | jq
```

> ⚠️ **Fíjate en `--workers 1`.** gunicorn puede arrancar varios procesos para
> aprovechar varias CPUs, pero esta versión de la API guarda las notas **en
> memoria**: con 2 workers habría 2 listas distintas (el mismo problema que al
> escalar en el módulo 08). Otra razón más para sacar el estado a una BD. En el
> proyecto final, con PostgreSQL, usamos 2 workers sin problema.

---

## 4. Seguridad: lo esencial

**Ejecuta como usuario no-root.** Por defecto los contenedores corren como
root. Aunque está aislado, un fallo en el kernel o una mala configuración
(un volumen del host montado) puede convertir "root en el contenedor" en "root
en tu máquina".

```bash
docker run --rm python:3.12-slim whoami          # root
docker run --rm notas-api:prod whoami            # app
docker run --rm -u 1000:1000 alpine id           # forzar un usuario al arrancar
```

**No metas secretos en la imagen.** Ni con `ENV`, ni con `ARG`, ni con `COPY .env`.

```bash
# 🧪 Lo que se graba en una imagen, se puede leer
docker build -t secreto - <<'EOF'
FROM alpine:3.20
ARG TOKEN=ghp_mi_token_super_secreto
RUN echo "usando token" > /dev/null
EOF
docker history --no-trunc secreto | grep -o 'TOKEN=[^ ]*'     # ¡ahí está!
docker rmi secreto
```

Los secretos se pasan **al arrancar** (variables de entorno desde `.env`,
ficheros montados, Docker secrets) o, si se necesitan durante el build, con
`RUN --mount=type=secret` de BuildKit.

**Reduce la superficie de ataque:**

- Imágenes base pequeñas (`slim`, `alpine`, `distroless`): menos paquetes = menos vulnerabilidades.
- Sistema de ficheros de solo lectura: `docker run --read-only` (`read_only: true` en Compose) + `--tmpfs /tmp` si necesita escribir.
- Quitar capacidades del kernel: `--cap-drop ALL` (y añadir solo las necesarias con `--cap-add`).
- No uses `--privileged` salvo que sepas exactamente por qué.
- No montes `/var/run/docker.sock` en un contenedor: es darle control total de Docker (= root en el host).

**Escanea tus imágenes** en busca de vulnerabilidades conocidas:

```bash
docker scout quickview notas-api:prod      # si tienes Docker Scout (requiere cuenta de Docker Hub)
# o con Trivy, sin instalar nada:
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock aquasec/trivy image notas-api:prod
```

---

## 5. Recursos, reinicios y logs

```bash
docker run -d --name limitado \
  --memory 256m --cpus 0.5 \
  --restart unless-stopped \
  --log-opt max-size=10m --log-opt max-file=3 \
  notas-api:prod
docker stats --no-stream limitado
docker rm -f limitado
```

- `--memory 256m --cpus 0.5` → como máximo 256 MB de RAM y media CPU.
- `--restart unless-stopped` → reiniciar si falla (y cuando arranque Docker).
- `--log-opt ...` → rotación de logs: como mucho 3 ficheros de 10 MB.

> ⚠️ En bash no se puede poner un comentario `# ...` detrás de una `\` de
> continuación de línea: rompe el comando. Por eso las explicaciones van aparte.

| Política `--restart` | Comportamiento |
|----------------------|----------------|
| `no` (defecto) | Nunca reinicia |
| `on-failure[:N]` | Solo si sale con código ≠ 0 (máximo N intentos) |
| `unless-stopped` | Siempre, salvo que lo pararas tú a mano. **La más usada** |
| `always` | Siempre, incluso si lo paraste a mano (al reiniciar Docker vuelve) |

> ⚠️ **Los logs crecen sin límite por defecto.** El driver `json-file` guarda
> todo lo que la app escribe en `/var/lib/docker/containers/<id>/<id>-json.log`.
> Una app muy habladora puede llenar el disco. Configura la rotación por
> contenedor (como arriba) o para todo Docker en `/etc/docker/daemon.json`:
>
> ```json
> { "log-driver": "json-file", "log-opts": { "max-size": "10m", "max-file": "3" } }
> ```
>
> y `sudo systemctl restart docker`.

---

## 6. ✅ Lista de comprobación de un buen Dockerfile

- [ ] Imagen base **oficial**, **pequeña** y con **versión fijada**.
- [ ] Dependencias copiadas e instaladas **antes** que el código (caché).
- [ ] `.dockerignore` con `.git`, `node_modules`, `.env`, cachés...
- [ ] **Multi-stage** si hay pasos de compilación o herramientas de build.
- [ ] `apt-get update && apt-get install ... && rm -rf /var/lib/apt/lists/*` en **un único** `RUN`, con `--no-install-recommends`.
- [ ] **Usuario no-root** (`USER`).
- [ ] **Sin secretos** en la imagen.
- [ ] `CMD`/`ENTRYPOINT` en **forma exec**, y la app gestiona **SIGTERM**.
- [ ] La app escucha en **`0.0.0.0`** y escribe logs en **stdout/stderr**.
- [ ] La configuración llega por **variables de entorno**.
- [ ] **`HEALTHCHECK`** (en el Dockerfile o en Compose).
- [ ] Una **responsabilidad por contenedor**.
- [ ] Etiquetas de versión con significado (no solo `latest`).

---

## 7. ✍️ Ejercicios

**Ejercicio 1.** Aplica la lista de comprobación al
[Dockerfile de la web](../07-separar-en-dos-contenedores/web/Dockerfile) del
módulo 07: añade usuario no-root y un healthcheck. (Pista: la imagen
`node:22-alpine` ya trae un usuario `node`, y Alpine trae `wget`.)

<details><summary>Ver solución</summary>

```dockerfile
FROM node:22-alpine
ENV NODE_ENV=production
WORKDIR /app
COPY package*.json ./
RUN npm ci --omit=dev && npm cache clean --force
COPY . .
USER node
EXPOSE 3000
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/health > /dev/null || exit 1
CMD ["node", "server.js"]
```

Usamos `127.0.0.1` y no `localhost`: en Alpine `localhost` puede resolverse a
IPv6 (`::1`) y la app solo escucha en IPv4. La solución completa está en
`11-proyecto-final/solucion/web/Dockerfile`.

</details>

**Ejercicio 2.** Quita el manejador de SIGTERM de
[api-produccion/app.py](api-produccion/app.py)... ¿cambia algo al hacer
`docker stop`? ¿Por qué?

<details><summary>Ver solución</summary>

No cambia nada: con gunicorn, el PID 1 es el **proceso maestro de gunicorn**,
que ya gestiona SIGTERM por sí mismo. Además, el manejador de `app.py` solo se
instala dentro de `if __name__ == "__main__":`, que no se ejecuta cuando
gunicorn importa el módulo.

</details>

**Ejercicio 3.** Arranca `notas-api:prod` con un sistema de ficheros de solo
lectura y sin ninguna capacidad del kernel. ¿Funciona? ¿Qué necesitas añadir
si falla?

<details><summary>Ver solución</summary>

```bash
docker run -d --name ro --read-only --cap-drop ALL --tmpfs /tmp -p 5000:5000 notas-api:prod
curl localhost:5000/health
docker rm -f ro
```

Funciona. Pero prueba sin `--tmpfs /tmp`: el contenedor se para al instante y
`docker logs` dice `No usable temporary directory found`. gunicorn necesita un
directorio temporal escribible: `--tmpfs /tmp` (o `--worker-tmp-dir /dev/shm`)
se lo da en memoria. Como la app no usa puertos privilegiados (<1024) ni nada
especial, `--cap-drop ALL` no le afecta.

</details>

### Limpieza del módulo

```bash
docker rm -f s1 s2 s3 s4 s5 hola prod limitado ro 2>/dev/null
docker rmi hola:una-etapa hola:multi senales senales:shell notas-api:prod 2>/dev/null
```

---

➡️ Siguiente: [11 · Proyecto final](../11-proyecto-final/README.md)
