/**
 * Конфигурация фронтенда из переменных сборки Vite.
 *
 * Чтение `import.meta.env` собрано в одном месте: значения нужны в нескольких
 * слоях (HTTP-клиент, адаптер платформы), и разбросанные обращения к env быстро
 * расходятся в значениях по умолчанию.
 */

export interface AppConfig {
  /** Базовый URL Core API без завершающего слэша. */
  readonly apiBaseUrl: string;
  /** Идентификатор пользователя для режима MOCK_AUTH на бэкенде. */
  readonly mockMaxUserId: string;
}

const DEFAULT_API_BASE_URL = 'http://localhost:8000';
const DEFAULT_MOCK_MAX_USER_ID = 'mock-user-1';

/** Убирает завершающие слэши, чтобы склейка с путём не давала `//api/v1`. */
export function normaliseBaseUrl(value: string): string {
  return value.trim().replace(/\/+$/, '');
}

/** Только те переменные сборки, которые читает конфигурация. */
export type ConfigEnv = Pick<ImportMetaEnv, 'VITE_API_BASE_URL' | 'VITE_MOCK_MAX_USER_ID'>;

export function readConfig(env: ConfigEnv): AppConfig {
  const apiBaseUrl = normaliseBaseUrl(env.VITE_API_BASE_URL ?? DEFAULT_API_BASE_URL);
  return {
    apiBaseUrl: apiBaseUrl === '' ? DEFAULT_API_BASE_URL : apiBaseUrl,
    mockMaxUserId: env.VITE_MOCK_MAX_USER_ID?.trim() || DEFAULT_MOCK_MAX_USER_ID,
  };
}

export const config: AppConfig = readConfig(import.meta.env);
