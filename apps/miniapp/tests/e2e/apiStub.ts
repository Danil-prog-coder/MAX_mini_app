import type { Page, Route } from '@playwright/test';

/**
 * Заглушка Core API для e2e.
 *
 * e2e проверяет фронтенд, а не бэкенд: поднимать ради него Postgres, Redis и
 * два сервиса — значит превратить быструю проверку навигации в долгую и
 * хрупкую. Ответы отдаёт Playwright, перехватывая запросы страницы.
 *
 * Побочная польза: без заглушки каждый экран писал бы в консоль ошибку сети, а
 * обход всех роутов проверяет в том числе чистую консоль — и эта проверка
 * перестала бы что-либо значить.
 *
 * Данные повторяют то, что отдаёт настоящий API после заливки справочников:
 * тексты вопросов — из макета, направления — из справочника проекта.
 */

const CORS_HEADERS = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': '*',
  'Access-Control-Allow-Methods': 'GET,POST,PATCH,DELETE,OPTIONS',
};

export const PROFILE = {
  max_user_id: 'e2e-user',
  display_name: 'Артём',
  needs_display_name: false,
  status: 'applicant',
  university: null,
  group_name: null,
  is_verified_student: false,
  points_balance: 540,
  access: { schedule: false, food: false, answer_questions: false },
};

/** Первый вопрос — дословно из макета, остальные подписаны номером. */
export const QUESTIONS = Array.from({ length: 10 }, (_, index) => ({
  id: index + 1,
  order: index + 1,
  text:
    index === 0
      ? 'Что из этого вам ближе в свободный вечер?'
      : `Вопрос ${String(index + 1)} профориентационного теста`,
  options: [
    { id: index * 3 + 1, order: 1, text: 'Разобрать, как что-то устроено внутри' },
    { id: index * 3 + 2, order: 2, text: 'Придумать и нарисовать своё' },
    { id: index * 3 + 3, order: 3, text: 'Поговорить с людьми и что-то организовать' },
  ],
}));

/** Направления результата по именам: тесты не индексируют массив вслепую. */
export const DIRECTIONS = {
  first: {
    code: 'applied_mathematics',
    name: 'Прикладная математика и информатика',
    summary: 'Задачи, где ответ надо вывести, а не угадать.',
    match_percent: 100,
  },
  second: {
    code: 'information_systems',
    name: 'Информационные системы и технологии',
    summary: 'Соединять людей, данные и программы в работающую систему.',
    match_percent: 90,
  },
  third: {
    code: 'software_engineering',
    name: 'Программная инженерия',
    summary: 'Разбираться, как устроена система, и собирать её самому.',
    match_percent: 83,
  },
};

export const TEST_RESULT = {
  id: 1,
  profile: { analyst: 10 },
  top_directions: [DIRECTIONS.first, DIRECTIONS.second, DIRECTIONS.third],
  explanation: 'Вы выбираете задачи с понятной логикой и доводите их до конца.',
  saved_to_profile: false,
  created_at: '2026-08-18T09:00:00Z',
};

export const VACANCIES = {
  direction: 'applied_mathematics',
  items: [
    { title: 'Аналитик данных', count: 2410 },
    { title: 'Data scientist', count: 860 },
    { title: 'BI-аналитик', count: 1290 },
    { title: 'Математик', count: 140 },
  ],
  stale: false,
  source: 'fixture',
};

/** Что отдавать на какой путь. Ключ — метод и путь без строки запроса. */
function response(method: string, path: string): unknown {
  if (method === 'GET' && path === '/api/v1/users/me') return PROFILE;
  if (method === 'GET' && path === '/api/v1/career-test/questions') return QUESTIONS;
  if (method === 'GET' && path === '/api/v1/career-test/results/latest') return TEST_RESULT;
  if (method === 'GET' && path === '/api/v1/career-test/vacancies') return VACANCIES;
  if (method === 'POST' && path === '/api/v1/career-test/submit') return TEST_RESULT;
  if (method === 'POST' && /^\/api\/v1\/career-test\/results\/\d+\/save$/.test(path)) {
    return {
      result: { ...TEST_RESULT, saved_to_profile: true },
      points_granted: true,
      points_balance: PROFILE.points_balance + 50,
    };
  }
  return undefined;
}

export async function installApiStub(page: Page): Promise<void> {
  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    // Запрос с телом и заголовком опознания браузер предваряет preflight —
    // без ответа на него до самого запроса дело не дойдёт.
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }

    const path = new URL(request.url()).pathname;
    const body = response(request.method(), path);
    if (body === undefined) {
      // Неизвестный путь — честный 404 с телом ошибки: так ведёт себя и
      // настоящий API, а экран покажет пустое состояние, а не сбой сети.
      await route.fulfill({
        status: 404,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'не найдено' }),
      });
      return;
    }

    await route.fulfill({
      status: 200,
      headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
  });
}
