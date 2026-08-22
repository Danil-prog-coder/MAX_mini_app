import { expect, test } from '@playwright/test';

import { APPLICANT_PROFILE, installApiStub, SPOTS } from './apiStub';

/**
 * Блок 7 глазами студента (ТЗ 7.2–7.6).
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

test.beforeEach(async ({ page }) => {
  await installApiStub(page);
});

test('раздел закрыт абитуриенту и ведёт на гейт', async ({ page }) => {
  // ТЗ 7.2: маршрут вместо отказа, с текстом именно про еду.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/food');

  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'gate');
  await expect(page.getByText(/Точки питания подбираются рядом с вашим вузом/)).toBeVisible();
});

test('точки показываются с адресом корпуса', async ({ page }) => {
  // ТЗ 7.3, 7.4: координаты вуза из профиля, топ-5 в пешей доступности.
  await page.goto('/food');

  await expect(page.getByText('В ПЕШЕЙ ДОСТУПНОСТИ')).toBeVisible();
  await expect(page.getByText(/от корпуса: Москва, Ленинские горы, 1/)).toBeVisible();
  for (const spot of SPOTS) {
    await expect(page.getByText(spot.name)).toBeVisible();
  }
});

test('у общепита и магазина разные наборы полей', async ({ page }) => {
  // ТЗ 7.5: у кафе меню и оценка, у магазина выпечка и ассортимент.
  await page.goto('/food');

  await expect(page.getByText('СТОЛОВАЯ · 4.4')).toBeVisible();
  await expect(page.getByText('комплексные обеды, супы, выпечка')).toBeVisible();
  await expect(page.getByText('Выпечка есть')).toBeVisible();
  await expect(page.getByText('Ассортимент средний')).toBeVisible();
});

test('каждая карточка ведёт на место в картах, а не в общий поиск', async ({ page }) => {
  // ТЗ 7.6.
  await page.goto('/food');

  const links = page.getByRole('link', { name: 'Открыть на карте' });
  await expect(links).toHaveCount(SPOTS.length);

  const hrefs = await links.evaluateAll((nodes) =>
    nodes.map((node) => (node as HTMLAnchorElement).href),
  );
  for (const href of hrefs) {
    // Уточнение У27: карта открывается на точке, а не на поиске по названию.
    expect(href).toContain('ll=');
    expect(href).toContain('pt=');
    expect(href).not.toContain('text=');
  }
  // И у каждой точки она своя, иначе «открыть на карте» везде одинаково.
  expect(new Set(hrefs).size).toBe(hrefs.length);
});

test('демонстрационные данные подписаны как демонстрационные', async ({ page }) => {
  // Уточнение У4: выдумку нельзя выдавать за данные карт.
  await page.goto('/food');

  await expect(page.getByText(/Названия и оценки точек демонстрационные/)).toBeVisible();
});

test('шкала близости читается вслух', async ({ page }) => {
  await page.goto('/food');

  await expect(page.getByLabel('Близость 5 из 5')).toBeVisible();
});
