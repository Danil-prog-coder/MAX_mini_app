/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Базовый URL Core API с точки зрения браузера. */
  readonly VITE_API_BASE_URL?: string;
  /**
   * Идентификатор пользователя, который отправляется в X-Max-User-Id, пока на
   * бэкенде включён MOCK_AUTH (тех. ТЗ 9.3). В продовой сборке не используется:
   * там идентификатор приходит из подписанного initData от MAX.
   */
  readonly VITE_MOCK_MAX_USER_ID?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
