import { expect, test, type Page } from '@playwright/test';

import { APPLICANT_PROFILE, installApiStub } from './apiStub';

/**
 * Календарь-решётка на главном экране (уточнения У10, У32).
 *
 * Этот файл появился после приёмки, на которой выяснилось, что календаря на
 * главной просто нет: обход роутов был зелёным, потому что проверял кнопку
 * «Главное меню», а не содержимое экрана. Отсюда правило — у главного элемента
 * экрана должен быть свой тест.
 *
 * Даты настоящие, поэтому тесты считают их от сегодняшнего дня, а не берут из
 * макета: иначе сюита позеленела бы ровно один месяц в году.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

const MONTHS_GENITIVE = [
  'января',
  'февраля',
  'марта',
  'апреля',
  'мая',
  'июня',
  'июля',
  'августа',
  'сентября',
  'октября',
  'ноября',
  'декабря',
];

/** Дата в формате API — как её собирает и сам экран. */
function iso(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${String(date.getFullYear())}-${month}-${day}`;
}

/** Подпись кнопки дня: «25 августа». */
function dayLabel(date: Date): string {
  return `${String(date.getDate())} ${MONTHS_GENITIVE[date.getMonth()] ?? ''}`;
}

/**
 * День текущего месяца, до которого гарантированно можно доскроллить и в
 * который можно поставить событие: не сегодня и не в прошлом.
 */
function futureDayThisMonth(): Date {
  const today = new Date();
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();
  // Хвост месяца оставляем в покое: 28-е есть в любом месяце.
  const day = today.getDate() < 28 ? today.getDate() + 1 : Math.min(daysInMonth, 28);
  return new Date(today.getFullYear(), today.getMonth(), day);
}

async function openDay(page: Page, date: Date): Promise<void> {
  await page.getByRole('button', { name: new RegExp(`^${dayLabel(date)}`) }).click();
}

test('на главной есть календарь с сеткой текущего месяца', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  const today = new Date();
  const daysInMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0).getDate();

  await expect(page.getByText(String(today.getFullYear()), { exact: true })).toBeVisible();
  await expect(
    page.getByRole('button', { name: new RegExp(MONTHS_GENITIVE[today.getMonth()] ?? '') }),
  ).toHaveCount(daysInMonth);
  await expect(page.getByText(/Нажмите на день/)).toBeVisible();
});

test('день с событиями показывает их в шторке', async ({ page }) => {
  const day = futureDayThisMonth();
  await installApiStub(page, {
    profile: APPLICANT_PROFILE,
    calendarEvents: [
      {
        day: iso(day),
        title: 'Последний день приёма документов',
        note: 'МГУ · вуз в вашем трекере',
        kind: 'admission',
        event_id: null,
      },
    ],
  });
  await page.goto('/');

  await openDay(page, day);

  const sheet = page.getByRole('dialog');
  await expect(sheet).toContainText('Последний день приёма документов');
  await expect(sheet).toContainText('вуз в вашем трекере');
  // Чужое событие удалить нельзя: кнопки нет.
  await expect(sheet.getByRole('button', { name: 'Удалить' })).toHaveCount(0);
});

test('день без событий не выглядит ошибкой и предлагает добавить своё', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await openDay(page, futureDayThisMonth());

  await expect(page.getByRole('dialog')).toContainText('Ничего не запланировано');
  await expect(page.getByRole('button', { name: 'Добавить событие' })).toBeVisible();
});

test('событие добавляется прямо в календаре и день меняет цвет', async ({ page }) => {
  // Главная просьба заказчика (уточнение У32): завести событие, не уходя с
  // главного экрана, и сразу увидеть это в сетке.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  const day = futureDayThisMonth();
  const dot = page.getByRole('button', { name: new RegExp(`^${dayLabel(day)}`) });
  await expect(dot).toHaveAttribute('aria-label', dayLabel(day));

  await dot.click();
  await page.getByRole('button', { name: 'Добавить событие' }).click();
  await page.getByRole('textbox', { name: 'Название события' }).fill('Курсовая по базам данных');
  await page.getByRole('button', { name: 'Добавить' }).click();

  await expect(page.getByRole('dialog')).toContainText('Курсовая по базам данных');

  // Шторку нужно закрыть: пока она открыта, фон помечен aria-hidden, и точки
  // дней просто не видны дереву доступности — как и человеку.
  await page.keyboard.press('Escape');
  await expect(page.getByRole('dialog')).toHaveCount(0);

  // Подпись дня теперь говорит о событиях — это и есть смена состояния точки.
  await expect(page.getByRole('button', { name: `${dayLabel(day)}, есть события` })).toBeVisible();
});

test('своё событие можно удалить', async ({ page }) => {
  const day = futureDayThisMonth();
  await installApiStub(page, {
    profile: APPLICANT_PROFILE,
    calendarEvents: [
      {
        day: iso(day),
        title: 'Отчёт по практике',
        note: 'ваше событие · напомню за сутки',
        kind: 'personal',
        event_id: 901,
      },
    ],
  });
  await page.goto('/');

  await openDay(page, day);
  await page.getByRole('button', { name: 'Удалить' }).click();

  await expect(page.getByRole('dialog')).toContainText('Ничего не запланировано');
});

test('пустое название не отправляется', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  await openDay(page, futureDayThisMonth());
  await page.getByRole('button', { name: 'Добавить событие' }).click();

  await expect(page.getByRole('button', { name: 'Добавить', exact: true })).toBeDisabled();
});

test('стрелки листают месяцы, включая переход через год', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/');

  const today = new Date();
  // Двенадцать шагов вперёд — это тот же месяц через год: проверка, что
  // листание не упирается в конец года и не сбрасывает год.
  for (let step = 0; step < 12; step++) {
    await page.getByRole('button', { name: 'Следующий месяц' }).click();
  }

  await expect(page.getByText(String(today.getFullYear() + 1), { exact: true })).toBeVisible();
});
