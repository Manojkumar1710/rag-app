# --- Build stage ---
FROM node:20-slim AS build

WORKDIR /app

COPY package.json ./
RUN npm install

COPY . .

ARG VITE_BACKEND_URL=http://localhost:8000
ENV VITE_BACKEND_URL=$VITE_BACKEND_URL

RUN npm run build

# --- Serve stage ---
FROM nginx:1.27-alpine

COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 5173

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -q -O- http://localhost:5173/health || exit 1

CMD ["nginx", "-g", "daemon off;"]
