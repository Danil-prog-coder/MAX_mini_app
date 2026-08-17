import { defineConfig, devices } from '@playwright/test';

/**
 * Конфигурация e2e.
 *
 * Первый и обязательный e2e-тест — обход всех зарегистрированных роутов с
 * проверкой, что каждый экран отрисовывает кнопку «Главное меню» (тех. ТЗ 8.9,
 * 9.5). Он появляется вместе с деревом роутов на шаге «оболочка фронта».
 *
 * Два проекта, потому что кроссплатформенность — критерий приёмки (ТЗ 0.2):
 * мобильный клиент MAX и десктопный/веб-клиент проверяются отдельно.
 */

const PORT = 5173;
const BASE_URL = `http://127.0.0.1:${String(PORT)}`;

/**
 * Обычно браузеры ставит `pnpm exec playwright install`. Но часть окружений
 * (dev-контейнеры, готовые CI-образы) поставляет Chromium заранее и своей
 * версии сборки — тогда путь к нему передаётся переменной, и загрузка не нужна.
 */
const chromiumExecutable = process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE;
const preinstalledChromium = chromiumExecutable
  ? { launchOptions: { executablePath: chromiumExecutable } }
  : {};

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: BASE_URL,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: {
        ...devices['Desktop Chrome'],
        viewport: { width: 1280, height: 900 },
        ...preinstalledChromium,
      },
    },
    {
      name: 'mobile',
      use: { ...devices['Pixel 7'], ...preinstalledChromium },
    },
  ],
  webServer: {
    command: 'pnpm dev',
    url: BASE_URL,
    reuseExistingServer: !process.env.CI,
    timeout: 60_000,
  },
});
