/**
 * Запросы блока 4 к Core API.
 *
 * Раздел закрыт гейтом (ТЗ 4.2): сервер отвечает 403, пока в профиле нет
 * статуса «Студент» и вуза. Это не ошибка, а маршрут — экран уводит человека
 * на гейт с кнопкой в профиль (инвариант 4 в CLAUDE.md).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import { profileKeys } from './profile';
import type { components } from './schema';

export type Today = components['schemas']['TodayOut'];
export type Lesson = components['schemas']['LessonOut'];
export type Deadline = components['schemas']['DeadlineOut'];
export type Group = components['schemas']['GroupOut'];

/** Раздел закрыт по статусу: запрос отдаёт это значение вместо данных. */
export const CLOSED = 'closed' as const;
export type Closed = typeof CLOSED;

export const scheduleKeys = {
  all: ['schedule'] as const,
  today: ['schedule', 'today'] as const,
  groups: ['schedule', 'groups'] as const,
};

export function useToday() {
  return useQuery({
    queryKey: scheduleKeys.today,
    queryFn: async (): Promise<Today | Closed> => {
      const { data, error, response } = await api.GET('/api/v1/schedule/today');
      if (response.status === 403) return CLOSED;
      if (error || !data) throw new Error('не удалось загрузить расписание');
      return data;
    },
  });
}

export function useGroups(enabled: boolean) {
  return useQuery({
    queryKey: scheduleKeys.groups,
    enabled,
    queryFn: async (): Promise<Group[]> => {
      const { data, error } = await api.GET('/api/v1/schedule/groups');
      if (error || !data) throw new Error('не удалось загрузить список групп');
      return data;
    },
  });
}

export function useBindGroup() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (groupName: string): Promise<Group> => {
      const { data, error } = await api.POST('/api/v1/schedule/source', {
        body: { group_name: groupName },
      });
      if (error || !data) throw new Error('не удалось сохранить группу');
      return data;
    },
    onSuccess: () => {
      // Группа хранится в профиле, поэтому меняется именно он; расписание на
      // сегодня после смены группы другое.
      void queryClient.invalidateQueries({ queryKey: profileKeys.me });
      void queryClient.invalidateQueries({ queryKey: scheduleKeys.today });
    },
  });
}

export function useAddDeadline() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (deadline: { title: string; dueDate: string }): Promise<Deadline> => {
      const { data, error } = await api.POST('/api/v1/schedule/deadlines', {
        body: { title: deadline.title, due_date: deadline.dueDate },
      });
      if (error || !data) throw new Error('не удалось добавить дедлайн');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: scheduleKeys.today });
    },
  });
}
