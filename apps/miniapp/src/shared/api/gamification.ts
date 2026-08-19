/**
 * Запросы блока 6 к Core API.
 *
 * Рейтинг общеплатформенный: ни вуза в запросе, ни вуза в ответе (уточнение
 * У19, инвариант 9 в CLAUDE.md). Если здесь когда-нибудь появится `vuz_id` —
 * это ошибка, а не расширение.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import { profileKeys } from './profile';
import type { components } from './schema';

export type Me = components['schemas']['MeOut'];
export type Leaderboard = components['schemas']['LeaderboardOut'];
export type LeaderboardRow = components['schemas']['LeaderboardRowOut'];
export type Reward = components['schemas']['RewardOut'];
export type RewardResult = components['schemas']['RewardResultOut'];

export const gamificationKeys = {
  all: ['gamification'] as const,
  me: ['gamification', 'me'] as const,
  leaderboard: ['gamification', 'leaderboard'] as const,
};

export function useGamificationMe() {
  return useQuery({
    queryKey: gamificationKeys.me,
    queryFn: async (): Promise<Me> => {
      const { data, error } = await api.GET('/api/v1/gamification/me');
      if (error || !data) throw new Error('не удалось загрузить баллы');
      return data;
    },
  });
}

export function useLeaderboard() {
  return useQuery({
    queryKey: gamificationKeys.leaderboard,
    queryFn: async (): Promise<Leaderboard> => {
      const { data, error } = await api.GET('/api/v1/gamification/leaderboard');
      if (error || !data) throw new Error('не удалось загрузить рейтинг');
      return data;
    },
  });
}

/** Обновляет всё, на что влияет изменение баланса. */
function refreshPoints(queryClient: ReturnType<typeof useQueryClient>) {
  void queryClient.invalidateQueries({ queryKey: gamificationKeys.all });
  // Баланс виден и в профиле — он единственный источник правды о нём.
  void queryClient.invalidateQueries({ queryKey: profileKeys.me });
}

export function useCheckIn() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST('/api/v1/gamification/checkin');
      if (error || !data) throw new Error('не удалось отметиться');
      return data;
    },
    onSuccess: () => {
      refreshPoints(queryClient);
    },
  });
}

export function useBuyReward() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (code: string): Promise<RewardResult> => {
      const { data, error } = await api.POST('/api/v1/gamification/rewards/{code}', {
        params: { path: { code } },
      });
      if (error || !data) throw new Error('не удалось обменять баллы');
      return data;
    },
    onSuccess: () => {
      refreshPoints(queryClient);
    },
  });
}
