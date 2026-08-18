/**
 * Требование №1 продуктового ТЗ (п. 1.1): кнопка «Главное меню» есть на каждом
 * экране без исключений.
 *
 * Это быстрая проверка того же инварианта, что и обязательный e2e-обход
 * (тех. ТЗ 9.5): здесь она ловит поломку за секунду и без браузера, а e2e
 * доказывает то же самое в настоящем клиенте на двух профилях устройств.
 */
import { render, screen, within } from '@testing-library/react';
import { createMemoryRouter, RouterProvider } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { withProviders } from '@/test/providers';

import { buildRoutes } from './router';
import { SCREENS } from './screens';

/** Нижняя панель. Экраны тоже ведут в профиль, поэтому ищем строго в ней. */
function tabbar() {
  return within(screen.getByRole('navigation', { name: 'Основная навигация' }));
}

function renderAt(pathname: string) {
  const router = createMemoryRouter(buildRoutes(), { initialEntries: [pathname] });
  // Экраны читают серверное состояние через TanStack Query: без провайдера
  // они падают, и проверка кнопки «Главное меню» ничего не покажет.
  return render(withProviders(<RouterProvider router={router} />));
}

describe('оболочка приложения', () => {
  it.each(SCREENS.map((s) => [s.id, s.e2ePath] as const))(
    'на экране %s (%s) есть кнопка «Главное меню» и кнопка профиля',
    (id, e2ePath) => {
      renderAt(e2ePath);

      expect(tabbar().getByRole('link', { name: 'Главное меню' })).toHaveAttribute('href', '/');
      expect(tabbar().getByRole('link', { name: 'Мой профиль' })).toHaveAttribute(
        'href',
        '/profile',
      );
      expect(document.querySelector('[data-screen-id]')).toHaveAttribute('data-screen-id', id);
    },
  );

  it('на экране профиля кнопка профиля помечена как текущая страница', () => {
    renderAt('/profile');
    expect(tabbar().getByRole('link', { name: 'Мой профиль' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });

  it('вне профиля пометки текущей страницы нет', () => {
    renderAt('/support');
    expect(tabbar().getByRole('link', { name: 'Мой профиль' })).not.toHaveAttribute('aria-current');
    expect(tabbar().getByRole('link', { name: 'Главное меню' })).not.toHaveAttribute(
      'aria-current',
    );
  });

  it('в главном меню кнопка меню помечена как текущая страница', () => {
    renderAt('/');
    expect(tabbar().getByRole('link', { name: 'Главное меню' })).toHaveAttribute(
      'aria-current',
      'page',
    );
  });
});
