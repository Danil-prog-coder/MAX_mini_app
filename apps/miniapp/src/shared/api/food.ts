/**
 * Запросы блока 7 к Core API.
 *
 * Раздел закрыт гейтом (ТЗ 7.2): 403 — не сбой, а маршрут на экран-гейт.
 * Геолокация не запрашивается ни здесь, ни где-либо ещё: координаты вуза берёт
 * сервер из справочника (ТЗ 7.3).
 */
import { useQuery } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Nearby = components['schemas']['NearbyOut'];
export type Spot = components['schemas']['SpotOut'];

/** Раздел закрыт по статусу: запрос отдаёт это значение вместо данных. */
export const CLOSED = 'closed' as const;
export type Closed = typeof CLOSED;

export const foodKeys = {
  all: ['food'] as const,
  nearby: ['food', 'nearby'] as const,
};

export function useNearby() {
  return useQuery({
    queryKey: foodKeys.nearby,
    queryFn: async (): Promise<Nearby | Closed> => {
      const { data, error, response } = await api.GET('/api/v1/food/nearby');
      if (response.status === 403) return CLOSED;
      if (error || !data) throw new Error('не удалось загрузить точки питания');
      return data;
    },
    // Зеркалит кэш бэкенда: там сутки на вуз (тех. ТЗ 3.8).
    staleTime: 60 * 60 * 1000,
  });
}
