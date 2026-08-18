/**
 * Типизированный клиент Core API.
 *
 * Типы не пишутся руками, а генерируются из схемы OpenAPI (`make api-types`,
 * тех. ТЗ 8.6): при параллельной работе над фронтом и бэкендом ручные
 * интерфейсы расходятся со схемой молча, а сгенерированные — ломают сборку.
 */
import createClient, { type Middleware } from 'openapi-fetch';

import { config } from '@/shared/config';
import { getInitData } from '@/shared/platform/max';

import type { paths } from './schema';

/** Заголовок с подписанными данными инициализации (проверяется на бэкенде). */
export const INIT_DATA_HEADER = 'X-Max-Init-Data';
/** Заголовок с идентификатором пользователя в режиме MOCK_AUTH. */
export const MOCK_USER_HEADER = 'X-Max-User-Id';

/**
 * Опознание пользователя на каждом запросе.
 *
 * Клиент только прикладывает `initData` — доверять ей он не вправе, подпись
 * проверяет Core API (тех. ТЗ 6, 8.6). Если моста платформы нет, приложение
 * открыто в обычном браузере: тогда уходит идентификатор для `MOCK_AUTH`, и
 * бэкенд с выключенным флагом ответит 401 — это правильное поведение, а не
 * повод слать оба заголовка сразу.
 */
export const authMiddleware: Middleware = {
  onRequest({ request }) {
    const initData = getInitData();
    if (initData !== null) {
      request.headers.set(INIT_DATA_HEADER, initData);
    } else {
      request.headers.set(MOCK_USER_HEADER, config.mockMaxUserId);
    }
    return request;
  },
};

export function createApiClient(baseUrl: string = config.apiBaseUrl) {
  const client = createClient<paths>({ baseUrl });
  client.use(authMiddleware);
  return client;
}

export const api = createApiClient();
