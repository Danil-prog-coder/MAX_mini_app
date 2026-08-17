# syntax=docker/dockerfile:1
#
# Мини-приложение. Две цели сборки:
#   dev        — dev-сервер Vite с HMR, используется в docker-compose;
#   production — многостадийная сборка node → nginx (тех. ТЗ 8.10).
#
# Core API статику фронтенда не отдаёт: зоны ответственности разделены, статика
# уходит отдельным контейнером с nginx.
#
# Контекст сборки — корень монорепо: там лежат pnpm-workspace.yaml и локфайл.

FROM node:22-slim AS deps

ENV PNPM_HOME=/pnpm \
    PATH="/pnpm:$PATH"
RUN corepack enable

WORKDIR /repo

# Манифесты — отдельным слоем: правка кода не переустанавливает зависимости.
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/miniapp/package.json apps/miniapp/
RUN pnpm install --frozen-lockfile

# ─── dev: живой сервер Vite ──────────────────────────────────────────────────
FROM deps AS dev
COPY apps/miniapp apps/miniapp
WORKDIR /repo/apps/miniapp
EXPOSE 5173
CMD ["pnpm", "dev"]

# ─── build: статика ──────────────────────────────────────────────────────────
FROM deps AS build
COPY apps/miniapp apps/miniapp
WORKDIR /repo/apps/miniapp
# Значения подставляются в бандл на этапе сборки: у Vite нет рантайм-конфига.
ARG VITE_API_BASE_URL
ARG VITE_MOCK_MAX_USER_ID
RUN pnpm build

# ─── production: nginx со статикой ───────────────────────────────────────────
FROM nginx:1-alpine AS production
COPY apps/miniapp/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /repo/apps/miniapp/dist /usr/share/nginx/html
EXPOSE 80
HEALTHCHECK --interval=15s --timeout=5s --start-period=5s --retries=3 \
    CMD ["wget", "--quiet", "--tries=1", "--spider", "http://127.0.0.1/"]
