/**
 * Запросы блока 5 к Core API.
 *
 * Читают все, отвечают свои (уточнение У15): лента любого вуза открыта всем, а
 * право ответа приходит из профиля полем `access.answer_questions` — считает
 * его сервер (решение Р19).
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';

import { api } from './client';
import { profileKeys } from './profile';
import type { components } from './schema';

export type Topic = components['schemas']['TopicOut'];
export type QuestionTopic = components['schemas']['QuestionTopic'];
export type Feed = components['schemas']['FeedOut'];
export type FeedQuestion = components['schemas']['FeedQuestionOut'];
export type FeedAnswer = components['schemas']['AnswerOut'];
export type Asked = components['schemas']['AskedOut'];

export const mentorQaKeys = {
  all: ['mentor-qa'] as const,
  topics: ['mentor-qa', 'topics'] as const,
  feed: (universityId: number, topic: QuestionTopic | null) =>
    ['mentor-qa', 'feed', universityId, topic] as const,
};

export function useTopics() {
  return useQuery({
    queryKey: mentorQaKeys.topics,
    queryFn: async (): Promise<Topic[]> => {
      const { data, error } = await api.GET('/api/v1/mentor-qa/topics');
      if (error || !data) throw new Error('не удалось загрузить темы');
      return data;
    },
    staleTime: 60 * 60 * 1000,
  });
}

export function useFeed(universityId: number | null, topic: QuestionTopic | null = null) {
  return useQuery({
    queryKey: mentorQaKeys.feed(universityId ?? 0, topic),
    enabled: universityId !== null,
    queryFn: async (): Promise<Feed> => {
      const { data, error } = await api.GET('/api/v1/mentor-qa/questions', {
        params: { query: { vuz_id: universityId ?? 0, topic } },
      });
      if (error || !data) throw new Error('не удалось загрузить ленту');
      return data;
    },
  });
}

export function useAsk() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (question: {
      universityId: number;
      topic: QuestionTopic;
      text: string;
    }): Promise<Asked> => {
      const { data, error } = await api.POST('/api/v1/mentor-qa/questions', {
        body: {
          university_id: question.universityId,
          topic: question.topic,
          text: question.text,
        },
      });
      if (error || !data) throw new Error('не удалось отправить вопрос');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mentorQaKeys.all });
    },
  });
}

export function useAnswer() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (answer: { questionId: number; text: string }) => {
      const { data, error } = await api.POST('/api/v1/mentor-qa/questions/{question_id}/answers', {
        params: { path: { question_id: answer.questionId } },
        body: { text: answer.text },
      });
      if (error || !data) throw new Error('не удалось отправить ответ');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mentorQaKeys.all });
      // Ответ даёт +25 (уточнение У21) — баланс в профиле изменился.
      void queryClient.invalidateQueries({ queryKey: profileKeys.me });
    },
  });
}

export function useToggleLike() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (answerId: number) => {
      const { data, error } = await api.POST('/api/v1/mentor-qa/answers/{answer_id}/like', {
        params: { path: { answer_id: answerId } },
      });
      if (error || !data) throw new Error('не удалось поставить лайк');
      return data;
    },
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: mentorQaKeys.all });
    },
  });
}
