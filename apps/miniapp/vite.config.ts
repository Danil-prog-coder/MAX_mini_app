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
