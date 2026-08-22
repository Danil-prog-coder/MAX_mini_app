import { expect, test } from '@playwright/test';

import { APPLICANT_PROFILE, STUDENT_PROFILE, installApiStub } from './apiStub';

/**
 * Календарь-решётка на главном экране (уточнение У10, хендофф — экран 1).
 *
 * Этот файл появился после приёмки, на которой выяснилось, что календаря на
 * главной просто нет: обход роутов был зелёным, потому что проверял кнопку
 * «Главное меню», а не содержимое экрана. Отсюда правило — у главного элемента
 * экрана должен быть свой тест, иначе его отсутствие никто не заметит.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test('на главной есть календарь: месяц, дни недели и сетка дней', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await expect(page.getByText('ИЮЛЬ', { exact: true })).toBeVisible();
  await expect(page.getByText('2026', { exact: true })).toBeVisible();
  // Июль 2026 — 31 день, каждый день кликабелен.
  await expect(page.getByRole('button', { name: /июля/ })).toHaveCount(31);
  await expect(page.getByText('Нажмите на день — покажу, что в нём')).toBeVisible();
});

test('клик по дню открывает шторку с событиями этого дня', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await page.getByRole('button', { name: '13 июля, есть события' }).click();

  const sheet = page.getByRole('dialog');
  await expect(sheet).toContainText('13 ИЮЛЯ · ПН');
  await expect(sheet).toContainText('Приём документов идёт');
  await expect(sheet).toContainText('Вы поднялись на 64 место');
});

test('день без событий не выглядит ошибкой', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await page.getByRole('button', { name: '2 июля', exact: true }).click();

  await expect(page.getByRole('dialog')).toContainText('Ничего не запланировано');
});

test('у студента в том же дне свои события, а не приёмная кампания', async ({ page }) => {
  // Содержимое календаря зависит от статуса профиля (макет, `events()`).
  await installApiStub(page, { profile: STUDENT_PROFILE });
  await page.goto('/');

  await page.getByRole('button', { name: '13 июля, есть события' }).click();

  const sheet = page.getByRole('dialog');
  await expect(sheet).toContainText('4 пары · с 09:00');
  await expect(sheet).toContainText('Курсовая по базам данных');
});

test('стрелки листают месяцы и не выпускают за границы макета', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await page.getByRole('button', { name: 'Следующий месяц' }).click();
  await expect(page.getByText('АВГУСТ', { exact: true })).toBeVisible();
  // Август — последний месяц макета, дальше листать некуда.
  await expect(page.getByRole('button', { name: 'Следующий месяц' })).toBeDisabled();

  await page.getByRole('button', { name: 'Предыдущий месяц' }).click();
  await page.getByRole('button', { name: 'Предыдущий месяц' }).click();
  await expect(page.getByText('ИЮНЬ', { exact: true })).toBeVisible();
  await expect(page.getByRole('button', { name: 'Предыдущий месяц' })).toBeDisabled();
});
