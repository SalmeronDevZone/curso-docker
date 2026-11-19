# 05 · Redes: cómo se hablan los contenedores

**Objetivo:** entender cómo se conectan los contenedores entre sí y con el
exterior. Este módulo es la base para separar aplicaciones (módulo 07): dos
contenedores que no se "ven" no pueden colaborar.

---

## 1. Lo que pasa por debajo

Gracias al *namespace* de red, cada contenedor tiene su **propia pila de red**:
sus interfaces, su IP, sus puertos, su tabla de rutas. Docker lo conecta a un
**switch virtual** (una red *bridge*) dentro de tu Ubuntu.

```text
  ┌────────────────────────────── TU UBUNTU ───────────────────────────────┐
  │                                                                        │
  │   enp0s3 (192.168.1.50) ◀── tu red real / internet                     │
  │        ▲                                                               │
  │        │ NAT (iptables)  +  -p 8080:80 (redirección de puertos)        │
  │        │                                                               │
  │   ┌────┴──────────── bridge "docker0" (172.17.0.1) ──────────────┐     │
  │   │                         (switch virtual)                     │     │
  │   └───────┬─────────────────────────┬──────────────────────┬─────┘     │
  │      ┌────┴────┐               ┌────┴────┐            ┌────┴────┐      │
  │      │ cont. A │               │ cont. B │            │ cont. C │      │
  │      │172.17.0.2│              │172.17.0.3│           │172.17.0.4│     │
  │      └─────────┘               └─────────┘            └─────────┘      │
  └────────────────────────────────────────────────────────────────────────┘
```

- Los contenedores de la misma red se comunican directamente por IP.
- Para **salir** a internet, Docker hace NAT (como tu router de casa).
- Para **entrar** desde fuera, hay que **publicar** puertos (`-p`).

```bash
ip addr show docker0          # el switch virtual en tu Ubuntu
docker network ls             # redes que existen: bridge, host, none
```

---

## 2. Tipos de red (drivers)

| Driver | Qué hace | Cuándo |
|--------|----------|--------|
| `bridge` (por defecto) | Red privada virtual en el host | **El 95 % de los casos** |
| `host` | El contenedor usa **directamente** la red del host (sin aislamiento) | Rendimiento extremo, herramientas de red |
| `none` | Sin red (solo `lo`) | Tareas que no deben tener red |
| `overlay` | Red que abarca **varias máquinas** | Docker Swarm (fuera de este curso) |
| `macvlan` | El contenedor aparece como un equipo más de tu red física | Casos especiales |

---

## 3. La red `bridge` por defecto vs una red creada por ti

Esta es **la** lección del módulo.

### 🧪 Experimento: en la red por defecto NO hay DNS

```bash
docker run -d --name a1 alpine sleep 1000
docker run -d --name a2 alpine sleep 1000

docker exec a1 ping -c 2 a2
# ping: bad address 'a2'   ← no sabe quién es "a2"

docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' a2   # p. ej. 172.17.0.3
docker exec a1 ping -c 2 172.17.0.3      # por IP sí funciona
```

Pero las IPs **cambian** cada vez que se recrea un contenedor. Depender de
ellas es frágil.

### 🧪 Experimento: en una red tuya SÍ hay DNS

```bash
docker network create mired
docker run -d --name b1 --network mired alpine sleep 1000
docker run -d --name b2 --network mired alpine sleep 1000

docker exec b1 ping -c 2 b2               # ✅ funciona por NOMBRE
docker exec b1 nslookup b2                # lo resuelve el DNS interno de Docker
docker exec b1 cat /etc/resolv.conf       # nameserver 127.0.0.11  ← el DNS de Docker
```

> 🧠 **Regla práctica:** crea **siempre** una red propia para tus contenedores
> (`docker network create`). En ella, cada contenedor es accesible por su
> **nombre** (y por sus alias). Docker Compose lo hace automáticamente por ti.

### Aislamiento entre redes

```bash
docker exec b1 ping -c 2 -W 1 a1         # ❌ bad address: b1 y a1 están en redes distintas
```

Contenedores en redes distintas **no se ven**. Esto es una herramienta de
seguridad: en el proyecto final la base de datos estará en una red a la que
la web no tiene acceso.

### Conectar un contenedor a varias redes

```bash
docker network connect mired a1          # ahora a1 está en "bridge" Y en "mired"
docker exec b1 ping -c 2 a1              # ✅
docker inspect -f '{{json .NetworkSettings.Networks}}' a1 | jq 'keys'   # ["bridge","mired"]
docker network disconnect mired a1
```

### Inspeccionar una red

```bash
docker network inspect mired             # subred, gateway y contenedores conectados
```

---

## 4. Publicar puertos: del exterior al contenedor

Por defecto, **nada de fuera** puede llegar a un contenedor. `-p` crea una
redirección:

```text
-p 8080:80
   │    └── puerto DENTRO del contenedor (donde escucha la app)
   └─────── puerto en TU UBUNTU (el que usas en el navegador)
```

| Sintaxis | Significado |
|----------|-------------|
| `-p 8080:80` | Puerto 8080 de **todas** las interfaces del host → 80 del contenedor |
| `-p 127.0.0.1:8080:80` | Solo accesible **desde el propio host** (no desde otros equipos) |
| `-p 80` | Puerto **aleatorio** del host → 80 del contenedor (míralo con `docker port`) |
| `-P` | Publica todos los puertos del `EXPOSE` en puertos aleatorios |
| `-p 5353:53/udp` | Puerto UDP |

```bash
docker run -d --name w1 -p 8080:80 nginx:1.27-alpine
docker run -d --name w2 -p 8081:80 nginx:1.27-alpine   # dos nginx, ambos en su puerto 80 interno
docker run -d --name w3 -P nginx:1.27-alpine
docker port w3                                         # 80/tcp -> 0.0.0.0:32768 (por ejemplo)
docker run -d --name w4 -p 8080:80 nginx:1.27-alpine   # ❌ port is already allocated
```

> 🧠 Cada contenedor tiene **sus propios puertos**: varios contenedores pueden
> escuchar en su puerto 80 sin conflicto. Lo que no puede repetirse es el
> puerto **del host**.

### `EXPOSE` no publica nada

`EXPOSE 80` en un Dockerfile es **documentación**: dice "esta app escucha en el
80". Solo tiene efecto práctico con `-P`. Para publicar, siempre `-p`.

### ⚠️ Docker y el cortafuegos UFW

En Ubuntu, Docker añade sus propias reglas de `iptables` y **los puertos
publicados con `-p` se saltan UFW**. Aunque tengas `ufw deny 8080`, si haces
`-p 8080:80` el puerto estará abierto al exterior. Para servicios que solo
deben verse desde la propia máquina, publica en `127.0.0.1:` o no los
publiques (deja que se comuniquen por la red interna).

---

## 5. La trampa de `127.0.0.1` DENTRO del contenedor

Una app que escucha en `127.0.0.1` (localhost) **solo acepta conexiones desde
dentro de su propio contenedor**: ni otros contenedores ni el `-p` llegan a ella.

### 🧪 Experimento

```bash
# Servidor que escucha SOLO en 127.0.0.1 dentro del contenedor
docker run -d --name solo-local -p 8000:8000 python:3.12-slim \
  python -m http.server 8000 --bind 127.0.0.1
curl localhost:8000          # ❌ curl: (52) Empty reply from server  (o "connection reset")

# El mismo servidor escuchando en TODAS las interfaces (0.0.0.0)
docker run -d --name todos -p 8001:8000 python:3.12-slim \
  python -m http.server 8000 --bind 0.0.0.0
curl localhost:8001          # ✅ listado de ficheros
docker rm -f solo-local todos
```

> ✅ **Las apps dentro de contenedores deben escuchar en `0.0.0.0`.** Por eso en
> la API del curso verás `app.run(host="0.0.0.0")` y en la web
> `app.listen(PORT, "0.0.0.0")`. Es uno de los errores más frecuentes al
> "dockerizar" una aplicación.

Y la otra cara: **`localhost` dentro de un contenedor es el propio
contenedor**, no tu Ubuntu ni otro contenedor. Si la web hace
`fetch("http://localhost:5000")` y la API está en otro contenedor, falla. Esto
es exactamente lo que habrá que cambiar al separar aplicaciones en el módulo 07.

---

## 6. Redes `host` y `none`

```bash
# host: sin aislamiento de red. nginx escucha DIRECTAMENTE en el puerto 80 del host
# (sin -p). Solo funciona así en Linux.
docker run -d --name enhost --network host nginx:1.27-alpine
curl localhost:80
docker rm -f enhost

# none: sin red
docker run --rm --network none alpine ip addr        # solo "lo"
docker run --rm --network none alpine ping -c 1 8.8.8.8   # ❌ Network unreachable
```

---

## 7. ¿Y si un contenedor necesita llegar a un servicio del host?

Por ejemplo, una base de datos instalada directamente en tu Ubuntu. Desde el
contenedor, `localhost` no sirve. En Linux:

```bash
docker run --rm --add-host=host.docker.internal:host-gateway alpine \
  ping -c 2 host.docker.internal
```

`host-gateway` es la IP del host vista desde los contenedores. (En Docker
Desktop para Windows/Mac, `host.docker.internal` ya existe sin hacer nada.)

---

## 8. Caja de herramientas para depurar redes

La imagen `nicolaka/netshoot` trae todas las herramientas de red (curl, dig,
nslookup, tcpdump, nc, ip...). Conéctala a la red que quieras investigar:

```bash
docker run --rm -it --network mired nicolaka/netshoot
# (dentro)
dig b1                 # ¿resuelve el nombre?
nc -zv b1 80           # ¿está abierto el puerto?
curl http://b1         # ¿responde HTTP?
exit
```

Desde un contenedor `alpine` normal también tienes `ping`, `nslookup` y `wget`.

---

## 9. ✍️ Ejercicios

**Ejercicio 1.** Crea una red `tienda`. Arranca en ella un `nginx:1.27-alpine`
llamado `catalogo` **sin publicar puertos**. Desde otro contenedor `alpine`
efímero en la misma red, descarga la página de `catalogo` con `wget`.
¿Puedes acceder a `catalogo` desde tu Ubuntu con `curl`?

<details><summary>Ver solución</summary>

```bash
docker network create tienda
docker run -d --name catalogo --network tienda nginx:1.27-alpine
docker run --rm --network tienda alpine wget -qO- http://catalogo | head -5   # ✅
curl localhost:80        # ❌ desde el host no: no hay puertos publicados
```

Este es exactamente el patrón de la API en los módulos 07-09: accesible para
los otros contenedores, invisible desde fuera.

</details>

**Ejercicio 2.** Un contenedor puede tener **alias** de red. Arranca otro nginx
en la red `tienda` con `--network-alias web`. Haz `nslookup web` desde un alpine.

<details><summary>Ver solución</summary>

```bash
docker run -d --name tienda-web --network tienda --network-alias web nginx:1.27-alpine
docker run --rm --network tienda alpine nslookup web
docker run --rm --network tienda alpine wget -qO- http://web | head -3
```

</details>

**Ejercicio 3.** Arranca dos contenedores con **el mismo alias** `servidor` en
la red `tienda` y haz varias veces `nslookup servidor`. ¿Qué observas? ¿Para qué
podría servir?

<details><summary>Ver solución</summary>

```bash
docker run -d --name s1 --network tienda --network-alias servidor nginx:1.27-alpine
docker run -d --name s2 --network tienda --network-alias servidor nginx:1.27-alpine
for i in 1 2 3; do docker run --rm --network tienda alpine nslookup servidor | grep Address; done
```

El DNS devuelve **las dos IPs**. Es un reparto de carga básico por DNS: lo verás
en el módulo 08 al escalar con `docker compose up --scale api=3`.

</details>

### Limpieza del módulo

```bash
docker rm -f a1 a2 b1 b2 w1 w2 w3 w4 catalogo tienda-web s1 s2 2>/dev/null
docker network rm mired tienda 2>/dev/null
```

---

➡️ Siguiente: [06 · Dos aplicaciones en un contenedor](../06-dos-apps-un-contenedor/README.md)
