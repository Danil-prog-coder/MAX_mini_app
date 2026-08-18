/**
 * Профиль пользователя — единственный источник правды о нём (ТЗ 1.3, 3).
 *
 * Все экраны читают статус, вуз и баллы отсюда и нигде их не дублируют.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Profile = components['schemas']['ProfileOut'];
export type UserStatus = components['schemas']['UserStatus'];
export type University = components['schemas']['UniversityOut'];
export type ProfileUpdate = components['schemas']['ProfileUpdateIn'];

/** Подписи статусов — из макета, экран «Мой профиль». */
export const STATUS_LABELS: Record<UserStatus, string> = {
  school: 'Школьник',
  applicant: 'Абитуриент',
  student: 'Студент',
};

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

export function useUniversities() {
  return useQuery({
    queryKey: profileKeys.universities,
    queryFn: async (): Promise<University[]> => {
      const { data, error } = await api.GET('/api/v1/universities');
      if (error || !data) throw new Error('не удалось загрузить справочник вузов');
      return data;
    },
    // Справочник курируется в репозитории и меняется релизами, а не в рантайме.
    staleTime: 60 * 60 * 1000,
  });
}

export function useUpdateProfile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (patch: ProfileUpdate): Promise<Profile> => {
      const { data, error } = await api.PATCH('/api/v1/users/me', { body: patch });
      if (error || !data) throw new Error('не удалось сохранить профиль');
      return data;
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.me, profile);
      // Смена статуса или вуза открывает и закрывает разделы 4 и 7, а вместе с
      // ними меняет и то, что они отдают: их кэш больше не верен.
      void queryClient.invalidateQueries({ queryKey: ['schedule'] });
      void queryClient.invalidateQueries({ queryKey: ['food'] });
    },
  });
}

export function useConfirmVerification() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (): Promise<Profile> => {
      const { data, error } = await api.POST('/api/v1/users/me/verification');
      if (error || !data) throw new Error('не удалось подтвердить статус');
      return data;
    },
    onSuccess: (profile) => {
      queryClient.setQueryData(profileKeys.me, profile);
    },
  });
}
