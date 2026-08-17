/**
 * Экран проверки связи — временная заглушка каркаса.
 *
 * Задача этого экрана одна: показать, что фронтенд собирается, поднимается и
 * достаёт Core API по настроенному адресу. На шаге «оболочка фронта» он целиком
 * заменяется на `AppLayout` с безусловной кнопкой «Главное меню» и дерево
 * из 16 экранов (тех. ТЗ 8.3).
 */
import { useEffect, useState } from 'react';

import { config } from '@/shared/config';

type Probe =
  | { readonly state: 'loading' }
  | { readonly state: 'ok'; readonly version: string }
  | { readonly state: 'error'; readonly reason: string };

export function App() {
  const [probe, setProbe] = useState<Probe>({ state: 'loading' });

  useEffect(() => {
    const controller = new AbortController();

    void (async () => {
      try {
        const response = await fetch(`${config.apiBaseUrl}/health`, {
          signal: controller.signal,
        });
        if (!response.ok) {
          setProbe({ state: 'error', reason: `HTTP ${String(response.status)}` });
          return;
        }
        const body = (await response.json()) as { version?: string };
        setProbe({ state: 'ok', version: body.version ?? 'неизвестна' });
      } catch (error) {
        if (controller.signal.aborted) return;
        setProbe({
          state: 'error',
          reason: error instanceof Error ? error.message : 'неизвестная ошибка',
        });
      }
    })();

    return () => {
      controller.abort();
    };
  }, []);

  return (
    <main className="mx-auto flex h-full max-w-[440px] flex-col justify-center gap-4 p-6">
      <h1 className="text-3xl font-bold">Навигатор</h1>
      <p className="text-sm text-neutral-600">
        Каркас монорепо. Экраны появятся на шаге «оболочка фронта».
      </p>
      <dl className="flex flex-col gap-2 rounded-2xl border p-4 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-neutral-600">Core API</dt>
          <dd className="text-right font-medium">{config.apiBaseUrl}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-neutral-600">Связь</dt>
          <dd className="text-right font-medium">
            {probe.state === 'loading' && 'проверяю…'}
            {probe.state === 'ok' && `есть, версия ${probe.version}`}
            {probe.state === 'error' && `нет: ${probe.reason}`}
          </dd>
        </div>
      </dl>
    </main>
  );
}
