"""Провайдер GigaChat — резерв при недоступности основного (тех. ТЗ 5, п. 3).

**Не сверен с живым API** по тем же причинам, что и YandexGPT: ключа нет, домен
закрыт сетевой политикой окружения. Всё, что зависит от документации, собрано в
`_payload` и `_read`.

Отличие от YandexGPT — двухшаговая авторизация: сначала ключ обменивается на
временный токен, затем токен идёт в заголовке. Токен кэшируется в памяти
процесса до истечения: обменивать его на каждый запрос — лишний вызов и лишняя
точка отказа.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Final

import httpx

from navigator_ai.config import Settings
from navigator_ai.providers.base import Completion, LLMUnavailableError

AUTH_URL: Final = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
API_URL: Final = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
MODEL: Final = "GigaChat"

#: Запас перед истечением токена: обновляем чуть раньше, чем он протухнет.
TOKEN_LEEWAY_SECONDS: Final = 60


class GigaChatProvider:
    """Обёртка над GigaChat API с обменом ключа на временный токен."""

    def __init__(self, settings: Settings) -> None:
        if settings.gigachat_api_key is None:
            raise ValueError("GigaChat требует GIGACHAT_API_KEY")
        self._api_key = settings.gigachat_api_key.get_secret_value()
        self._timeout = settings.llm_timeout_seconds
        self._token: str | None = None
        self._token_expires_at: float = 0.0

    @property
    def name(self) -> str:
        return "gigachat"

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        try:
            async with httpx.AsyncClient(timeout=self._timeout, verify=True) as client:
                token = await self._access_token(client)
                response = await client.post(
                    API_URL,
                    headers={"Authorization": f"Bearer {token}"},
                    json=self._payload(prompt, max_tokens=max_tokens, temperature=temperature),
                )
                response.raise_for_status()
                body = response.json()
        except LLMUnavailableError:
            raise
        except Exception as error:
            raise LLMUnavailableError(f"GigaChat недоступен: {type(error).__name__}") from error

        return self._read(body)

    async def _access_token(self, client: httpx.AsyncClient) -> str:
        """Временный токен. Кэшируется в памяти процесса до истечения."""
        now = time.monotonic()
        if self._token is not None and now < self._token_expires_at:
            return self._token

        response = await client.post(
            AUTH_URL,
            headers={
                "Authorization": f"Basic {self._api_key}",
                "RqUID": str(uuid.uuid4()),
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={"scope": "GIGACHAT_API_PERS"},
        )
        response.raise_for_status()
        body = response.json()

        token = body.get("access_token")
        if not isinstance(token, str) or not token:
            raise LLMUnavailableError("GigaChat не выдал токен")

        # `expires_at` приходит в миллисекундах эпохи; переводим в монотонное
        # время процесса, чтобы перевод часов не сделал токен вечным.
        expires_at = body.get("expires_at")
        lifetime = 1800.0
        if isinstance(expires_at, (int, float)):
            lifetime = max(60.0, expires_at / 1000 - time.time())

        self._token = token
        self._token_expires_at = now + lifetime - TOKEN_LEEWAY_SECONDS
        return token

    def _payload(self, prompt: str, *, max_tokens: int, temperature: float) -> dict[str, Any]:
        """Тело запроса. Зависит от документации — меняется при сверке."""
        return {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    def _read(self, body: Any) -> Completion:
        """Разбор ответа. Зависит от документации — меняется при сверке."""
        try:
            text = body["choices"][0]["message"]["content"]
            usage = body.get("usage", {})
        except (KeyError, IndexError, TypeError) as error:
            raise LLMUnavailableError("GigaChat вернул неожиданный ответ") from error

        if not isinstance(text, str) or not text.strip():
            raise LLMUnavailableError("GigaChat вернул пустой ответ")

        return Completion(
            text=text.strip(),
            provider=self.name,
            prompt_tokens=_int(usage.get("prompt_tokens")),
            completion_tokens=_int(usage.get("completion_tokens")),
        )


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
