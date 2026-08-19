import { expect, test, type Page } from '@playwright/test';

import { DIRECTIONS, installApiStub, QUESTIONS } from './apiStub';

/**
 * Блок 1 целиком глазами пользователя: десять вопросов, результат, сохранение
 * в профиль и вакансии по профилю (ТЗ 2, блок 1).
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

async function answerAll(page: Page): Promise<void> {
  for (let step = 0; step < QUESTIONS.length; step += 1) {
    await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', String(step + 1));
    await page.getByRole('button', { name: 'Разобрать, как что-то устроено внутри' }).click();
  }
}

test('тест открывается из меню и показывает первый вопрос из макета', async ({ page }) => {
  await page.goto('/');

  await page.getByRole('link', { name: 'Профориентационный тест' }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'career-test');
  await expect(
    page.getByRole('heading', { name: 'Что из этого вам ближе в свободный вечер?' }),
  ).toBeVisible();
  await expect(page.getByText('ИЗ 10')).toBeVisible();
});

test('десять ответов приводят к результату с топ-3 направлений', async ({ page }) => {
  await page.goto('/career-test');

  await answerAll(page);

  await expect(page).toHaveURL('/career-test/results');
  await expect(page.getByRole('heading', { name: DIRECTIONS.first.name })).toBeVisible();
  await expect(page.getByText('СОВПАДЕНИЕ')).toBeVisible();
  // Второе и третье направления тоже на экране (ТЗ 1.4).
  await expect(page.getByText(DIRECTIONS.second.name)).toBeVisible();
  await expect(page.getByText(DIRECTIONS.third.name)).toBeVisible();
});

test('прогресс теста теряется при выходе в меню', async ({ page }) => {
  // ТЗ 1.3: это требование, а не баг сохранения.
  await page.goto('/career-test');
  await page.getByRole('button', { name: 'Разобрать, как что-то устроено внутри' }).click();
  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '2');

  await page.getByRole('navigation').getByRole('link', { name: 'Главное меню' }).click();
  await page.getByRole('link', { name: 'Профориентационный тест' }).click();

  await expect(page.getByRole('progressbar')).toHaveAttribute('aria-valuenow', '1');
});

test('результат сохраняется в профиль и начисляет баллы', async ({ page }) => {
  await page.goto('/career-test/results');

  await page.getByRole('button', { name: 'Сохранить в профиль' }).click();

  // Уточнение У21: +50 за прохождение теста.
  await expect(
    page.getByRole('button', { name: /Сохранено в профиль · \+50 баллов/ }),
  ).toBeVisible();
  await expect(page.getByRole('button', { name: /Сохранено/ })).toBeDisabled();
});

test('вакансии по профилю открываются шторкой', async ({ page }) => {
  await page.goto('/career-test/results');

  await page.getByRole('button', { name: 'Вакансии' }).click();

  const sheet = page.getByRole('dialog');
  await expect(sheet).toBeVisible();
  await expect(sheet.getByText('Аналитик данных')).toBeVisible();
  // Число позиций разделяется пробелами по-русски: 2 410, а не 2,410.
  await expect(sheet.getByText('2 410')).toBeVisible();

  await page.keyboard.press('Escape');
  await expect(sheet).toBeHidden();
});

test('из результата можно уйти в подбор вузов с предзаполненным направлением', async ({ page }) => {
  await page.goto('/career-test/results');

  await page.getByRole('link', { name: 'Показать вузы' }).click();

  await expect(page).toHaveURL('/vuz-selection?direction=applied_mathematics');
  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'vuz-selection');
});
