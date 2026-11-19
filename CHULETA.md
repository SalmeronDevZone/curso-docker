# 📋 Chuleta de Docker

Todos los comandos del curso en una página. `<c>` = nombre o ID de contenedor,
`<img>` = imagen, `<v>` = volumen, `<red>` = red.

---

## Contenedores

| Comando | Qué hace |
|---------|----------|
| `docker run <img>` | Crear y arrancar un contenedor |
| `docker run -d --name web -p 8080:80 <img>` | En segundo plano, con nombre y puerto publicado |
| `docker run -it --rm <img> sh` | Interactivo con shell, se borra al salir |
| `docker run -e VAR=valor --env-file .env <img>` | Variables de entorno |
| `docker run -v <v>:/ruta -v "$(pwd)":/app:ro <img>` | Volumen con nombre + bind mount de solo lectura |
| `docker run --network <red> <img>` | Conectar a una red |
| `docker run --restart unless-stopped <img>` | Reiniciar si falla |
| `docker run --memory 256m --cpus 0.5 <img>` | Limitar recursos |
| `docker run --init <img>` | Usar `tini` como PID 1 (señales) |
| `docker run --read-only --tmpfs /tmp <img>` | Sistema de ficheros de solo lectura |
| `docker run --rm --entrypoint sh -it <img>` | Entrar en una imagen saltándose su ENTRYPOINT |
| `docker ps` / `docker ps -a` | En marcha / todos |
| `docker ps -aq` | Solo IDs |
| `docker logs -f --tail 50 <c>` | Logs en directo |
| `docker exec -it <c> sh` | Shell dentro de un contenedor en marcha |
| `docker exec <c> comando` | Ejecutar un comando suelto |
| `docker stop <c>` / `docker start <c>` / `docker restart <c>` | Parar / arrancar / reiniciar |
| `docker stop -t 30 <c>` | Dar 30 s de gracia antes del SIGKILL |
| `docker kill <c>` | Parar a lo bruto (SIGKILL) |
| `docker rm <c>` / `docker rm -f <c>` | Borrar (parado) / parar y borrar |
| `docker inspect <c>` | Todo en JSON |
| `docker inspect -f '{{.State.ExitCode}}' <c>` | Un campo concreto |
| `docker top <c>` | Procesos |
| `docker stats` | Consumo de CPU/RAM en directo |
| `docker port <c>` | Puertos publicados |
| `docker cp <c>:/ruta .` / `docker cp fichero <c>:/ruta` | Copiar ficheros |
| `docker diff <c>` | Cambios en el sistema de ficheros |
| `docker update --restart unless-stopped <c>` | Cambiar política sin recrear |
| `docker events` | Eventos del motor en directo |

## Imágenes

| Comando | Qué hace |
|---------|----------|
| `docker build -t nombre:tag .` | Construir con el Dockerfile de la carpeta actual |
| `docker build -t nombre:tag -f Dockerfile.otro .` | Con otro Dockerfile |
| `docker build --build-arg VAR=valor -t ... .` | Pasar un ARG |
| `docker build --no-cache -t ... .` | Sin caché |
| `docker images` | Listar |
| `docker pull <img>` / `docker push <img>` | Descargar / subir |
| `docker tag <img> usuario/nombre:tag` | Añadir otra etiqueta |
| `docker image history <img>` | Capas |
| `docker image inspect <img>` | Metadatos (CMD, ENV, puertos...) |
| `docker rmi <img>` | Borrar |
| `docker login` | Iniciar sesión en Docker Hub |

## Volúmenes

| Comando | Qué hace |
|---------|----------|
| `docker volume create <v>` | Crear |
| `docker volume ls` | Listar |
| `docker volume inspect <v>` | Detalles (Mountpoint) |
| `docker volume rm <v>` | Borrar ⚠️ |
| `docker run --rm -v <v>:/o:ro -v "$(pwd)":/b alpine tar czf /b/backup.tgz -C /o .` | Backup de un volumen |

## Redes

| Comando | Qué hace |
|---------|----------|
| `docker network create <red>` | Crear red (con DNS por nombre) |
| `docker network ls` | Listar |
| `docker network inspect <red>` | Detalles y contenedores conectados |
| `docker network connect <red> <c>` / `disconnect` | Conectar / desconectar |
| `docker network rm <red>` | Borrar |
| `docker run --rm -it --network <red> nicolaka/netshoot` | Depurar la red |

## Limpieza

| Comando | Qué borra |
|---------|-----------|
| `docker system df` | (solo muestra el espacio usado) |
| `docker container prune` | Contenedores parados |
| `docker image prune` / `-a` | Imágenes colgantes / todas las no usadas |
| `docker volume prune` | Volúmenes anónimos sin usar ⚠️ |
| `docker network prune` | Redes sin usar |
| `docker builder prune` | Caché de construcción |
| `docker system prune` | Todo lo anterior salvo volúmenes e imágenes en uso |

## Docker Compose

| Comando | Qué hace |
|---------|----------|
| `docker compose up -d` | Crear/actualizar y arrancar todo |
| `docker compose up -d --build` | ...reconstruyendo imágenes |
| `docker compose up -d --scale api=3` | Varias réplicas de un servicio |
| `docker compose --profile debug up -d` | Incluir servicios de un perfil |
| `docker compose ps` | Estado |
| `docker compose logs -f [servicio]` | Logs |
| `docker compose exec <servicio> sh` | Shell dentro |
| `docker compose run --rm <servicio> comando` | Contenedor temporal del servicio |
| `docker compose restart <servicio>` | Reiniciar |
| `docker compose stop` / `start` | Parar / arrancar sin borrar |
| `docker compose down` | Borrar contenedores y red (conserva volúmenes) |
| `docker compose down -v` | ...y los volúmenes ⚠️ |
| `docker compose config` | Ver/validar el YAML resuelto |
| `docker compose -p nombre up -d` | Con otro nombre de proyecto |
| `docker compose -f a.yaml -f b.yaml up -d` | Combinar ficheros |

## Dockerfile

```dockerfile
FROM python:3.12-slim                 # imagen base (versión fijada)
ARG VERSION=1.0                       # variable solo de build
ENV APP_ENV=prod PYTHONUNBUFFERED=1   # variable en build y ejecución
WORKDIR /app                          # carpeta de trabajo
COPY requirements.txt .               # 1º dependencias (caché)
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                              # 2º código
RUN useradd --uid 10001 app
USER app                              # no-root
EXPOSE 5000                           # documentación del puerto
HEALTHCHECK CMD python -c "..."       # salud
CMD ["python", "app.py"]              # comando por defecto (forma exec)
```

```dockerfile
# Multi-stage
FROM golang:1.23 AS build
RUN go build -o /app .
FROM scratch
COPY --from=build /app /app
ENTRYPOINT ["/app"]
```

## compose.yaml

```yaml
name: miproyecto
services:
  web:
    build: ./web                     # o image: nginx:1.27-alpine
    image: miweb:1.0
    ports: ["8080:3000"]
    environment:
      API_URL: http://api:5000       # nombre del servicio = nombre DNS
    env_file: .env
    volumes:
      - datos:/var/lib/datos         # volumen con nombre
      - ./conf:/etc/conf:ro          # bind mount
    networks: [frontend]
    depends_on:
      api: { condition: service_healthy }
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://127.0.0.1:3000/health"]
      interval: 10s
      retries: 3
    restart: unless-stopped
    read_only: true
    tmpfs: [/tmp]
    deploy:
      resources:
        limits: { cpus: "0.5", memory: 256M }
    profiles: [debug]                # solo con --profile debug
volumes:
  datos: {}
networks:
  frontend: {}
  backend: { internal: true }
```

## Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | OK |
| 1-2 | Error de la app |
| 125 | Error de `docker run` |
| 126 | No ejecutable (permisos) |
| 127 | Comando no encontrado |
| 137 | SIGKILL (OOM, `docker kill`, no paró a tiempo) |
| 143 | SIGTERM no gestionado |
