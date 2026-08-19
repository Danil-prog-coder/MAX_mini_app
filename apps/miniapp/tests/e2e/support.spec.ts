import { expect, test } from '@playwright/test';

import { installApiStub, SUPPORT_CATEGORIES, SUPPORT_REPLIES } from './apiStub';

/**
 * Блок 8 глазами пользователя (ТЗ 8.2–8.6).
 *
 * Смысл блока — снять ощущение «сообщение ушло в пустоту», поэтому проверяется
 * не только отправка, но и то, что отписка видна сразу и остаётся в истории.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

test('три типа обращения выбираются чипами', async ({ page }) => {
  await page.goto('/support');

  for (const category of SUPPORT_CATEGORIES) {
    await expect(page.getByRole('button', { name: category.label })).toBeVisible();
  }
});

test('обращение получает типовую отписку сразу', async ({ page }) => {
  // ТЗ 8.4: отписка немедленная и от имени «Поддержки».
  await page.goto('/support');

  await page.getByRole('textbox', { name: 'Текст обращения' }).fill('Расписание не открывается');
  await page.getByRole('button', { name: 'Отправить' }).click();

  await expect(page.getByText('ПОДДЕРЖКА', { exact: true })).toBeVisible();
  await expect(page.getByText(SUPPORT_REPLIES.bug ?? '')).toBeVisible();
});

test('отписка соответствует выбранному типу', async ({ page }) => {
  // ТЗ 8.4: пул отписок свой у каждого типа.
  await page.goto('/support');

  await page.getByRole('button', { name: 'Есть идея по улучшению' }).click();
  await page.getByRole('textbox', { name: 'Текст обращения' }).fill('Добавьте экспорт дедлайнов');
  await page.getByRole('button', { name: 'Отправить' }).click();

  await expect(page.getByText(SUPPORT_REPLIES.idea ?? '')).toBeVisible();
});

test('пустое обращение не отправляется', async ({ page }) => {
  await page.goto('/support');

  await expect(page.getByRole('button', { name: 'Отправить' })).toBeDisabled();
});

test('прошлые обращения видны вместе с ответом', async ({ page }) => {
  // ТЗ 8.6: «сообщение ушло в пустоту» — ровно то ощущение, которое снимается.
  await page.goto('/support');
  await page
    .getByRole('textbox', { name: 'Текст обращения' })
    .fill('Первое обращение по расписанию');
  await page.getByRole('button', { name: 'Отправить' }).click();
  await expect(page.getByText('ПОДДЕРЖКА', { exact: true })).toBeVisible();

  await page.getByRole('textbox', { name: 'Текст обращения' }).fill('Второе обращение про баллы');
  await page.getByRole('button', { name: 'Отправить' }).click();

  await expect(page.getByText('ВАШИ ОБРАЩЕНИЯ')).toBeVisible();
  await expect(page.getByText('Первое обращение по расписанию')).toBeVisible();
});
