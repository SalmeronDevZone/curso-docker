# WEB de notas con Dockerfile de producción (ver módulo 10).
FROM node:22-alpine

ENV NODE_ENV=production
WORKDIR /app

COPY package*.json ./
# Instalamos como root -> node_modules queda en propiedad de root: el usuario
# "node" puede LEERLO pero no modificarlo (si atacan la app, no puede tocarlo).
RUN npm ci --omit=dev && npm cache clean --force

COPY . .

# La imagen oficial de Node ya trae un usuario sin privilegios llamado "node"
USER node

EXPOSE 3000

# Alpine trae "wget" (de busybox). Usamos 127.0.0.1 y no "localhost" porque
# "localhost" puede resolverse a IPv6 (::1) y la app solo escucha en IPv4.
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -qO- http://127.0.0.1:3000/health > /dev/null || exit 1

CMD ["node", "server.js"]
