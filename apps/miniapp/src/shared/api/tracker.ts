/**
 * Запросы блока 3 к Core API.
 *
 * Вузы попадают в трекер из блока 2 (ТЗ 3.2), поэтому после добавления
 * отслеживания список надо перечитать — за это отвечает `useTrackUniversity`
 * в `vuzSelection.ts`, инвалидирующая ключ `['tracker']`.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type TrackedList = components['schemas']['TrackedListOut'];
export type TrackedItem = components['schemas']['TrackedItemOut'];
export type Positions = components['schemas']['PositionsOut'];
export type WeekPoint = components['schemas']['WeekPointOut'];

export const trackerKeys = {
  all: ['tracker'] as const,
  list: ['tracker', 'list'] as const,
  positions: (universityId: number) => ['tracker', 'positions', universityId] as const,
};

export function useTracked() {
  return useQuery({
    queryKey: trackerKeys.list,
    queryFn: async (): Promise<TrackedList> => {
      const { data, error } = await api.GET('/api/v1/tracker');
      if (error || !data) throw new Error('не удалось загрузить список отслеживаемых вузов');
      return data;
    },
  });
}

export function usePositions(universityId: number | null) {
  return useQuery({
    queryKey: trackerKeys.positions(universityId ?? 0),
    enabled: universityId !== null,
    queryFn: async (): Promise<Positions | null> => {
      const { data, error, response } = await api.GET('/api/v1/tracker/{university_id}/positions', {
        params: { path: { university_id: universityId ?? 0 } },
      });
      // 404 — не сбой, а «этот вуз не отслеживается»: экран скажет это словами
      // и оставит выход в трекер (ТЗ 1.1).
      if (response.status === 404) return null;
      if (error || !data) throw new Error('не удалось загрузить позицию в списке');
      return data;
    },
  });
}

export function useSavePosition(universityId: number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (position: number): Promise<Positions> => {
      const { data, error } = await api.POST('/api/v1/tracker/{university_id}/positions', {
        params: { path: { university_id: universityId ?? 0 } },
        body: { position },
      });
      if (error || !data) throw new Error('не удалось сохранить позицию');
      return data;
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(trackerKeys.positions(universityId ?? 0), saved);
      // В списке трекера у карточки появляется число — его надо перечитать.
      void queryClient.invalidateQueries({ queryKey: trackerKeys.list });
    },
  });
}
