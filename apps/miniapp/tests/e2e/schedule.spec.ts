import { expect, test, type Page } from '@playwright/test';

import { installApiStub, LESSONS, STUDENT_PROFILE } from './apiStub';

/**
 * Блок 4 глазами студента: группа, пары на сегодня, личные дедлайны
 * (ТЗ 4.3–4.6).
 *
 * Стартовый профиль — студент с вузом: гейт проверяется отдельно, в
 * `profile.spec.ts`, а здесь важно то, что за ним.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page, { profile: STUDENT_PROFILE });
});

/** Выбирает группу в профиле — как это делает человек (ТЗ 4.3). */
async function pickGroup(page: Page, name: string): Promise<void> {
  await page.goto('/profile');
  await page.getByRole('button', { name: 'Изменить группу' }).click();
  await page.getByRole('dialog').getByRole('button', { name, exact: true }).click();
}

test('без группы расписание объясняет, чего не хватает', async ({ page }) => {
  await page.goto('/schedule');

  await expect(page.getByText('ГРУППА НЕ УКАЗАНА')).toBeVisible();
  await expect(page.getByText(/Группа не выбрана/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Выбрать группу' })).toBeVisible();
});

test('группа выбирается из списка и появляется в шапке расписания', async ({ page }) => {
  // ТЗ 4.3 и уточнение У13: только выбор из списка, поля для ссылки нет.
  await pickGroup(page, 'ИС-231');

  await page.getByRole('navigation').getByRole('link', { name: 'Главное меню' }).click();
  await page.getByRole('link', { name: /Расписание и дедлайны/ }).click();

  await expect(page.getByText('ИС-231')).toBeVisible();
});

test('день группы показывает пары и текущую из них', async ({ page }) => {
  await installApiStub(page, { profile: { ...STUDENT_PROFILE, group_name: 'ИС-231' } });
  await page.goto('/schedule');

  await expect(page.getByText('СЕГОДНЯ')).toBeVisible();
  for (const lesson of LESSONS) {
    await expect(page.getByText(lesson.title)).toBeVisible();
  }
  // Идущая пара помечена плашкой — она одна.
  await expect(page.getByText('СЕЙЧАС')).toHaveCount(1);
});

test('личный дедлайн добавляется шторкой и встаёт в список', async ({ page }) => {
  // ТЗ 4.5: название и срок, напоминание за сутки (ТЗ 4.6).
  await page.goto('/schedule');

  await page.getByRole('button', { name: 'Добавить дедлайн' }).click();
  const sheet = page.getByRole('dialog');
  await sheet.getByRole('textbox', { name: 'Название дедлайна' }).fill('Курсовая по базам данных');
  await sheet.getByRole('button', { name: 'через 3 дня' }).click();
  await sheet.getByRole('button', { name: 'Добавить' }).click();

  await expect(page.getByText('Курсовая по базам данных')).toBeVisible();
  await expect(page.getByText(/напомню за сутки/)).toBeVisible();
});

test('дедлайн без названия не добавляется', async ({ page }) => {
  await page.goto('/schedule');

  await page.getByRole('button', { name: 'Добавить дедлайн' }).click();

  await expect(page.getByRole('dialog').getByRole('button', { name: 'Добавить' })).toBeDisabled();
});
