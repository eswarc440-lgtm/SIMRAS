FROM node:20-bookworm-slim AS development
WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund

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
