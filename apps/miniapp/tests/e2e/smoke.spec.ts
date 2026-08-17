import { expect, test } from '@playwright/test';

/**
 * Проверка, что связка «сборка Vite → браузер» жива и e2e-обвязка работает на
 * обоих профилях устройств (ТЗ 0.2). На шаге «оболочка фронта» рядом появляется
 * главный e2e-тест: обход всех роутов с проверкой кнопки «Главное меню».
 */
test('приложение открывается и не роняет консоль', async ({ page }) => {
  const consoleErrors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => consoleErrors.push(error.message));

  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Навигатор' })).toBeVisible();
  // Ошибка запроса к недоступному Core API в консоль попадает штатно и не
  // считается поломкой страницы, поэтому её отфильтровываем.
  const unexpected = consoleErrors.filter((text) => !text.includes('/health'));
  expect(unexpected).toEqual([]);
});

test('нет горизонтального скролла', async ({ page }) => {
  // ТЗ 0.2: адаптивная вёрстка без горизонтального скролла и обрезанных
  // элементов — одинаково на мобильном и на десктопе.
  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Навигатор' })).toBeVisible();

  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflows).toBe(false);
});
