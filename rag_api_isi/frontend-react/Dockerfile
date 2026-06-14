# --- Étape 1 : build ---
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json ./
RUN npm install
COPY . .
RUN npm run build

# --- Étape 2 : service statique ---
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
# proxy /api vers le backend
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
