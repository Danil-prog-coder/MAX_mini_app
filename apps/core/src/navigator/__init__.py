"""Core API «Навигатора» — модульный монолит (тех. ТЗ 1.1).

Внутри одного деплоймента живут независимые домены (`navigator.domains.*`),
Celery-воркер (`navigator.worker`) и HTTP-слой (`navigator.api`).
Границы доменов описаны в CONTRIBUTING.md и проверяются тестом
`tests/test_domain_boundaries.py`.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"
