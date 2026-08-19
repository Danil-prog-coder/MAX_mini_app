/**
 * Каждый запрос обязан нести опознание пользователя, и ровно одно: подпись
 * платформы либо идентификатор для режима MOCK_AUTH (тех. ТЗ 6, 9.3).
 * Отправлять оба заголовка сразу нельзя — это молча превратило бы включённый
 * на бэкенде MOCK_AUTH в дыру, которую не видно с фронта.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';

import { config } from '@/shared/config';

import { createApiClient, INIT_DATA_HEADER, MOCK_USER_HEADER } from './client';

type FetchMock = ReturnType<typeof captureRequest>;

function captureRequest() {
  const fetchMock = vi.fn<(request: Request) => Promise<Response>>(() =>
    Promise.resolve(new Response('{}', { headers: { 'Content-Type': 'application/json' } })),
  );
  vi.stubGlobal('fetch', fetchMock);
  return fetchMock;
}

/** Запрос, который клиент отправил. Отсутствие запроса — тоже провал теста. */
function sentRequest(fetchMock: FetchMock): Request {
  const request = fetchMock.mock.calls[0]?.[0];
  if (!request) throw new Error('клиент не отправил ни одного запроса');
  return request;
}

afterEach(() => {
  delete window.WebApp;
  vi.unstubAllGlobals();
});

describe('клиент Core API', () => {
  it('без моста платформы шлёт идентификатор для MOCK_AUTH', async () => {
    const fetchMock = captureRequest();

    await createApiClient('http://api.test').GET('/api/v1/users/me');

    const request = sentRequest(fetchMock);
    expect(request.url).toBe('http://api.test/api/v1/users/me');
    expect(request.headers.get(MOCK_USER_HEADER)).toBe(config.mockMaxUserId);
    expect(request.headers.get(INIT_DATA_HEADER)).toBeNull();
  });

  it('с мостом платформы шлёт подписанные данные и не шлёт mock-заголовок', async () => {
    const fetchMock = captureRequest();
    window.WebApp = { initData: 'user=1&hash=abc' };

    await createApiClient('http://api.test').GET('/api/v1/users/me');

    const request = sentRequest(fetchMock);
    expect(request.headers.get(INIT_DATA_HEADER)).toBe('user=1&hash=abc');
    expect(request.headers.get(MOCK_USER_HEADER)).toBeNull();
  });
});
