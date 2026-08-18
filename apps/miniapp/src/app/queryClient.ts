/**
 * Кэш серверного состояния.
 *
 * TanStack Query — единственный источник всего, что приходит с Core API
 * (тех. ТЗ 8.2). Zustand копий серверных данных не хранит: два источника
 * правды на фронте расходятся так же, как расходились бы на бэкенде.
 */
import { QueryClient } from '@tanstack/react-query';

/** Пауза перед повтором: 1с, 2с, 4с, но не больше 15с. */
function retryDelay(attempt: number): number {
  return Math.min(1000 * 2 ** attempt, 15_000);
}

export function createQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: 2,
        retryDelay,
        // Аудитория заходит с телефонов и не всегда с хорошей сети: лишний
        // рефетч на каждый фокус окна — это лишний трафик, а не свежесть.
        refetchOnWindowFocus: false,
        staleTime: 30_000,
      },
      mutations: {
        // Мутации не повторяются автоматически: повтор POST — это дубль
        // обращения в поддержку или дубль вопроса в ленте (тех. ТЗ 8.6).
        retry: false,
      },
    },
  });
}
