/**
 * Реестр экранов должен быть согласован сам с собой: иначе e2e-обход всех
 * роутов проверяет не то, что думает.
 *
 * Главная ловушка: если `e2ePath` не совпадает ни с одним роутом, React Router
 * отдаст экран «адрес не найден» — а на нём кнопка «Главное меню» тоже есть, и
 * e2e пройдёт, ничего не проверив. Поэтому здесь сверяется, что каждый адрес
 * обхода попадает именно в свой экран.
 */
import { matchRoutes } from 'react-router-dom';
import { describe, expect, it } from 'vitest';

import { buildRoutes } from './router';
import { SCREENS } from './screens';

const routes = buildRoutes();

function screenIdAt(pathname: string): string | undefined {
  const matches = matchRoutes(routes, pathname);
  const handle = matches?.at(-1)?.route.handle as { screenId?: string } | undefined;
  return handle?.screenId;
}

describe('реестр экранов', () => {
  it('содержит шестнадцать экранов макета и экран «адрес не найден»', () => {
    expect(SCREENS).toHaveLength(17);
  });

  it('не повторяет идентификаторы и пути', () => {
    expect(new Set(SCREENS.map((screen) => screen.id)).size).toBe(SCREENS.length);
    expect(new Set(SCREENS.map((screen) => screen.path)).size).toBe(SCREENS.length);
  });

  it.each(SCREENS.map((screen) => [screen.id, screen.e2ePath] as const))(
    'адрес обхода %s (%s) открывает именно этот экран',
    (id, e2ePath) => {
      expect(screenIdAt(e2ePath)).toBe(id);
    },
  );

  it('статические адреса не перехватываются роутами с параметром', () => {
    // `/vuz-selection/results` и `/vuz-selection/:universityId` различаются
    // только приоритетом сегментов — сломать это легко, заметить трудно.
    expect(screenIdAt('/vuz-selection/results')).toBe('vuz-selection-results');
    expect(screenIdAt('/career-test/results')).toBe('career-test-results');
  });

  it('неизвестный адрес ведёт на экран «адрес не найден», а не в пустоту', () => {
    expect(screenIdAt('/чего-то-такого-нет/точно')).toBe('not-found');
  });
});
