/**
 * Обёртка провайдерами для компонентных тестов.
 *
 * Экраны читают серверное состояние через TanStack Query, поэтому без
 * `QueryClientProvider` они падают на первом же хуке. Клиент создаётся свой на
 * каждый рендер: общий переносил бы кэш между тестами.
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      // Без повторов: в тесте отказ должен становиться отказом сразу, а не
      // через три попытки и таймауты.
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
}

export function withProviders(children: ReactNode) {
  return <QueryClientProvider client={createTestQueryClient()}>{children}</QueryClientProvider>;
}
