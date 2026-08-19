/**
 * Адаптер платформы обязан вести себя предсказуемо в трёх состояниях: моста
 * нет (обычный браузер, режим MOCK_AUTH), мост есть и отвечает, мост есть и
 * сломан. Третье не гипотетическое: реализация моста не подтверждена
 * документацией (тех. ТЗ 9.7), и её поведение мы не контролируем.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { getDisplayName, getInitData, nativeBackButton } from './max';

afterEach(() => {
  delete window.WebApp;
  vi.restoreAllMocks();
});

describe('данные инициализации', () => {
  it('без моста возвращают null — приложение открыто в браузере', () => {
    expect(getInitData()).toBeNull();
  });

  it('пустую строку считают отсутствием подписи', () => {
    window.WebApp = { initData: '' };
    expect(getInitData()).toBeNull();
  });

  it('возвращают строку моста как есть: проверяет её бэкенд', () => {
    window.WebApp = { initData: 'user=1&hash=abc' };
    expect(getInitData()).toBe('user=1&hash=abc');
  });
});

describe('имя пользователя (уточнение У6)', () => {
  it('без моста отсутствует — приложение попросит ввести его самому', () => {
    expect(getDisplayName()).toBeNull();
  });

  it('собирается из имени и фамилии', () => {
    window.WebApp = { initDataUnsafe: { user: { first_name: 'Артём', last_name: 'Волков' } } };
    expect(getDisplayName()).toBe('Артём Волков');
  });

  it('обходится одним именем, если фамилии нет', () => {
    window.WebApp = { initDataUnsafe: { user: { first_name: 'Артём' } } };
    expect(getDisplayName()).toBe('Артём');
  });

  it('считает пустое имя отсутствующим', () => {
    window.WebApp = { initDataUnsafe: { user: { first_name: '   ' } } };
    expect(getDisplayName()).toBeNull();
  });
});

describe('нативная кнопка «назад»', () => {
  it('без моста не падает и отписка ничего не делает', () => {
    expect(() => {
      nativeBackButton.show();
      nativeBackButton.hide();
      nativeBackButton.onClick(() => undefined)();
    }).not.toThrow();
  });

  it('прокидывает обработчик в мост и снимает его отпиской', () => {
    const onClick = vi.fn();
    const offClick = vi.fn();
    window.WebApp = { BackButton: { onClick, offClick } };
    const handler = () => undefined;

    const unsubscribe = nativeBackButton.onClick(handler);
    expect(onClick).toHaveBeenCalledWith(handler);

    unsubscribe();
    expect(offClick).toHaveBeenCalledWith(handler);
  });

  it('переживает мост, который бросает исключение', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => undefined);
    window.WebApp = {
      BackButton: {
        show: () => {
          throw new Error('мост не готов');
        },
      },
    };

    expect(() => {
      nativeBackButton.show();
    }).not.toThrow();
    expect(warn).toHaveBeenCalled();
  });
});
