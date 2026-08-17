"""Сервисный слой домена users — публичная граница домена.

Остальные домены обращаются сюда и никогда к моделям напрямую (тех. ТЗ 1.1).
Здесь же живут правила доступа к разделам, зависящим от статуса: блоки 4 и 7
требуют «Студент» + вуз (ТЗ 1.3), право отвечать в блоке 5 — ещё и верификацию
(уточнение У17).
"""

from __future__ import annotations

from dataclasses import dataclass

from tortoise.exceptions import IntegrityError

from navigator.domains.users.models import University, User, UserStatus

# Модели переэкспортируются намеренно: сервисный слой — публичная граница
# домена (тех. ТЗ 1.1), и потребителю негде взять тип пользователя, кроме как
# отсюда. Импорт `navigator.domains.users.models` из другого домена запрещён и
# проверяется тестом границ.
__all__ = [
    "MAX_DISPLAY_NAME_LENGTH",
    "MAX_GROUP_NAME_LENGTH",
    "InvalidProfileValue",
    "ProfileAccess",
    "University",
    "UniversityNotFound",
    "User",
    "UserStatus",
    "VerificationNotAllowed",
    "access_for",
    "access_of",
    "confirm_student_verification",
    "get_or_create",
    "get_university",
    "list_universities",
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


async def list_universities() -> list[University]:
    """Справочник вузов для выбора в профиле."""
    return await University.all()


async def get_university(university_id: int) -> University:
    university = await University.get_or_none(id=university_id)
    if university is None:
        raise UniversityNotFound(f"вуз {university_id} не найден")
    return university
