# ✅ MULTI-ETAPA (multi-stage build)
#
# Etapa 1 ("compilador"): imagen grande con todas las herramientas -> compila.
# Etapa 2 (final):        imagen vacía ("scratch") -> solo copiamos el binario.
#
# Solo la ÚLTIMA etapa acaba en la imagen final. Las anteriores se descartan.

# ---------- Etapa 1: compilar ----------
FROM golang:1.23 AS compilador
WORKDIR /src
COPY go.mod ./
COPY main.go ./
# CGO_ENABLED=0 -> binario estático (no depende de librerías del sistema)
# -ldflags="-s -w" -> quita símbolos de depuración (binario más pequeño)
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-s -w" -o /hola .

# ---------- Etapa 2: imagen final ----------
# "scratch" es una imagen VACÍA: ni shell, ni ls, ni nada. Solo nuestro binario.
FROM scratch
COPY --from=compilador /hola /hola
# Usuario sin privilegios (en scratch no hay /etc/passwd, así que usamos un UID)
USER 10001
EXPOSE 8080
ENTRYPOINT ["/hola"]
