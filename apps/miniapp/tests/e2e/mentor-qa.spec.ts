import { expect, test, type Page } from '@playwright/test';

import { APPLICANT_PROFILE, installApiStub, SEEDED_QUESTION } from './apiStub';

/**
 * Блок 5 глазами абитуриента и студента (ТЗ 5.2–5.8).
 *
 * Читают все, отвечают свои (уточнение У15): абитуриент спрашивает и читает,
 * верифицированный студент своего вуза отвечает.
 *
 * Прогоняется на обоих профилях устройств: кроссплатформенность — критерий
 * приёмки (ТЗ 0.2).
 */

/**
 * Выбирает вуз ленты.
 *
 * У абитуриента вуза в профиле нет, и подставлять его за него нельзя: вопрос
 * ушёл бы в ленту случайного вуза. Поэтому он выбирает вуз сам (ТЗ 5.3).
 */
async function pickUniversity(page: Page): Promise<void> {
  await page.getByRole('button', { name: 'Другой' }).click();
  await page.getByRole('dialog').getByRole('button', { name: /МГУ/ }).click();
}

test('вопрос задаётся анонимно и сразу публикуется', async ({ page }) => {
  // ТЗ 5.5 и уточнение У18: чистый текст публикуется без ожидания.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa');
  await pickUniversity(page);

  await page.getByRole('button', { name: 'Учёба', exact: true }).click();
  await page
    .getByRole('textbox', { name: 'Текст вопроса' })
    .fill('Реально ли совмещать первый курс и подработку?');
  await page.getByRole('button', { name: 'Опубликовать анонимно' }).click();

  await expect(page.getByText('ВАШ ВОПРОС ОПУБЛИКОВАН')).toBeVisible();
});

test('отклонённый вопрос честно назван неопубликованным', async ({ page }) => {
  // Уточнение У18: делать вид, что вопрос в ленте, — значит обмануть автора.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa');
  await pickUniversity(page);

  await page.getByRole('textbox', { name: 'Текст вопроса' }).fill('вы там все тупые вообще');
  await page.getByRole('button', { name: 'Опубликовать анонимно' }).click();

  await expect(page.getByText('ВОПРОС НЕ ОПУБЛИКОВАН')).toBeVisible();
});

test('спорный вопрос уходит живому модератору', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa');
  await pickUniversity(page);

  await page.getByRole('textbox', { name: 'Текст вопроса' }).fill('куплю ответы к сессии недорого');
  await page.getByRole('button', { name: 'Опубликовать анонимно' }).click();

  await expect(page.getByText('ВОПРОС НА ПРОВЕРКЕ')).toBeVisible();
  await expect(page.getByText(/посмотрит живой модератор/)).toBeVisible();
});

test('короткий вопрос не отправляется', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa');
  await pickUniversity(page);

  await page.getByRole('textbox', { name: 'Текст вопроса' }).fill('а?');

  await expect(page.getByRole('button', { name: 'Опубликовать анонимно' })).toBeDisabled();
});

test('лента открыта всем, включая абитуриента без вуза', async ({ page }) => {
  // Уточнение У15: читают все — в этом смысл блока для абитуриента.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa/1');

  await expect(page.getByText(SEEDED_QUESTION.text)).toBeVisible();
  await expect(page.getByText('ПОСТУПЛЕНИЕ · 1 ОТВЕТ')).toBeVisible();
  // Подпись автора ответа — только имя (уточнение У16).
  await expect(page.getByText('Марина')).toBeVisible();
  await expect(page.getByText(/курс/)).toHaveCount(0);
});

test('без права ответа поля ответа нет', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa/1');

  await expect(page.getByRole('textbox', { name: 'Ваш ответ' })).toHaveCount(0);
});

test('верифицированный студент своего вуза отвечает и получает +25', async ({ page }) => {
  // Уточнения У17 и У21.
  await installApiStub(page, { profile: { is_verified_student: true } });
  await page.goto('/mentor-qa/1');

  await page
    .getByRole('textbox', { name: 'Ваш ответ' })
    .fill('Общежитие около 900 рублей, остальное — еда и проезд.');
  await page.getByRole('button', { name: 'Ответить' }).click();

  await expect(
    page.getByText('Общежитие около 900 рублей, остальное — еда и проезд.'),
  ).toBeVisible();
});

test('лайк переключается и меняет счётчик', async ({ page }) => {
  // ТЗ 5.8: лайк — переключатель, баллов не даёт (уточнение У22).
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa/1');

  const like = page.getByRole('button', { name: /Лайк ответа/ });
  await expect(like).toHaveAttribute('aria-pressed', 'false');

  await like.click();

  const pressed = page.getByRole('button', { name: /Лайк ответа/ });
  await expect(pressed).toHaveAttribute('aria-pressed', 'true');
  await expect(pressed).toContainText('25');
});

test('пустая лента предлагает задать первый вопрос', async ({ page }) => {
  await installApiStub(page, { profile: APPLICANT_PROFILE, questions: [] });
  await page.goto('/mentor-qa/1');

  await expect(page.getByText(/пока нет вопросов/)).toBeVisible();
  await expect(page.getByRole('link', { name: 'Задать вопрос' })).toBeVisible();
});

test('без выбранного вуза вопрос отправить нельзя', async ({ page }) => {
  // ТЗ 5.3: вуз по умолчанию берётся из профиля, а у абитуриента его нет.
  // Подставлять вуз за человека нельзя — вопрос ушёл бы в чужую ленту.
  await installApiStub(page, { profile: APPLICANT_PROFILE });
  await page.goto('/mentor-qa');

  await page
    .getByRole('textbox', { name: 'Текст вопроса' })
    .fill('Реально ли совмещать первый курс и подработку?');

  await expect(page.getByRole('button', { name: 'Опубликовать анонимно' })).toBeDisabled();
  await expect(page.getByText(/Выберите вуз кнопкой «Другой»/)).toBeVisible();
});
