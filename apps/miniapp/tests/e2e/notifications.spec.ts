import { expect, test } from '@playwright/test';

import { installApiStub, NOTIFICATIONS } from './apiStub';

/**
 * Уведомления (уточнения У9, У25): бейдж, лента и настройки в профиле.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

test('бейдж непрочитанных виден в нижней панели с любого экрана', async ({ page }) => {
  await page.goto('/support');

  await expect(page.getByRole('button', { name: 'Уведомления, непрочитанных 1' })).toBeVisible();
});

test('лента открывается шторкой и показывает уведомление', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('button', { name: /Уведомления/ }).click();

  const sheet = page.getByRole('dialog');
  await expect(sheet).toBeVisible();
  await expect(sheet.getByText(NOTIFICATIONS[0]?.title ?? '')).toBeVisible();
  await expect(sheet.getByText('СКОРО ДЕДЛАЙН')).toBeVisible();
});

test('прочитанное уведомление снимает бейдж', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('button', { name: /Уведомления/ }).click();

  await page
    .getByRole('dialog')
    .getByRole('button', { name: /Курсовая завтра/ })
    .click();

  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: 'Уведомления', exact: true })).toBeVisible();
});

test('пустая лента объясняет, что сюда придёт', async ({ page }) => {
  await installApiStub(page, { notifications: [] });
  await page.goto('/');

  await page.getByRole('button', { name: /Уведомления/ }).click();

  await expect(page.getByText(/Пока тихо/)).toBeVisible();
});

test('время сводки и типы уведомлений настраиваются в профиле', async ({ page }) => {
  // Уточнение У9: время ежедневной сводки (ТЗ 4.4) и переключатели типов.
  await page.goto('/profile');

  await expect(page.getByText('УВЕДОМЛЕНИЯ')).toBeVisible();
  await page.getByRole('button', { name: '18:00' }).click();
  await expect(page.getByRole('button', { name: '18:00' })).toHaveAttribute('aria-pressed', 'true');

  const deadline = page.getByRole('checkbox', { name: 'Скоро дедлайн' });
  await expect(deadline).toBeChecked();
  // Клик, а не `uncheck()`: состояние переключателя приходит с сервера, и
  // синхронной смены галочки Playwright тут не дождётся.
  await deadline.click();
  await expect(page.getByRole('checkbox', { name: 'Скоро дедлайн' })).not.toBeChecked();
});
