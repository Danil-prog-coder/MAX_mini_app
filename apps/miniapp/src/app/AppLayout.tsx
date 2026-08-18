/**
 * Корпус приложения: рамка макета, область экрана и нижняя панель.
 *
 * Здесь выполняется требование №1 продуктового ТЗ (п. 1.1): кнопка
 * «🏠 Главное меню» рендерится **безусловно**, в общем layout-роуте, который
 * оборачивает все маршруты без исключения. Это архитектурная гарантия вместо
 * дисциплины: новый экран физически не может оказаться без кнопки возврата,
 * если он зарегистрирован в дереве роутов (тех. ТЗ 8.3).
 *
 * Переход в меню — обычная навигация без побочных эффектов: сохранённые данные
 * профиля и черновики сценариев он не сбрасывает (ТЗ 1.1).
 */
import { Link, Outlet, useLocation, useMatches } from 'react-router-dom';

import { HomeIcon, UserIcon } from '@/shared/ui/icons';

import type { ScreenId } from './screens';
import { useNativeBackButton } from './useNativeBackButton';

/** Данные, которые роут сообщает о себе layout-у. */
export interface ScreenHandle {
  readonly screenId: ScreenId;
}

function screenIdOf(handle: unknown): ScreenId | undefined {
  if (typeof handle !== 'object' || handle === null) return undefined;
  const { screenId } = handle as Partial<ScreenHandle>;
  return typeof screenId === 'string' ? screenId : undefined;
}

/** Общая часть классов кнопки профиля: различается только заливка. */
const PROFILE_BUTTON =
  'flex h-[54px] w-[54px] flex-none items-center justify-center rounded-full border-[1.5px] transition-colors';

export function AppLayout() {
  const { pathname } = useLocation();
  const matches = useMatches();
  useNativeBackButton();

  // Идентификатор экрана приходит из реестра роутов, а не задаётся вручную в
  // каждом экране: по нему e2e-тест проверяет, что обход дошёл именно туда,
  // куда собирался, а не свалился на экран «адрес не найден».
  const screenId = screenIdOf(matches.at(-1)?.handle);
  const isProfile = screenId === 'profile';
  const isMenu = screenId === 'menu';

  return (
    <div className="flex min-h-full items-center justify-center">
      <div className="relative h-[min(100dvh,940px)] w-[440px] max-w-[100vw] overflow-hidden rounded-[46px] bg-neutral-200 text-text shadow-frame max-[520px]:h-[100dvh] max-[520px]:w-[100vw] max-[520px]:rounded-none max-[520px]:shadow-none">
        <main
          // key по адресу: смена экрана переигрывает анимацию входа `nvIn`
          // (хендофф, «Анимации»).
          key={pathname}
          data-screen-id={screenId}
          className="animate-screen-in absolute inset-x-0 top-0 bottom-[var(--tabbar-height)] overflow-y-auto px-[22px] pt-6 pb-7 [scrollbar-width:none] [&::-webkit-scrollbar]:hidden"
        >
          <Outlet />
        </main>

        <nav
          aria-label="Основная навигация"
          // Градиент от прозрачного к фону: контент уходит под панель мягко.
          // Интерполяция градиента идёт с предумноженной альфой, поэтому
          // `transparent` не даёт серого «провала» на светлом фоне.
          className="absolute inset-x-0 bottom-0 flex h-[var(--tabbar-height)] items-center gap-[10px] bg-[linear-gradient(180deg,transparent,var(--color-neutral-200)_34%)] px-[22px] pb-[calc(12px+env(safe-area-inset-bottom,0px))]"
        >
          <Link
            to="/"
            aria-current={isMenu ? 'page' : undefined}
            className="flex h-[54px] flex-1 items-center justify-center gap-[9px] rounded-full bg-text text-[13px] font-semibold tracking-[0.06em] text-neutral-200 transition-colors hover:bg-neutral-800"
          >
            <HomeIcon />
            Главное меню
          </Link>
          <Link
            to="/profile"
            aria-label="Мой профиль"
            aria-current={isProfile ? 'page' : undefined}
            className={
              isProfile
                ? `${PROFILE_BUTTON} border-transparent bg-text text-neutral-200 hover:bg-neutral-800`
                : `${PROFILE_BUTTON} border-neutral-400 text-text hover:bg-text/6`
            }
          >
            <UserIcon />
          </Link>
        </nav>
      </div>
    </div>
  );
}
