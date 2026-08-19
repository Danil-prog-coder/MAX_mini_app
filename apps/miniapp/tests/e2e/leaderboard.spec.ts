import { expect, test } from '@playwright/test';

import { installApiStub, LEADERBOARD } from './apiStub';

/**
 * Блок 6 глазами пользователя: баллы, чек-ин, рейтинг и обмен (ТЗ 6.1–6.7).
 *
 * Рейтинг общеплатформенный (уточнение У19): подписи «в вузе» на экране быть
 * не должно — это проверяется отдельно.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

test('чек-ин даёт +10 и второй раз не предлагается', async ({ page }) => {
  // Уточнение У21: ежедневный чек-ин +10.
  await page.goto('/leaderboard');

  await page.getByRole('button', { name: /Ежедневный чек-ин · \+10/ }).click();

  await expect(page.getByRole('button', { name: /Чек-ин засчитан сегодня/ })).toBeDisabled();
  await expect(page.getByText('550', { exact: true })).toBeVisible();
});

test('рейтинг показывает лидеров, статус месяца и своё место', async ({ page }) => {
  await page.goto('/leaderboard');

  for (const row of LEADERBOARD) {
    await expect(page.getByText(row.display_name)).toBeVisible();
  }
  // Уточнение У24: название статуса месяца.
  await expect(page.getByText('НАШ ЧЕЛОВЕК')).toBeVisible();
  await expect(page.getByText('Вы', { exact: true })).toBeVisible();
  await expect(page.getByText(/до 3 места 60/)).toBeVisible();
});

test('на экране нет привязки рейтинга к вузу', async ({ page }) => {
  // Уточнение У19 и инвариант 9: рейтинг один на всю площадку.
  await page.goto('/leaderboard');

  await expect(page.getByText(/МЕСТО В ВУЗЕ/)).toHaveCount(0);
  await expect(page.getByText(/НЕДЕЛЯ В ВУЗЕ/)).toHaveCount(0);
});

test('баллов не хватает — кнопка обмена говорит об этом', async ({ page }) => {
  // ТЗ 6.7 и уточнение У23: бейдж стоит 500, а на счету 540 — хватит на него,
  // но не на оба сразу.
  await page.goto('/leaderboard');

  await page.getByRole('button', { name: /Бейдж в профиле/ }).click();

  await expect(page.getByRole('button', { name: /Бейдж в профиле · активировано/ })).toBeVisible();
  await expect(page.getByText(/Не хватает баллов: нужно ещё/)).toBeVisible();
});

test('купленная награда не покупается второй раз', async ({ page }) => {
  await page.goto('/leaderboard');

  await page.getByRole('button', { name: /Приоритет показа вопроса/ }).click();

  await expect(
    page.getByRole('button', { name: /Приоритет показа вопроса · активировано/ }),
  ).toBeDisabled();
  // 540 − 300 = 240.
  await expect(page.getByText('240', { exact: true })).toBeVisible();
});
