/**
 * Запросы блока 8 к Core API.
 *
 * Отписка приходит от сервера из заготовленного пула (ТЗ 8.4): экран её не
 * выбирает и не сочиняет — иначе текст менялся бы при каждом рендере.
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Category = components['schemas']['CategoryOut'];
export type TicketCategory = components['schemas']['TicketCategory'];
export type Ticket = components['schemas']['TicketOut'];
export type CreatedTicket = components['schemas']['CreatedTicketOut'];

export const supportKeys = {
  all: ['support'] as const,
  categories: ['support', 'categories'] as const,
  tickets: ['support', 'tickets'] as const,
};

export function useCategories() {
  return useQuery({
    queryKey: supportKeys.categories,
    queryFn: async (): Promise<Category[]> => {
      const { data, error } = await api.GET('/api/v1/support/categories');
      if (error || !data) throw new Error('не удалось загрузить типы обращений');
      return data;
    },
    staleTime: 60 * 60 * 1000,
  });
}

export function useTickets() {
  return useQuery({
    queryKey: supportKeys.tickets,
    queryFn: async () => {
      const { data, error } = await api.GET('/api/v1/support/tickets');
      if (error || !data) throw new Error('не удалось загрузить обращения');
      return data;
    },
  });
}

export function useSendTicket() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (ticket: {
      category: TicketCategory;
      text: string;
    }): Promise<CreatedTicket> => {
      const { data, error } = await api.POST('/api/v1/support/tickets', {
        body: { category: ticket.category, text: ticket.text },
      });
      if (error || !data) throw new Error('не удалось отправить обращение');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: supportKeys.tickets });
    },
  });
}
