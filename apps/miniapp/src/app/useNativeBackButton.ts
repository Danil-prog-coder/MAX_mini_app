/**
 * Синхронизация нативной кнопки «назад» клиента MAX с историей роутера
 * (тех. ТЗ 8.3): кнопка показывается везде, кроме главного меню, и по нажатию
 * делает шаг назад по истории React Router.
 *
 * Без моста платформы все вызовы — no-op (см. `shared/platform/max`), поэтому
 * хук безопасно работает и в обычном браузере, и в тестах.
 */
import { useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { nativeBackButton } from '@/shared/platform/max';

export function useNativeBackButton(): void {
  const navigate = useNavigate();
  const { pathname } = useLocation();

  useEffect(() => {
    if (pathname === '/') {
      nativeBackButton.hide();
      return;
    }

    nativeBackButton.show();
    const unsubscribe = nativeBackButton.onClick(() => {
      void navigate(-1);
    });

    return () => {
      unsubscribe();
      nativeBackButton.hide();
    };
  }, [pathname, navigate]);
}
