/**
 * Запросы блока 1 к Core API.
 *
 * Всё, что приходит с сервера, живёт в TanStack Query и только в нём
 * (тех. ТЗ 8.2): Zustand копий серверных данных не хранит. Прогресс
 * прохождения теста серверным состоянием не является — он обычный локальный
 * state экрана и намеренно теряется при выходе (ТЗ 1.3).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import type { components } from './schema';

export type Question = components['schemas']['QuestionOut'];
export type TestResult = components['schemas']['TestResultOut'];
export type SavedResult = components['schemas']['SavedResultOut'];
export type Vacancies = components['schemas']['VacanciesOut'];

export const careerTestKeys = {
  questions: ['career-test', 'questions'] as const,
  latestResult: ['career-test', 'result', 'latest'] as const,
  vacancies: (direction: string) => ['career-test', 'vacancies', direction] as const,
};

export function useQuestions() {
  return useQuery({
    queryKey: careerTestKeys.questions,
    queryFn: async (): Promise<Question[]> => {
      const { data, error } = await api.GET('/api/v1/career-test/questions');
      if (error || !data) throw new Error('не удалось загрузить вопросы теста');
      return data;
    },
    // Вопросы меняются раз в никогда: перезапрашивать их нет смысла.
    staleTime: 60 * 60 * 1000,
  });
}

export function useLatestResult() {
  return useQuery({
    queryKey: careerTestKeys.latestResult,
    queryFn: async (): Promise<TestResult | null> => {
      const { data, error, response } = await api.GET('/api/v1/career-test/results/latest');
      // 404 — не ошибка, а «тест ещё не пройден»: экран покажет приглашение
      // пройти его, а не сообщение о сбое.
      if (response.status === 404) return null;
      // Проверяем и `error`, и `data`: типы клиента допускают, что не будет ни
      // того ни другого — например, при неожиданном коде ответа.
      if (error || !data) throw new Error('не удалось загрузить результат теста');
      return data;
    },
  });
}

export function useSubmitTest() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (optionIds: number[]): Promise<TestResult> => {
      const { data, error } = await api.POST('/api/v1/career-test/submit', {
        body: { option_ids: optionIds },
      });
      if (error || !data) throw new Error('не удалось отправить ответы');
      return data;
    },
    onSuccess: (result) => {
      // Свежий результат кладём в кэш сразу: экран результата открывается
      // мгновенно, без второго запроса за тем же самым.
      queryClient.setQueryData(careerTestKeys.latestResult, result);
    },
  });
}

export function useSaveResult() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (resultId: number): Promise<SavedResult> => {
      const { data, error } = await api.POST('/api/v1/career-test/results/{result_id}/save', {
        params: { path: { result_id: resultId } },
      });
      if (error || !data) throw new Error('не удалось сохранить результат');
      return data;
    },
    onSuccess: (saved) => {
      queryClient.setQueryData(careerTestKeys.latestResult, saved.result);
      // Баланс баллов изменился — профиль перечитываем.
      void queryClient.invalidateQueries({ queryKey: ['users', 'me'] });
    },
  });
}

export function useVacancies(direction: string | null) {
  return useQuery({
    queryKey: careerTestKeys.vacancies(direction ?? ''),
    // Запрос уходит только когда шторку открыли: до этого направление неизвестно.
    enabled: direction !== null,
    queryFn: async (): Promise<Vacancies> => {
      const { data, error } = await api.GET('/api/v1/career-test/vacancies', {
        params: { query: { direction: direction ?? '' } },
      });
      if (error || !data) throw new Error('не удалось загрузить вакансии');
      return data;
    },
    // Зеркалит кэш бэкенда: там те же шесть часов (уточнение У14).
    staleTime: 6 * 60 * 60 * 1000,
  });
}
