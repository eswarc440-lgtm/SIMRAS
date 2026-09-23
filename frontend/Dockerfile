FROM node:24-bookworm-slim AS development
WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates && rm -rf /var/lib/apt/lists/*
COPY package.json package-lock.json ./
ENV NODE_OPTIONS=--use-system-ca
# The isolated Docker build network presents a local registry proxy
# certificate; runtime traffic remains HTTPS.
RUN npm config set strict-ssl false && npm ci --no-audit --no-fund

COPY . .
EXPOSE 5173
CMD ["npm", "run", "dev"]

FROM development AS build
ARG VITE_API_BASE_URL=/api/v1
ARG VITE_CESIUM_ION_TOKEN=
ARG VITE_DEFAULT_ASSET_ID=AP_DAM_00001
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL \
    VITE_CESIUM_ION_TOKEN=$VITE_CESIUM_ION_TOKEN \
    VITE_DEFAULT_ASSET_ID=$VITE_DEFAULT_ASSET_ID
RUN npm run build

FROM nginx:1.29-alpine AS production
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]

