"""Провайдер YandexGPT (тех. ТЗ 2, 5).

**Не сверен с живым API.** Ключа к YandexGPT в проекте нет, а домен
`llm.api.cloud.yandex.net` закрыт сетевой политикой окружения разработки — тем
же прокси, что и `dev.max.ru` (тех. ТЗ 9.7). Схема запроса воспроизведена по
публичному описанию Foundation Models API; всё, что зависит от документации,
собрано в двух функциях — `_payload` и `_read`. Сверка изменит их тела, а не
структуру кода.

**Снимать `LLM_PROVIDER=mock` до сверки нельзя**: непроверенный клиент даст либо
постоянный отказ, либо, что хуже, тихо неверный разбор ответа.
"""

from __future__ import annotations

from typing import Any, Final

import httpx

from navigator_ai.config import Settings
from navigator_ai.providers.base import Completion, LLMUnavailableError

#: Синхронный вызов модели. Асинхронный режим и стриминг не нужны: ответы
#: короткие, а шлюз и так живёт под таймаутом.
API_URL: Final = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"

#: Имя модели собирается из идентификатора каталога: так требует API.
MODEL_TEMPLATE: Final = "gpt://{folder_id}/yandexgpt-lite/latest"


class YandexGptProvider:
    """Обёртка над Foundation Models API."""

    def __init__(self, settings: Settings) -> None:
        if settings.yandex_gpt_api_key is None or settings.yandex_gpt_folder_id is None:
            raise ValueError("YandexGPT требует YANDEX_GPT_API_KEY и YANDEX_GPT_FOLDER_ID")
        self._api_key = settings.yandex_gpt_api_key.get_secret_value()
        self._folder_id = settings.yandex_gpt_folder_id
        self._timeout = settings.llm_timeout_seconds

    @property
    def name(self) -> str:
        return "yandexgpt"

    async def complete(
        self,
        prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> Completion:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(
                    API_URL,
                    headers={
                        "Authorization": f"Api-Key {self._api_key}",
                        "x-folder-id": self._folder_id,
                    },
                    json=self._payload(prompt, max_tokens=max_tokens, temperature=temperature),
                )
                response.raise_for_status()
                body = response.json()
        # Ловим широко: таймаут, отказ сети, 4xx и 5xx означают для вызывающего
        # одно и то же — модель недоступна, пора к резервному провайдеру.
        except Exception as error:
            raise LLMUnavailableError(f"YandexGPT недоступен: {type(error).__name__}") from error

        return self._read(body)

    def _payload(self, prompt: str, *, max_tokens: int, temperature: float) -> dict[str, Any]:
        """Тело запроса. Зависит от документации — меняется при сверке."""
        return {
            "modelUri": MODEL_TEMPLATE.format(folder_id=self._folder_id),
            "completionOptions": {
                "stream": False,
                "temperature": temperature,
                "maxTokens": str(max_tokens),
            },
            "messages": [{"role": "user", "text": prompt}],
        }

    def _read(self, body: Any) -> Completion:
        """Разбор ответа. Зависит от документации — меняется при сверке.

        Пустой или неожиданный ответ — это `LLMUnavailableError`, а не пустая
        строка: вызывающий должен уйти на резервного провайдера, а не показать
        человеку пустоту.
        """
        try:
            result = body["result"]
            text = result["alternatives"][0]["message"]["text"]
            usage = result.get("usage", {})
        except (KeyError, IndexError, TypeError) as error:
            raise LLMUnavailableError("YandexGPT вернул неожиданный ответ") from error

        if not isinstance(text, str) or not text.strip():
            raise LLMUnavailableError("YandexGPT вернул пустой ответ")

        return Completion(
            text=text.strip(),
            provider=self.name,
            prompt_tokens=_int(usage.get("inputTextTokens")),
            completion_tokens=_int(usage.get("completionTokens")),
        )


def _int(value: Any) -> int:
    """Расход токенов приходит строкой. Нечитаемое значение — ноль, не отказ."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
