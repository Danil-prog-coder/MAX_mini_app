"""Правила доступа к разделам по статусу профиля (ТЗ 1.3, уточнение У17).

Чистая логика, поэтому без базы: тех. ТЗ 7 требует, чтобы доменные расчёты
проверялись как функции на входе и выходе.
"""

from __future__ import annotations

import pytest

from navigator.domains.users.service import UserStatus, access_for


@pytest.mark.parametrize("status", [UserStatus.school, UserStatus.applicant])
@pytest.mark.parametrize("has_university", [False, True])
def test_non_students_never_get_schedule_or_food(status: UserStatus, has_university: bool) -> None:
    """Блоки 4 и 7 требуют статус «Студент» — одного вуза недостаточно."""
    access = access_for(status=status, has_university=has_university, is_verified_student=False)

    assert access.schedule is False
    assert access.food is False


def test_student_without_university_does_not_get_schedule_or_food() -> None:
    """И статуса без вуза недостаточно: расписание и еда привязаны к вузу."""
    access = access_for(status=UserStatus.student, has_university=False, is_verified_student=False)

    assert access.schedule is False
    assert access.food is False


def test_student_with_university_gets_schedule_and_food() -> None:
    access = access_for(status=UserStatus.student, has_university=True, is_verified_student=False)

    assert access.schedule is True
    assert access.food is True


def test_answering_requires_verification_on_top_of_status_and_university() -> None:
    """Уточнение У17: статус «Студент» + вуз + нажатая верификация."""
    almost = access_for(status=UserStatus.student, has_university=True, is_verified_student=False)
    full = access_for(status=UserStatus.student, has_university=True, is_verified_student=True)

    assert almost.answer_questions is False
    assert full.answer_questions is True


@pytest.mark.parametrize("status", [UserStatus.school, UserStatus.applicant])
def test_verification_alone_does_not_grant_the_right_to_answer(status: UserStatus) -> None:
    """Флаг верификации сохраняется при смене статуса, но права не даёт."""
    access = access_for(status=status, has_university=True, is_verified_student=True)

    assert access.answer_questions is False


def test_verified_student_without_university_cannot_answer() -> None:
    access = access_for(status=UserStatus.student, has_university=False, is_verified_student=True)

    assert access.answer_questions is False


def test_default_status_is_applicant() -> None:
    """Онбординга нет, новый пользователь — абитуриент (уточнение У5)."""
    assert UserStatus("applicant") is UserStatus.applicant
    assert [status.value for status in UserStatus] == ["school", "applicant", "student"]
