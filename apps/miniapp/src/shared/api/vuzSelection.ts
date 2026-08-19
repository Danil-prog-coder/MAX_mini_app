/**
 * Запросы блока 2 к Core API.
 *
 * Баллы ЕГЭ хранятся на сервере и живут в TanStack Query (тех. ТЗ 8.2):
 * требование ТЗ 2.4 «выход в меню не теряет введённое» выполняется не
 * локальным черновиком, а тем, что баллы вообще не лежат на клиенте. Заодно
 * это закрывает ТЗ 0.2: человек ввёл баллы с телефона и видит их на десктопе.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Subjects = components['schemas']['SubjectsOut'];
export type Direction = components['schemas']['DirectionOut'];
export type ExamScores = components['schemas']['ExamScoresOut'];
export type Matches = components['schemas']['MatchesOut'];
export type Match = components['schemas']['MatchOut'];
export type Chance = components['schemas']['Chance'];
export type UniversityCard = components['schemas']['UniversityCardOut'];
export type Tracked = components['schemas']['TrackedOut'];

export const vuzSelectionKeys = {
  subjects: ['vuz-selection', 'subjects'] as const,
  directions: ['vuz-selection', 'directions'] as const,
  scores: ['vuz-selection', 'scores'] as const,
  matches: ['vuz-selection', 'matches'] as const,
  university: (id: number) => ['vuz-selection', 'university', id] as const,
};

export function useSubjects() {
  return useQuery({
    queryKey: vuzSelectionKeys.subjects,
    queryFn: async (): Promise<Subjects> => {
      const { data, error } = await api.GET('/api/v1/vuz-selection/subjects');
      if (error || !data) throw new Error('не удалось загрузить список предметов');
      return data;
    },
    // Справочник предметов меняется раз в никогда.
    staleTime: 60 * 60 * 1000,
  });
}

export function useDirections() {
  return useQuery({
    queryKey: vuzSelectionKeys.directions,
    queryFn: async (): Promise<Direction[]> => {
      const { data, error } = await api.GET('/api/v1/vuz-selection/directions');
      if (error || !data) throw new Error('не удалось загрузить справочник направлений');
      return data;
    },
    staleTime: 60 * 60 * 1000,
  });
}

export function useScores() {
  return useQuery({
    queryKey: vuzSelectionKeys.scores,
    queryFn: async (): Promise<ExamScores> => {
      const { data, error } = await api.GET('/api/v1/vuz-selection/scores');
      if (error || !data) throw new Error('не удалось загрузить баллы');
      return data;
    },
  });
}

export function useSaveScores() {
  const queryClient = useQueryClient();
  return useMutation({
    // Кэш обновляется внутри `mutationFn`, а не в `onSuccess`, намеренно:
    // экран досохраняет баллы при размонтировании (ТЗ 2.4), а к этому моменту
    // наблюдатель мутации уже отписан и его `onSuccess` не вызовется.
    mutationFn: async (scores: Record<string, number>): Promise<ExamScores> => {
      const { data, error } = await api.POST('/api/v1/vuz-selection/scores', {
        body: { scores },
      });
      if (error || !data) throw new Error('не удалось сохранить баллы');
      queryClient.setQueryData(vuzSelectionKeys.scores, data);
      // Подбор считается от баллов: старая выдача после их изменения врёт.
      void queryClient.invalidateQueries({ queryKey: ['vuz-selection', 'matches'] });
      void queryClient.invalidateQueries({ queryKey: ['vuz-selection', 'university'] });
      return data;
    },
  });
}

export function useMatches() {
  return useQuery({
    queryKey: vuzSelectionKeys.matches,
    queryFn: async (): Promise<Matches> => {
      const { data, error } = await api.GET('/api/v1/vuz-selection/matches');
      if (error || !data) throw new Error('не удалось подобрать вузы');
      return data;
    },
  });
}

export function useUniversityCard(universityId: number | null) {
  return useQuery({
    queryKey: vuzSelectionKeys.university(universityId ?? 0),
    enabled: universityId !== null,
    queryFn: async (): Promise<UniversityCard | null> => {
      const { data, error, response } = await api.GET(
        '/api/v1/vuz-selection/universities/{university_id}',
        { params: { path: { university_id: universityId ?? 0 } } },
      );
      // 404 — не сбой, а «такого вуза нет»: экран покажет это словами и
      // оставит выход, а не сообщение об ошибке связи (ТЗ 1.1).
      if (response.status === 404) return null;
      if (error || !data) throw new Error('не удалось загрузить карточку вуза');
      return data;
    },
  });
}

export function useTrackUniversity() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      universityId,
      direction,
    }: {
      universityId: number;
      direction?: string | null;
    }): Promise<Tracked> => {
      const { data, error } = await api.POST('/api/v1/vuz-selection/track/{university_id}', {
        params: { path: { university_id: universityId } },
        body: { direction: direction ?? null },
      });
      if (error || !data) throw new Error('не удалось добавить вуз в отслеживаемые');
      return data;
    },
    onSuccess: (_tracked, { universityId }) => {
      void queryClient.invalidateQueries({ queryKey: vuzSelectionKeys.university(universityId) });
      // Список трекера читает блок 3 — он должен увидеть новый вуз.
      void queryClient.invalidateQueries({ queryKey: ['tracker'] });
    },
  });
}
