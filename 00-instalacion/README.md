# 00 · Instalación de Docker en Ubuntu

**Objetivo:** tener Docker Engine + Docker Compose funcionando en tu máquina
virtual Ubuntu, usarlo sin `sudo` y saber acceder a las aplicaciones desde el
navegador de Windows.

---

## 1. Antes de empezar: ¿qué vamos a instalar?

| Pieza | Qué es |
|-------|--------|
| **Docker Engine** (`docker-ce`) | El "motor": un servicio (`dockerd`) que corre en segundo plano y gestiona contenedores, imágenes, redes y volúmenes. |
| **Docker CLI** (`docker-ce-cli`) | El comando `docker` que escribes. Solo le manda órdenes al motor. |
| **containerd** (`containerd.io`) | El componente que de verdad arranca y vigila los contenedores (lo usa `dockerd` por debajo). |
| **Buildx** (`docker-buildx-plugin`) | El constructor moderno de imágenes (`docker build`). |
| **Compose** (`docker-compose-plugin`) | `docker compose`: arrancar aplicaciones de varios contenedores desde un fichero YAML. |

> 🧠 **Docker Desktop vs Docker Engine.** En Windows/Mac se usa *Docker Desktop*,
> que en realidad monta una pequeña máquina virtual Linux y corre Docker Engine
> dentro. En Ubuntu no hace falta: los contenedores son una característica del
> propio kernel Linux, así que instalamos el Engine directamente. Es lo que se
> usa en servidores.

---

## 2. Requisitos de la máquina virtual

- Ubuntu 22.04 LTS o 24.04 LTS (64 bits).
- **2 CPU, 4 GB RAM, 20 GB de disco** como mínimo.
- Red en modo **NAT** (con reenvío de puertos) o **Adaptador puente** (ver sección 7).

Comprueba tu versión y arquitectura:

```bash
lsb_release -a     # versión de Ubuntu
uname -m           # x86_64 (lo normal) o aarch64 (ARM)
```

---

## 3. Instalación (método oficial, recomendado)

### 3.1 Quitar versiones antiguas o no oficiales (si las hubiera)

```bash
for pkg in docker.io docker-doc docker-compose docker-compose-v2 podman-docker containerd runc; do
  sudo apt-get remove -y $pkg
done
```

Es normal que diga que no estaban instalados.

> ⚠️ **No uses `snap install docker`.** La versión snap tiene restricciones de
> seguridad (confinamiento) que dan errores raros con volúmenes fuera de tu
> carpeta personal. Usa siempre el repositorio oficial de Docker.

### 3.2 Añadir el repositorio oficial de Docker

```bash
# Herramientas necesarias
sudo apt-get update
sudo apt-get install -y ca-certificates curl

# Clave GPG de Docker (para verificar que los paquetes son auténticos)
sudo install -m 0755 -d /etc/apt/keyrings
sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc

# Añadir el repositorio a las fuentes de apt
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "${UBUNTU_CODENAME:-$VERSION_CODENAME}") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
```

### 3.3 Instalar Docker

```bash
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

### 3.4 (Alternativa rápida) Script de conveniencia

Para una VM de aprendizaje también vale el script oficial, que hace todo lo
anterior de golpe:

```bash
curl -fsSL https://get.docker.com -o get-docker.sh
less get-docker.sh          # ⚠️ buena costumbre: LEE un script antes de ejecutarlo con sudo
sudo sh get-docker.sh
```

---

## 4. Comprobar que el servicio está funcionando

```bash
sudo systemctl status docker      # debe decir "active (running)". Sal con q
sudo systemctl enable docker      # que arranque solo al encender la VM
sudo docker run hello-world       # primera prueba
```

Si ves `Hello from Docker!`, el motor funciona. 🎉

---

## 5. Usar Docker sin `sudo`

Por defecto, solo `root` puede hablar con el motor de Docker. Para no escribir
`sudo` delante de cada comando, añade tu usuario al grupo `docker`:

```bash
sudo usermod -aG docker $USER
```

Después **cierra sesión y vuelve a entrar** (o reinicia la VM). Para aplicarlo
solo en la terminal actual, sin cerrar sesión:

```bash
newgrp docker
```

✅ **Comprueba:**

```bash
docker run hello-world     # ahora sin sudo
groups                     # debe aparecer "docker" en la lista
```

> 🧠 **Por qué funciona y por qué es delicado.** El comando `docker` habla con el
> motor a través de un fichero especial: el *socket* `/var/run/docker.sock`.
> Ese fichero pertenece al grupo `docker`. Estar en ese grupo equivale a ser
> **root** en la máquina (puedes arrancar un contenedor que monte `/` del host).
> En tu VM de aprendizaje no pasa nada; en un servidor real, piensa bien a quién
> metes en ese grupo.

```bash
ls -l /var/run/docker.sock
# srw-rw---- 1 root docker 0 ... /var/run/docker.sock
```

---

## 6. Verificar la instalación completa

```bash
docker version            # versión del CLIENTE y del SERVIDOR (motor)
docker info               # información del motor: contenedores, imágenes, driver de almacenamiento...
docker compose version    # Compose v2 (¡con espacio, no con guion!)
docker buildx version
```

> 🧠 `docker version` muestra dos bloques: **Client** y **Server**. Son dos
> programas distintos. Si el bloque Server da error ("Cannot connect to the
> Docker daemon"), el cliente está instalado pero el motor no está corriendo o
> no tienes permisos.

---

## 7. Acceder a las aplicaciones de la VM desde Windows

Durante el curso arrancarás aplicaciones web en puertos como el `8080`. Tienes
tres opciones para verlas:

### Opción A — Navegador dentro de la propia VM (lo más simple)

Si tu Ubuntu tiene escritorio, abre Firefox dentro de la VM y ve a
`http://localhost:8080`. O desde la terminal: `curl http://localhost:8080`.

### Opción B — Red en modo "Adaptador puente" (Bridged)

La VM recibe una IP de tu router como si fuera otro ordenador de la casa.

```bash
ip -4 addr show | grep inet     # busca algo como 192.168.1.50
```

Desde el navegador de Windows: `http://192.168.1.50:8080`.

### Opción C — Red en modo NAT + reenvío de puertos

En **VirtualBox**: Configuración de la VM → Red → Adaptador 1 (NAT) → Avanzadas
→ Reenvío de puertos → añade una regla:

| Nombre | Protocolo | IP anfitrión | Puerto anfitrión | IP invitado | Puerto invitado |
|--------|-----------|--------------|------------------|-------------|-----------------|
| web    | TCP       | 127.0.0.1    | 8080             |             | 8080            |

(Repite con `8081` y `5000` si quieres usarlos también.) Ahora, en Windows,
`http://localhost:8080` llega a la VM.

En **VMware** el equivalente está en *Virtual Network Editor → NAT Settings →
Port Forwarding*.

> ⚠️ **Ojo con el cortafuegos.** En Ubuntu, Docker modifica las reglas de
> `iptables` directamente, y **los puertos que publiques con `-p` se saltan las
> reglas de UFW**. Es decir: aunque UFW diga que el puerto 8080 está cerrado, si
> haces `-p 8080:80`, estará abierto. Lo veremos en el módulo 05.

---

## 8. Instalar git y clonar el curso

```bash
sudo apt-get install -y git
git clone https://github.com/SalmeronDevZone/curso-docker.git
cd curso-docker
ls
```

Recomendado también (para los ejercicios):

```bash
sudo apt-get install -y curl jq tree
```

- `curl` → hacer peticiones HTTP desde la terminal.
- `jq` → mostrar JSON bonito (`curl -s localhost:8080/api/notas | jq`).
- `tree` → ver estructuras de carpetas.

---

## 9. Problemas típicos de instalación

| Síntoma | Causa | Solución |
|---------|-------|----------|
| `permission denied while trying to connect to the Docker daemon socket` | Tu usuario no está en el grupo `docker` (o no has vuelto a entrar) | Sección 5 y **cerrar sesión** |
| `Cannot connect to the Docker daemon at unix:///var/run/docker.sock` | El servicio no está arrancado | `sudo systemctl start docker` y mira `sudo journalctl -u docker` |
| `docker-compose: command not found` | Estás usando la sintaxis antigua (v1, con guion) | Usa `docker compose` (con espacio) |
| `E: Package 'docker-ce' has no installation candidate` | El repositorio no se añadió bien | Repite el paso 3.2 y revisa `/etc/apt/sources.list.d/docker.list` |
| Las descargas de imágenes van lentísimas o fallan | Red de la VM / DNS | Prueba `ping -c 3 registry-1.docker.io` y revisa la red de la VM |

---

## 10. (Por si acaso) Desinstalar Docker por completo

```bash
sudo apt-get purge -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo rm -rf /var/lib/docker /var/lib/containerd   # ⚠️ borra TODAS las imágenes, contenedores y volúmenes
```

> 🧠 Fíjate en esa ruta: **`/var/lib/docker`** es donde Docker guarda todo
> (imágenes, capas, volúmenes...). Lo volveremos a ver en la teoría.

---

➡️ Siguiente: [01 · Teoría](../01-teoria/README.md)
