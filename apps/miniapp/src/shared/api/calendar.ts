/**
 * Календарь на главном экране (уточнение У32).
 *
 * Источник правды один — сервер. Он собирает в одну ленту личные события,
 * дедлайны приёмной кампании отслеживаемых вузов и пары по расписанию группы,
 * поэтому фронт не знает, откуда что взялось, и не решает это сам.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from '@/shared/api/client';
import type { components } from '@/shared/api/schema';

export type CalendarEvent = components['schemas']['CalendarEventOut'];

export const calendarKeys = {
  /** Ключ на месяц: листание вперёд не сбрасывает уже загруженное. */
  month: (from: string, to: string) => ['calendar', from, to] as const,
  all: ['calendar'] as const,
};

export function useCalendarMonth(from: string, to: string) {
  return useQuery({
    queryKey: calendarKeys.month(from, to),
    queryFn: async (): Promise<CalendarEvent[]> => {
      const { data, error } = await api.GET('/api/v1/calendar', {
        params: { query: { date_from: from, date_to: to } },
      });
      if (error || !data) throw new Error('не удалось загрузить события календаря');
      return data;
    },
  });
}

export function useAddCalendarEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (event: { title: string; day: string }): Promise<CalendarEvent> => {
      const { data, error } = await api.POST('/api/v1/calendar/events', { body: event });
      if (error || !data) throw new Error('не удалось сохранить событие');
      return data;
    },
    // Обновляются все месяцы разом: событие могло уехать в соседний месяц,
    // и обновление только текущего оставило бы там дырку.
    onSuccess: () => queryClient.invalidateQueries({ queryKey: calendarKeys.all }),
  });
}

export function useDeleteCalendarEvent() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (eventId: number): Promise<void> => {
      const { error } = await api.DELETE('/api/v1/calendar/events/{event_id}', {
        params: { path: { event_id: eventId } },
      });
      if (error) throw new Error('не удалось удалить событие');
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: calendarKeys.all }),
  });
}
