import { expect, test, type Page } from '@playwright/test';

import { installApiStub, TECH_SCORES } from './apiStub';

/**
 * Блок 2 глазами пользователя: выбор предметов, ввод баллов, метки шанса,
 * карточка вуза и отслеживание (ТЗ 2.2–2.7).
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

/** Выбирает три технических предмета и вводит баллы, как это делает человек. */
async function fillScores(page: Page): Promise<void> {
  for (const [subject, score] of Object.entries(TECH_SCORES)) {
    await page.getByRole('button', { name: subject, exact: true }).click();
    await page.getByRole('spinbutton', { name: `Балл ЕГЭ, ${subject}` }).fill(String(score));
  }
}

test('подбор открывается из меню и просит минимум три предмета', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Подбор вуза по баллам ЕГЭ' }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'vuz-selection');
  await expect(
    page.getByRole('button', { name: /Выберите минимум 3 предмета и введите баллы/ }),
  ).toBeDisabled();
});

test('сумма баллов считается по мере ввода', async ({ page }) => {
  await page.goto('/vuz-selection');

  await fillScores(page);

  const total = Object.values(TECH_SCORES).reduce((sum, score) => sum + score, 0);
  await expect(page.getByText('СУММА БАЛЛОВ')).toBeVisible();
  await expect(page.getByText(String(total), { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Подобрать вузы' })).toBeEnabled();
});

test('балл вне диапазона 0–100 не засчитывается', async ({ page }) => {
  // ТЗ 2.3: проверка диапазона. Границы приходят с сервера, экран их только
  // показывает — но пропустить неверное значение он не должен.
  await page.goto('/vuz-selection');
  await fillScores(page);

  await page.getByRole('spinbutton', { name: 'Балл ЕГЭ, Математика' }).fill('120');

  await expect(page.getByRole('spinbutton', { name: 'Балл ЕГЭ, Математика' })).toHaveAttribute(
    'aria-invalid',
    'true',
  );
  await expect(page.getByRole('alert')).toHaveText('0–100');
  await expect(page.getByRole('button', { name: /Выберите минимум 3 предмета/ })).toBeDisabled();
});

test('баллы переживают выход в главное меню', async ({ page }) => {
  // ТЗ 2.4: выход в меню не теряет введённое.
  await page.goto('/vuz-selection');
  await fillScores(page);
  // Ждём, пока черновик доедет до сервера: он уходит с паузой после ввода.
  await expect(page.getByRole('button', { name: 'Подобрать вузы' })).toBeEnabled();
  await page.waitForResponse(
    (response) =>
      response.url().includes('/api/v1/vuz-selection/scores') &&
      response.request().method() === 'POST',
  );

  await page.getByRole('navigation').getByRole('link', { name: 'Главное меню' }).click();
  await page.getByRole('link', { name: 'Подбор вуза по баллам ЕГЭ' }).click();

  await expect(page.getByRole('spinbutton', { name: 'Балл ЕГЭ, Математика' })).toHaveValue(
    String(TECH_SCORES['Математика']),
  );
});

test('выдача показывает метки шанса всех трёх видов', async ({ page }) => {
  // Уточнения У11 и Д1: точки, caps-подпись и эмодзи из ТЗ 2.5.
  await page.goto('/vuz-selection');
  await fillScores(page);
  await page.getByRole('button', { name: 'Подобрать вузы' }).click();

  await expect(page).toHaveURL('/vuz-selection/results');
  await expect(page.getByText('🟢 ВЫСОКИЙ ШАНС')).toBeVisible();
  await expect(page.getByText('🟡 ПОГРАНИЧНЫЙ')).toBeVisible();
  await expect(page.getByText('🔴 МАЛОВЕРОЯТНО')).toBeVisible();
  // Высокий шанс идёт первым: список отсортирован по убыванию шанса.
  await expect(page.getByRole('link').filter({ hasText: 'ВЫСОКИЙ ШАНС' })).toHaveCount(1);
});

test('направление без сданных обязательных предметов в выдачу не попадает', async ({ page }) => {
  // Уточнение У12: показать вуз, куда человек не может подать документы, —
  // значит соврать ему.
  await page.goto('/vuz-selection');
  await fillScores(page);
  await page.getByRole('button', { name: 'Подобрать вузы' }).click();

  await expect(page.getByText('Программная инженерия')).toBeVisible();
  await expect(page.getByText('Юриспруденция')).toHaveCount(0);
});

test('карточка вуза показывает цифры приёмной кампании и метку демо-данных', async ({ page }) => {
  // ТЗ 2.6 плюс уточнения У4 и Д3: выдумку нельзя выдавать за официальные цифры.
  await page.goto('/vuz-selection');
  await fillScores(page);
  await page.getByRole('button', { name: 'Подобрать вузы' }).click();
  await page.getByRole('link').filter({ hasText: 'ВЫСОКИЙ ШАНС' }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'vuz-card');
  await expect(page.getByText('БЮДЖЕТ', { exact: true })).toBeVisible();
  await expect(page.getByText('ПЛАТНО', { exact: true })).toBeVisible();
  await expect(page.getByText('ОБЩЕЖИТИЕ', { exact: true })).toBeVisible();
  await expect(page.getByText('ПРИЁМ ДО', { exact: true })).toBeVisible();
  await expect(page.getByText(/демонстрационные данные/)).toBeVisible();
});

test('вуз добавляется в отслеживаемые и кнопка больше не предлагает это', async ({ page }) => {
  // ТЗ 2.7: отсюда наполняется трекер блока 3.
  await page.goto('/vuz-selection');
  await fillScores(page);
  await page.getByRole('button', { name: 'Подобрать вузы' }).click();
  await page.getByRole('link').filter({ hasText: 'ВЫСОКИЙ ШАНС' }).click();

  await page.getByRole('button', { name: 'Отслеживать этот вуз' }).click();

  await expect(page.getByRole('button', { name: 'Уже отслеживается' })).toBeDisabled();
  await expect(page.getByRole('link', { name: 'Перейти в трекер' })).toBeVisible();
});

test('карточка несуществующего вуза не оставляет тупика', async ({ page }) => {
  // ТЗ 1.1: тупиковых экранов нет даже по устаревшей ссылке.
  await page.goto('/vuz-selection/9999');

  await expect(page.getByText(/Такого вуза в справочнике нет/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'К списку вузов' })).toBeVisible();
});

test('пустая выдача предлагает ввести баллы, а не показывает ошибку', async ({ page }) => {
  await page.goto('/vuz-selection/results');

  await expect(page.getByText(/баллы ЕГЭ не введены/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Ввести баллы' })).toBeVisible();
});
