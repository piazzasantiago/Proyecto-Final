# Capa de presentación: se compila React con Vite y el resultado lo sirve nginx.

# --- Etapa 1: build ----------------------------------------------------------
FROM node:22-alpine AS build
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Vacío = la API está en el mismo dominio que el frontend (/api/...).
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# --- Etapa 2: nginx ----------------------------------------------------------
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
