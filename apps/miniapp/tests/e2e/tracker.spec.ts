import { expect, test, type Page } from '@playwright/test';

import { installApiStub, TECH_SCORES } from './apiStub';

/**
 * Блок 3 глазами пользователя: пустой трекер, добавление вуза из блока 2,
 * ручной ввод позиции и сравнение с прошлой проверкой (ТЗ 3.2–3.7).
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  // Трекер начинается пустым: блок 3 наполняется из блока 2, и путь «добавил
  // вуз — увидел его в трекере» проверяется целиком.
  await installApiStub(page, { tracked: [] });
});

/** Проходит блок 2 до карточки вуза и добавляет его в отслеживаемые. */
async function trackFirstUniversity(page: Page): Promise<void> {
  await page.goto('/vuz-selection');
  for (const [subject, score] of Object.entries(TECH_SCORES)) {
    await page.getByRole('button', { name: subject, exact: true }).click();
    await page.getByRole('spinbutton', { name: `Балл ЕГЭ, ${subject}` }).fill(String(score));
  }
  await page.getByRole('button', { name: 'Подобрать вузы' }).click();
  await page.getByRole('link').filter({ hasText: 'ВЫСОКИЙ ШАНС' }).click();
  await page.getByRole('button', { name: 'Отслеживать этот вуз' }).click();
  await page.getByRole('link', { name: 'Перейти в трекер' }).click();
}

test('пустой трекер объясняет, как его наполнить, и ведёт в подбор', async ({ page }) => {
  // ТЗ 3.3: пустое состояние — маршрут в блок 2, а не сообщение об ошибке.
  await page.goto('/tracker');

  await expect(page.getByText(/Подберите вуз по баллам ЕГЭ/)).toBeVisible();

  await page.getByRole('link', { name: 'Подобрать вуз' }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'vuz-selection');
});

test('вуз из блока 2 появляется в трекере без позиции', async ({ page }) => {
  // ТЗ 3.2 и 3.5: позицию человек называет сам, подставлять её нельзя.
  await trackFirstUniversity(page);

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'tracker');
  await expect(page.getByText('ПОЗИЦИЯ НЕ УКАЗАНА')).toBeVisible();
  await expect(page.getByText('ОТСЛЕЖИВАЕТСЯ')).toBeVisible();
});

test('позиция вводится вручную и попадает в карточку списка', async ({ page }) => {
  await trackFirstUniversity(page);
  await page.getByRole('link').filter({ hasText: 'ПОЗИЦИЯ НЕ УКАЗАНА' }).click();

  await expect(page.getByRole('heading', { name: 'На каком вы месте в списке?' })).toBeVisible();
  await page.getByRole('spinbutton', { name: 'Ваше место в конкурсном списке' }).fill('116');
  await page.getByRole('button', { name: 'Сохранить позицию' }).click();

  await expect(page.getByText('ВАША ПОЗИЦИЯ СЕГОДНЯ')).toBeVisible();
  await expect(page.getByText('116', { exact: true })).toBeVisible();

  await page.getByRole('navigation').getByRole('link', { name: 'Главное меню' }).click();
  await page.getByRole('link', { name: 'Трекер конкурсных списков' }).click();

  await expect(page.getByText('ВАША ПОЗИЦИЯ', { exact: true })).toBeVisible();
});

test('вторая проверка показывает движение по списку', async ({ page }) => {
  // ТЗ 3.6: сравнение с прошлой проверкой и есть смысл блока.
  await trackFirstUniversity(page);
  await page.getByRole('link').filter({ hasText: 'ПОЗИЦИЯ НЕ УКАЗАНА' }).click();
  await page.getByRole('spinbutton', { name: 'Ваше место в конкурсном списке' }).fill('116');
  await page.getByRole('button', { name: 'Сохранить позицию' }).click();

  await page.getByRole('button', { name: 'Обновить позицию вручную' }).click();
  await page.getByRole('spinbutton', { name: 'Ваше место в конкурсном списке' }).fill('64');
  await page.getByRole('button', { name: 'Сохранить позицию' }).click();

  await expect(page.getByText('на 52')).toBeVisible();
  await expect(page.getByText(/В прошлый раз вы были 116-м/)).toBeVisible();
});

test('обещание напомнить о датах приёма стоит на экране', async ({ page }) => {
  // ТЗ 3.7: за 7 дней до старта приёма и за 1 день до окончания.
  await trackFirstUniversity(page);
  await page.getByRole('link').filter({ hasText: 'ПОЗИЦИЯ НЕ УКАЗАНА' }).click();
  await page.getByRole('spinbutton', { name: 'Ваше место в конкурсном списке' }).fill('116');
  await page.getByRole('button', { name: 'Сохранить позицию' }).click();

  await expect(
    page.getByText('Напомню за 7 дней до старта приёма и за 1 день до конца'),
  ).toBeVisible();
});

test('место вне диапазона не сохраняется', async ({ page }) => {
  await trackFirstUniversity(page);
  await page.getByRole('link').filter({ hasText: 'ПОЗИЦИЯ НЕ УКАЗАНА' }).click();

  await page.getByRole('spinbutton', { name: 'Ваше место в конкурсном списке' }).fill('0');

  await expect(page.getByRole('alert')).toContainText('от 1 до 9999');
  await expect(page.getByRole('button', { name: 'Сохранить позицию' })).toBeDisabled();
});

test('не отслеживаемый вуз не оставляет тупика', async ({ page }) => {
  // ТЗ 1.1: тупиковых экранов нет даже по устаревшей ссылке.
  await page.goto('/tracker/9999');

  await expect(page.getByText(/Этот вуз не в отслеживаемых/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'К трекеру' })).toBeVisible();
});
