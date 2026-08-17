"""Домены модульного монолита (тех. ТЗ 1.1).

Каждый домен — самостоятельный Python-пакет со своими моделями, схемами,
сервисным слоем и роутами:

    navigator/domains/<домен>/
        models.py     — модели Tortoise, приватны для домена
        schemas.py    — pydantic-схемы HTTP-слоя
        service.py    — бизнес-логика; ЕДИНСТВЕННАЯ публичная граница домена
        router.py     — эндпоинты FastAPI
        sources.py    — реестры внешних источников домена (если они есть)

Планируемый состав: users, career_test, vuz_selection, tracker, schedule,
mentor_qa, gamification, food, support, notifications.

Правило границ (тех. ТЗ 1.1, 9.6): домен не импортирует модели, схемы и роуты
другого домена — только его `service`. Правило проверяется автоматически
тестом `tests/test_domain_boundaries.py`, а не договорённостью на словах.
"""
