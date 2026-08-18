"""Сервисный слой домена users — публичная граница домена.

Остальные домены обращаются сюда и никогда к моделям напрямую (тех. ТЗ 1.1).
Здесь же живут правила доступа к разделам, зависящим от статуса: блоки 4 и 7
требуют «Студент» + вуз (ТЗ 1.3), право отвечать в блоке 5 — ещё и верификацию
(уточнение У17).
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import asdict, dataclass

from tortoise.exceptions import IntegrityError
from tortoise.expressions import F
from tortoise.transactions import in_transaction

from navigator.domains.users.catalogue import UNIVERSITIES, UniversityRecord
from navigator.domains.users.models import University, User, UserStatus

# Модели переэкспортируются намеренно: сервисный слой — публичная граница
# домена (тех. ТЗ 1.1), и потребителю негде взять тип пользователя, кроме как
# отсюда. Импорт `navigator.domains.users.models` из другого домена запрещён и
# проверяется тестом границ.
__all__ = [
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_GROUP_NAME_LENGTH",
    "CatalogueSync",
    "InvalidProfileValue",
    "ProfileAccess",
    "University",
    "UniversityNotFound",
    "UniversityRecord",
    "User",
    "UserStatus",
    "VerificationNotAllowed",
    "access_for",
    "access_of",
    "add_points",
    "confirm_student_verification",
    "get_by_id",
    "get_many",
    "get_or_create",
    "get_university",
    "get_university_or_none",
    "list_universities",
    "sync_universities",
    "update_profile",
]

#: Ограничения совпадают с длиной колонок; клиентская валидация их зеркалит,
#: но источником истины остаётся сервер (тех. ТЗ 8.7).
MAX_DISPLAY_NAME_LENGTH = 128
MAX_GROUP_NAME_LENGTH = 128


class UniversityNotFound(LookupError):
    """В справочнике нет вуза с таким идентификатором."""


class VerificationNotAllowed(PermissionError):
    """Верификацию нельзя подтвердить: не выполнены условия уточнения У17."""


class InvalidProfileValue(ValueError):
    """Значение поля профиля не проходит проверку."""


@dataclass(frozen=True, slots=True)
class ProfileAccess:
    """Какие разделы открыты пользователю.

    Считается на сервере, а не на клиенте: профиль — единственный источник
    правды (ТЗ 3), и гейт не должен зависеть от того, как фронт понял статус.
    """

    schedule: bool
    food: bool
    answer_questions: bool


def access_for(
    *,
    status: UserStatus,
    has_university: bool,
    is_verified_student: bool,
) -> ProfileAccess:
    """Правила доступа. Чистая функция: ни базы, ни сети.

    Блоки 4 («Расписание») и 7 («Где покушать») требуют статус «Студент» и
    заполненный вуз (ТЗ 1.3). Закрытый раздел ведёт на экран-гейт, а не
    показывает отказ, — но решение «открыт или нет» принимается здесь.
    """
    is_student_with_university = status is UserStatus.student and has_university
    return ProfileAccess(
        schedule=is_student_with_university,
        food=is_student_with_university,
        answer_questions=is_student_with_university and is_verified_student,
    )


def access_of(user: User) -> ProfileAccess:
    return access_for(
        status=user.status,
        has_university=user.university_id is not None,
        is_verified_student=user.is_verified_student,
    )


def _clean_name(value: str, *, field: str, max_length: int) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise InvalidProfileValue(f"{field}: значение не может быть пустым")
    if len(cleaned) > max_length:
        raise InvalidProfileValue(f"{field}: длиннее {max_length} символов")
    return cleaned


async def get_or_create(max_user_id: str, display_name: str | None = None) -> User:
    """Профиль пользователя; при первом обращении создаётся.

    Онбординга нет: новый пользователь сразу попадает в главное меню со
    статусом «Абитуриент» (уточнение У5). Имя берётся из профиля MAX, если
    платформа его отдала; иначе остаётся пустым, и приложение просит ввести
    его самому (уточнение У6).
    """
    user = await User.get_or_none(max_user_id=max_user_id)
    if user is None:
        try:
            return await User.create(
                max_user_id=max_user_id,
                display_name=(display_name or "").strip()[:MAX_DISPLAY_NAME_LENGTH],
            )
        except IntegrityError:
            # Два первых запроса одного пользователя могли прийти одновременно.
            # Победил другой — просто берём то, что он создал.
            user = await User.get(max_user_id=max_user_id)

    # Имя могло появиться на стороне платформы позже, чем создался профиль.
    # Уже введённое пользователем имя не перетираем: оно приоритетнее.
    if not user.display_name and display_name and display_name.strip():
        user.display_name = display_name.strip()[:MAX_DISPLAY_NAME_LENGTH]
        await user.save(update_fields=["display_name"])
    return user


async def update_profile(
    user: User,
    *,
    display_name: str | None = None,
    status: UserStatus | None = None,
    university_id: int | None = None,
    group_name: str | None = None,
) -> User:
    """Обновляет профиль. `None` означает «не менять», а не «очистить».

    Очистки полей в продукте нет: вуз и группа выбираются из списка, имя не
    стирается. Смена статуса тоже ничего не удаляет — при возврате в «Студент»
    вуз и группа на месте («данные сохранены», экран профиля).
    """
    updated: list[str] = []

    if display_name is not None:
        user.display_name = _clean_name(
            display_name, field="display_name", max_length=MAX_DISPLAY_NAME_LENGTH
        )
        updated.append("display_name")

    if status is not None and status is not user.status:
        user.status = status
        updated.append("status")

    if university_id is not None and university_id != user.university_id:
        if not await University.exists(id=university_id):
            raise UniversityNotFound(f"вуз {university_id} не найден")
        user.university_id = university_id
        updated.append("university_id")

    if group_name is not None:
        user.group_name = _clean_name(
            group_name, field="group_name", max_length=MAX_GROUP_NAME_LENGTH
        )
        updated.append("group_name")

    if updated:
        await user.save(update_fields=updated)
    return user


async def confirm_student_verification(user: User) -> User:
    """Подтверждает статус верифицированного студента.

    Заглушка (уточнение У7): реальной проверки учебной почты и загрузки
    документов нет, кнопка просто переводит профиль в подтверждённое состояние.
    Условия при этом проверяются настоящие (уточнение У17), чтобы подключение
    реальной проверки меняло ровно одну функцию, а не логику блока 5.
    """
    if user.status is not UserStatus.student:
        raise VerificationNotAllowed("подтвердить можно только со статусом «Студент»")
    if user.university_id is None:
        raise VerificationNotAllowed("подтверждение требует заполненного вуза")
    if user.is_verified_student:
        return user
    user.is_verified_student = True
    await user.save(update_fields=["is_verified_student"])
    return user


async def get_by_id(user_id: int) -> User | None:
    """Профиль по идентификатору. Нужен домену gamification для баланса."""
    return await User.get_or_none(id=user_id)


async def add_points(user: User, amount: int) -> int:
    """Меняет баланс баллов и возвращает новое значение.

    Инкремент делается запросом к базе (`F`), а не чтением-записью в Python:
    два начисления подряд иначе затирают друг друга, а начисления приходят и
    из запросов пользователя, и из фоновых задач.

    Правила начисления живут в домене gamification (уточнение У21) — здесь
    только само изменение баланса: баланс принадлежит профилю (ТЗ 1.3).
    """
    await User.filter(id=user.id).update(points_balance=F("points_balance") + amount)
    fresh = await User.get(id=user.id)
    # Объект в памяти вызывающего кода не должен остаться со старым числом.
    user.points_balance = fresh.points_balance
    return fresh.points_balance


async def get_many(user_ids: Iterable[int]) -> list[User]:
    """Профили по набору идентификаторов. Нужен лентам, где авторов много."""
    ids = list(set(user_ids))
    if not ids:
        return []
    return await User.filter(id__in=ids)


async def list_universities() -> list[University]:
    """Справочник вузов для выбора в профиле."""
    return await University.all()


async def get_university_or_none(university_id: int) -> University | None:
    """Вуз или `None`. Для вызывающих, у которых отсутствие вуза — не ошибка."""
    return await University.get_or_none(id=university_id)


async def get_university(university_id: int) -> University:
    university = await University.get_or_none(id=university_id)
    if university is None:
        raise UniversityNotFound(f"вуз {university_id} не найден")
    return university


@dataclass(frozen=True, slots=True)
class CatalogueSync:
    """Что сделала заливка справочника. Короткие названия — для лога."""

    created: tuple[str, ...]
    updated: tuple[str, ...]
    unchanged: int
    #: Вузы, которые есть в базе, но которых нет в справочнике. Не удаляются —
    #: см. docstring `sync_universities`.
    extra: tuple[str, ...]


async def sync_universities(
    records: Sequence[UniversityRecord] = UNIVERSITIES,
) -> CatalogueSync:
    """Приводит справочник вузов в базе к содержимому `catalogue.py`.

    Повторный запуск безопасен и ничего не меняет: записи опознаются по полному
    названию, совпадающие поля не переписываются. Это позволяет вызывать
    заливку при каждом подъёме окружения, а не помнить про неё руками.

    Источник правды — файл справочника: правка строки в нём перетирает значение
    в базе. Ручные изменения в таблице `universities` не переживут следующую
    заливку, и это осознанно — иначе у справочника два источника правды.

    Вузы, которых в справочнике нет, **не удаляются**: на них могут ссылаться
    профили пользователей (ТЗ 1.3), и удаление молча обнулило бы им вуз. Такие
    записи возвращаются в `extra`, решение по ним — ручное.
    """
    names = [record.name for record in records]
    if len(set(names)) != len(names):
        # Ловим опечатку в справочнике здесь: иначе она превратится в
        # IntegrityError по уникальному индексу на середине заливки.
        duplicates = sorted({name for name in names if names.count(name) > 1})
        raise ValueError("в справочнике повторяются названия вузов: " + ", ".join(duplicates))

    created: list[str] = []
    updated: list[str] = []
    unchanged = 0

    # Транзакция на всю заливку: наполовину обновлённый справочник хуже, чем
    # необновлённый — пользователь увидит часть вузов со старыми данными.
    async with in_transaction():
        existing = {university.name: university for university in await University.all()}

        for record in records:
            # Поля берутся из самого датакласса, а не перечисляются здесь
            # руками: новое поле справочника тогда попадает в заливку само, а
            # не забывается в этой функции.
            values = asdict(record)
            name = values.pop("name")

            university = existing.pop(name, None)
            if university is None:
                await University.create(name=name, **values)
                created.append(record.short_name)
                continue

            changed = [
                field for field, value in values.items() if getattr(university, field) != value
            ]
            if not changed:
                unchanged += 1
                continue

            for field in changed:
                setattr(university, field, values[field])
            await university.save(update_fields=changed)
            updated.append(record.short_name)

    return CatalogueSync(
        created=tuple(created),
        updated=tuple(updated),
        unchanged=unchanged,
        extra=tuple(sorted(existing)),
    )
