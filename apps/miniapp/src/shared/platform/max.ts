/**
 * Адаптер платформы MAX — единственное место фронтенда, которое знает, как
 * устроен мост к мессенджеру.
 *
 * Причина изоляции в тех. ТЗ 9.7: публичного npm-пакета SDK мини-приложения
 * нет, точный формат `initData` и API нативной кнопки «назад» лежат в закрытой
 * документации `dev.max.ru` и первичными источниками не подтверждены. Поэтому
 * здесь нет импорта пакета: мост ищется как глобальный объект — по вторичным
 * данным он подключается скриптом платформы и называется `window.WebApp`.
 *
 * Все функции обязаны работать и без моста: приложение открывается в обычном
 * браузере в режиме `MOCK_AUTH` (тех. ТЗ 9.3), и это штатный режим разработки,
 * а не ошибка. Отсюда же правило «ничего не бросаем наружу»: неизвестная и
 * непроверенная реализация моста не должна ронять экран.
 */

/** Кнопка «назад» клиента MAX. Форма API не подтверждена — см. docstring. */
interface NativeBackButton {
  show?: () => void;
  hide?: () => void;
  onClick?: (handler: () => void) => void;
  offClick?: (handler: () => void) => void;
}

interface MaxBridge {
  /** Подписанная строка инициализации; её проверяет бэкенд, не клиент. */
  initData?: string;
  initDataUnsafe?: {
    user?: { first_name?: string; last_name?: string; name?: string };
  };
  BackButton?: NativeBackButton;
}

declare global {
  interface Window {
    WebApp?: MaxBridge;
  }
}

function bridge(): MaxBridge | undefined {
  return typeof window === 'undefined' ? undefined : window.WebApp;
}

/**
 * Вызов метода моста, который не должен ронять приложение.
 *
 * Мост непроверенный: метод может отсутствовать или бросить. Это не повод
 * закрывать пользователю экран, поэтому ошибка гасится с записью в консоль —
 * она пригодится при первом запуске внутри настоящего клиента MAX.
 */
function safely(what: string, action: () => void): void {
  try {
    action();
  } catch (error) {
    console.warn(`[platform] ${what} не удалось`, error);
  }
}

/** Данные инициализации от платформы или `null`, если моста нет. */
export function getInitData(): string | null {
  const value = bridge()?.initData;
  return typeof value === 'string' && value !== '' ? value : null;
}

/**
 * Имя пользователя из профиля MAX (уточнение У6).
 *
 * Если платформа имени не отдаёт — `null`, и приложение попросит ввести имя
 * самому. Данные из `initDataUnsafe` не подписаны, поэтому используются только
 * для показа: источник правды о профиле — ответ Core API (ТЗ 1.3).
 */
export function getDisplayName(): string | null {
  const user = bridge()?.initDataUnsafe?.user;
  if (!user) return null;
  const composed = user.name ?? [user.first_name, user.last_name].filter(Boolean).join(' ');
  const trimmed = composed.trim();
  return trimmed === '' ? null : trimmed;
}

/**
 * Нативная кнопка «назад» клиента MAX.
 *
 * Синхронизируется с историей React Router (тех. ТЗ 8.3): показывается везде,
 * кроме главного меню. Без моста все методы — no-op.
 */
export const nativeBackButton = {
  show(): void {
    const button = bridge()?.BackButton;
    if (button?.show) safely('BackButton.show', () => button.show?.());
  },
  hide(): void {
    const button = bridge()?.BackButton;
    if (button?.hide) safely('BackButton.hide', () => button.hide?.());
  },
  /** Возвращает функцию отписки: снимать обработчик обязан вызывающий. */
  onClick(handler: () => void): () => void {
    const button = bridge()?.BackButton;
    if (!button?.onClick) return () => undefined;
    safely('BackButton.onClick', () => button.onClick?.(handler));
    return () => {
      if (button.offClick) safely('BackButton.offClick', () => button.offClick?.(handler));
    };
  },
};
