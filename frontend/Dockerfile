# syntax=docker/dockerfile:1
# 构建上下文为 frontend/：
#   docker build -f frontend/Dockerfile -t ai-talent-web frontend
FROM node:22-bookworm-slim AS build

WORKDIR /app

ARG NPM_REGISTRY=https://registry.npmjs.org
COPY package.json package-lock.json ./
RUN npm config set registry "${NPM_REGISTRY}" && npm ci --no-fund --no-audit

COPY . .
RUN npm run build

FROM nginx:1.27-alpine
RUN rm -f /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/conf.d/app.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
