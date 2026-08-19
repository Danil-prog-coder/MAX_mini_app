/**
 * Запросы уведомлений (уточнения У9, У25).
 *
 * Уведомления копятся в базе и показываются внутри приложения: лента и
 * счётчик-бейдж в нижней панели. Отправка в чат мессенджера — дело сервера, и
 * фронт о ней ничего не знает.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Notifications = components['schemas']['NotificationsOut'];
export type Notification = components['schemas']['NotificationOut'];
export type NotificationSettings = components['schemas']['SettingsOut'];
export type NotificationKind = components['schemas']['NotificationKind'];

export const notificationKeys = {
  all: ['notifications'] as const,
  feed: ['notifications', 'feed'] as const,
  settings: ['notifications', 'settings'] as const,
};

/** Как часто перечитывается лента: бейдж должен оживать без перезагрузки. */
const FEED_REFETCH_MS = 60 * 1000;

export function useNotifications() {
  return useQuery({
    queryKey: notificationKeys.feed,
    queryFn: async (): Promise<Notifications> => {
      const { data, error } = await api.GET('/api/v1/notifications');
      if (error || !data) throw new Error('не удалось загрузить уведомления');
      return data;
    },
    refetchInterval: FEED_REFETCH_MS,
  });
}

export function useMarkRead() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: number) => {
      const { data, error } = await api.POST('/api/v1/notifications/{notification_id}/read', {
        params: { path: { notification_id: id } },
      });
      if (error || !data) throw new Error('не удалось отметить уведомление');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: notificationKeys.feed });
    },
  });
}

export function useNotificationSettings() {
  return useQuery({
    queryKey: notificationKeys.settings,
    queryFn: async (): Promise<NotificationSettings> => {
      const { data, error } = await api.GET('/api/v1/notifications/settings');
      if (error || !data) throw new Error('не удалось загрузить настройки уведомлений');
      return data;
    },
  });
}

export function useUpdateNotificationSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (patch: {
      digest_hour?: number;
      muted_kinds?: NotificationKind[];
    }): Promise<NotificationSettings> => {
      const { data, error } = await api.PATCH('/api/v1/notifications/settings', { body: patch });
      if (error || !data) throw new Error('не удалось сохранить настройки');
      return data;
    },
    onSuccess: (settings) => {
      queryClient.setQueryData(notificationKeys.settings, settings);
    },
  });
}
