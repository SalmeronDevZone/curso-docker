# Imagen de la WEB (Node.js). Solo contiene lo que la web necesita: Node + Express.
# Fíjate: imagen base DISTINTA a la de la API. Cada app elige su propio entorno.
FROM node:22-alpine

ENV NODE_ENV=production

WORKDIR /app

# 1º las dependencias (package.json + package-lock.json) -> capa cacheable
COPY package*.json ./
# npm ci = instalación exacta según package-lock.json (reproducible)
RUN npm ci --omit=dev

# 2º el código
COPY . .

EXPOSE 3000

CMD ["node", "server.js"]
