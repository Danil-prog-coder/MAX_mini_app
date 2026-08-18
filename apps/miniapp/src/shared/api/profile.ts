/**
 * Профиль пользователя — единственный источник правды о нём (ТЗ 1.3, 3).
 *
 * Все экраны читают статус, вуз и баллы отсюда и нигде их не дублируют.
 */
import { useQuery } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Profile = components['schemas']['ProfileOut'];
export type UserStatus = components['schemas']['UserStatus'];

export const profileKeys = {
  me: ['users', 'me'] as const,
  universities: ['users', 'universities'] as const,
};

export function useProfile() {
  return useQuery({
    queryKey: profileKeys.me,
    queryFn: async (): Promise<Profile> => {
      const { data, error } = await api.GET('/api/v1/users/me');
      if (error || !data) throw new Error('не удалось загрузить профиль');
      return data;
    },
  });
}
