import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vitest/config';

const MINIAPP_PORT = 5173;

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  server: {
    // Слушаем все интерфейсы: dev-сервер поднимается ещё и внутри контейнера,
    // где 127.0.0.1 недостижим снаружи.
    host: true,
    port: MINIAPP_PORT,
    strictPort: true,
    // Прокси на Core API. Нужен, чтобы браузеру хватало одного порта — 5173.
    //
    // Без него фронт в контейнере ходил в API по `localhost:8000`, то есть
    // порт Core API обязан был быть свободен и опубликован на машине
    // разработчика. Занятый порт 8000 (а он занят у многих) означал, что
    // контейнер core-api вообще не стартует, а приложение показывает
    // «не удалось загрузить» без единого намёка на причину.
    //
    // Внутри compose цель — `http://core-api:8000` по имени сервиса, при
    // разработке на хосте — локальный uvicorn.
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  preview: { host: true, port: MINIAPP_PORT, strictPort: true },
  build: {
    outDir: 'dist',
    // Sourcemap нужны при отладке внутри клиента MAX: DevTools там ограничены.
    sourcemap: true,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
