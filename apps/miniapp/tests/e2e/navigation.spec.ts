import { expect, test, type Page } from '@playwright/test';

import { SCREENS } from '../../src/app/screens';
import { installApiStub } from './apiStub';

/**
 * Обязательный e2e (тех. ТЗ 9.5): обход **всех** зарегистрированных экранов с
 * проверкой, что на каждом есть кнопка «🏠 Главное меню». Это единственная
 * автоматическая проверка требования №1 продуктового ТЗ (п. 1.1) — она не
 * откладывается ни при каком объёме работ.
 *
 * Список экранов берётся из того же реестра, что и дерево роутов
 * (`src/app/screens.ts`), поэтому новый экран попадает под проверку сам, без
 * правки этого файла — забыть невозможно.
 *
 * Оба профиля устройств (мобильный и десктопный, см. `playwright.config.ts`)
 * прогоняются отдельно: кроссплатформенность — критерий приёмки (ТЗ 0.2).
 */

/** Нижняя панель: экраны тоже ведут в профиль, поэтому ищем строго в ней. */
function tabbar(page: Page) {
  return page.getByRole('navigation', { name: 'Основная навигация' });
}

function homeButton(page: Page) {
  return tabbar(page).getByRole('link', { name: 'Главное меню' });
}

/** Собирает ошибки страницы: белый экран вместо экрана — тоже нарушение п. 1.1. */
function collectErrors(page: Page): string[] {
  const errors: string[] = [];
  page.on('console', (message) => {
    if (message.type() === 'error') errors.push(message.text());
  });
  page.on('pageerror', (error) => errors.push(error.message));
  return errors;
}

async function hasHorizontalScroll(page: Page): Promise<boolean> {
  return page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
}

for (const screen of SCREENS) {
  test(`${screen.label}: выход в главное меню и вёрстка без горизонтального скролла`, async ({
    page,
  }) => {
    const errors = collectErrors(page);
    await installApiStub(page);

    await page.goto(screen.e2ePath);

    // Сначала — что обход попал именно на этот экран. Без этой проверки тест
    // остаётся зелёным, даже если все адреса свалились на «адрес не найден»:
    // кнопка «Главное меню» есть и там.
    await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', screen.id);

    await expect(homeButton(page)).toBeVisible();
    await expect(tabbar(page).getByRole('link', { name: 'Мой профиль' })).toBeVisible();

    // ТЗ 0.2: адаптивная вёрстка без горизонтального скролла и обрезанных
    // элементов — одинаково на телефоне и на ПК.
    expect(await hasHorizontalScroll(page)).toBe(false);

    expect(errors).toEqual([]);
  });
}

test('кнопка «Главное меню» возвращает в меню с любого экрана', async ({ page }) => {
  await installApiStub(page);
  await page.goto('/tracker/1');
  await expect(page.locator('[data-screen-id]')).toHaveAttribute(
    'data-screen-id',
    'tracker-detail',
  );

  await homeButton(page).click();

  await expect(page).toHaveURL('/');
  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'menu');
});

test('возврат в меню работает с клавиатуры', async ({ page }) => {
  // ТЗ 0.2: на десктопном клиенте MAX интерфейс обязан работать с клавиатуры
  // наравне с мышью, а не только по нажатию пальцем.
  await installApiStub(page);
  await page.goto('/support');
  await homeButton(page).focus();
  await page.keyboard.press('Enter');

  await expect(page).toHaveURL('/');
});

test('переход в меню не считается тупиком: из меню открываются разделы', async ({ page }) => {
  await installApiStub(page);
  await page.goto('/');
  await page.getByRole('link', { name: 'Профориентационный тест' }).click();
  await expect(page.locator('[data-screen-id]')).toHaveAttribute('data-screen-id', 'career-test');
});
