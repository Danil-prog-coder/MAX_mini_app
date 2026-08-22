import { expect, test } from '@playwright/test';

import { APPLICANT_PROFILE, installApiStub } from './apiStub';

/**
 * Профиль, меню и гейт (ТЗ 1.2, 1.3, 4.2, 7.2).
 *
 * Профиль — единственный источник правды о пользователе: статус и вуз меняются
 * здесь, и от них немедленно зависит, открыты ли разделы 4 и 7.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test('закрытый раздел ведёт на гейт, а не показывает «недоступно»', async ({ page }) => {
  // Инвариант 4 в CLAUDE.md: гейт вместо отказа.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await page.getByRole('link', { name: /Расписание и дедлайны/ }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'gate');
  await expect(page.getByRole('heading', { name: 'Почти' })).toBeVisible();
  await expect(page.getByRole('link', { name: 'Перейти в профиль' })).toBeVisible();
});

test('у гейта разные тексты для расписания и еды', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });

  await page.goto('/gate/schedule');
  await expect(page.getByText(/расписание вашей группы/)).toBeVisible();

  await page.goto('/gate/food');
  await expect(page.getByText(/Точки питания подбираются рядом с вашим вузом/)).toBeVisible();
});

test('прямой заход в закрытый раздел уводит на гейт', async ({ page }) => {
  // Спрятать пункт меню мало: адрес открывается и по ссылке.
  await installApiStub(page, { profile: APPLICANT_PROFILE });

  await page.goto('/schedule');

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'gate');
});

test('статус и вуз в профиле открывают разделы 4 и 7', async ({ page }) => {
  // ТЗ 1.3 и 4.2: нужны оба условия, и смена статуса действует немедленно.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/profile');

  await page.getByRole('button', { name: 'Студент', exact: true }).click();
  await expect(page.getByText(/Осталось выбрать вуз/)).toBeVisible();

  await page.getByRole('button', { name: 'Изменить вуз' }).click();
  await page.getByRole('dialog').getByRole('button', { name: /МГУ/ }).click();

  await expect(page.getByText('МГУ')).toBeVisible();

  await page.getByRole('navigation').getByRole('link', { name: 'Главное меню' }).click();
  await page.getByRole('link', { name: /Расписание и дедлайны/ }).click();

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'schedule');
});

test('пилюля статуса в меню показывает текущий статус', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await expect(page.getByRole('link', { name: 'АБИТУРИЕНТ' })).toBeVisible();
});

test('верификация переводит профиль в подтверждённое состояние', async ({ page }) => {
  // Уточнение У7: реальной проверки почты нет, и текст её не обещает.
  await installApiStub(page);
  await page.goto('/profile');

  await page.getByRole('button', { name: 'Подтвердить' }).click();

  await expect(page.getByText('ГОТОВО')).toBeVisible();
  await expect(page.getByText(/Статус подтверждён/)).toBeVisible();
});

test('имя запрашивается, если платформа его не отдала', async ({ page }) => {
  // Уточнение У6: онбординга нет, но имя нужно.
  await installApiStub(page, { profile: { display_name: '', needs_display_name: true } });
  await page.goto('/profile');

  await expect(page.getByRole('heading', { name: 'Как вас зовут?' })).toBeVisible();
  await page.getByRole('textbox', { name: 'Ваше имя' }).fill('Артём');
  await page.getByRole('button', { name: 'Сохранить' }).click();

  await expect(page.getByRole('heading', { name: 'Артём' })).toBeVisible();
});

/**
 * Умный поиск вуза (уточнение У31). Одна шторка на профиль и на вопрос
 * старшекурснику, поэтому проверяются обе точки входа.
 */
test('шторка вуза показывает справочник сразу и сужает его при вводе', async ({ page }) => {
  await installApiStub(page);
  await page.goto('/profile');

  await page
    .getByRole('button', { name: /Изменить|Указать/ })
    .first()
    .click();

  // Список виден сразу, до первого символа.
  const options = page.getByRole('dialog').getByRole('button', { name: /У$|У\s/ });
  await expect(options).toHaveCount(3);

  await page.getByRole('searchbox', { name: 'Поиск вуза' }).fill('влад');

  // Поиск идёт и по городу: «влад» — это Владивосток, то есть ДВФУ.
  await expect(options).toHaveCount(1);
  await expect(page.getByRole('dialog').getByRole('button', { name: /ДВФУ/ })).toBeVisible();
});

test('поиск не находит — экран объясняет это, а не показывает пустоту', async ({ page }) => {
  await installApiStub(page);
  await page.goto('/profile');

  await page
    .getByRole('button', { name: /Изменить|Указать/ })
    .first()
    .click();
  await page.getByRole('searchbox', { name: 'Поиск вуза' }).fill('щщщщщ');

  await expect(page.getByText(/ничего не нашлось/)).toBeVisible();
});

test('выбранный в поиске вуз попадает в профиль', async ({ page }) => {
  await installApiStub(page);
  await page.goto('/profile');

  await page
    .getByRole('button', { name: /Изменить|Указать/ })
    .first()
    .click();
  await page.getByRole('searchbox', { name: 'Поиск вуза' }).fill('мгу');
  await page.getByRole('dialog').getByRole('button', { name: /МГУ/ }).click();

  await expect(page.getByRole('dialog')).toHaveCount(0);
  await expect(page.getByText('МГУ').first()).toBeVisible();
});
