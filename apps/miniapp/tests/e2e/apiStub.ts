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

/** Предметы ЕГЭ и границы проверки — как их отдаёт настоящий API. */
export const SUBJECTS = {
  subjects: [
    'Русский язык',
    'Математика',
    'Информатика',
    'Физика',
    'Обществознание',
    'Биология',
    'История',
    'Химия',
  ],
  min_subjects: 3,
  min_score: 0,
  max_score: 100,
};

const REQUIRED_SUBJECTS: Record<string, string[]> = {
  applied_mathematics: ['Русский язык', 'Математика', 'Информатика'],
  information_systems: ['Русский язык', 'Математика', 'Информатика'],
  software_engineering: ['Русский язык', 'Математика', 'Информатика'],
  jurisprudence: ['Русский язык', 'Обществознание', 'История'],
};

export const CATALOGUE_DIRECTIONS = Object.entries(REQUIRED_SUBJECTS).map(([code, subjects]) => ({
  code,
  name:
    code === 'jurisprudence'
      ? 'Юриспруденция'
      : (Object.values(DIRECTIONS).find((direction) => direction.code === code)?.name ?? code),
  summary: 'Направление из справочника проекта.',
  required_subjects: subjects,
}));

/**
 * Три программы с разными проходными: на баллах из теста они дают по одной
 * метке каждого вида, и экран шансов проверяется целиком.
 */
export const PROGRAMS = [
  { program_id: 11, university: 1, short_name: 'МГУ', direction: 'applied_mathematics', pass: 290 },
  {
    program_id: 12,
    university: 2,
    short_name: 'УрФУ',
    direction: 'information_systems',
    pass: 270,
  },
  {
    program_id: 13,
    university: 3,
    short_name: 'ЮФУ',
    direction: 'software_engineering',
    pass: 240,
  },
  {
    program_id: 14,
    university: 1,
    short_name: 'МГУ',
    direction: 'jurisprudence',
    pass: 250,
  },
];

/** Баллы, при которых видны все три метки шанса. */
export const TECH_SCORES = { 'Русский язык': 88, Математика: 92, Информатика: 95 };

const DEMO_FIELDS = ['passing_score', 'budget_places', 'tuition_price', 'admission_deadline'];

function university(id: number) {
  const program = PROGRAMS.find((item) => item.university === id);
  if (program === undefined) return null;
  return {
    id,
    name: `${program.short_name} — полное название`,
    short_name: program.short_name,
    city: 'Москва',
    address: 'Ленинские горы, 1',
    budget_places: 120,
    tuition_price: 498000,
    has_dormitory: true,
    admission_deadline: '2026-07-25',
  };
}

/** Формула уточнения У12 — повторена здесь, чтобы выдача заглушки была честной. */
function chanceOf(gap: number): string {
  if (gap >= 8) return 'high';
  if (gap >= -10) return 'borderline';
  return 'unlikely';
}

const CHANCE_ORDER: Record<string, number> = { high: 0, borderline: 1, unlikely: 2 };

/** Порядок метки. Неизвестной метки быть не может, но `noUncheckedIndexedAccess` об этом не знает. */
function chanceOrder(chance: string): number {
  return CHANCE_ORDER[chance] ?? CHANCE_ORDER.unlikely ?? 2;
}

function matchesFor(scores: Record<string, number>, universityId?: number) {
  return PROGRAMS.filter(
    (program) => universityId === undefined || program.university === universityId,
  )
    .flatMap((program) => {
      const required = REQUIRED_SUBJECTS[program.direction] ?? [];
      if (!required.every((subject) => subject in scores)) return [];
      const total = required.reduce((sum, subject) => sum + (scores[subject] ?? 0), 0);
      const direction = CATALOGUE_DIRECTIONS.find((item) => item.code === program.direction);
      return [
        {
          program_id: program.program_id,
          university: university(program.university),
          direction,
          chance: chanceOf(total - program.pass),
          applicant_score: total,
          passing_score: program.pass,
          budget_places: 120,
          demo_fields: DEMO_FIELDS,
          gap: total - program.pass,
        },
      ];
    })
    .sort((a, b) => chanceOrder(a.chance) - chanceOrder(b.chance) || b.gap - a.gap);
}

/** Состояние заглушки: баллы и трекер переживают запросы, как в настоящем API. */
interface StubState {
  scores: Record<string, number>;
  tracked: Set<number>;
}

/** Что отдавать на какой путь. Ключ — метод и путь без строки запроса. */
function response(method: string, path: string, body: unknown, state: StubState): unknown {
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

  if (method === 'GET' && path === '/api/v1/vuz-selection/subjects') return SUBJECTS;
  if (method === 'GET' && path === '/api/v1/vuz-selection/directions') return CATALOGUE_DIRECTIONS;
  if (method === 'GET' && path === '/api/v1/vuz-selection/scores') {
    return scoresBody(state.scores);
  }
  if (method === 'POST' && path === '/api/v1/vuz-selection/scores') {
    state.scores = (body as { scores?: Record<string, number> }).scores ?? {};
    return scoresBody(state.scores);
  }
  if (method === 'GET' && path === '/api/v1/vuz-selection/matches') {
    const items = matchesFor(state.scores);
    return {
      total: Object.values(state.scores).reduce((sum, score) => sum + score, 0),
      items,
    };
  }

  const card = /^\/api\/v1\/vuz-selection\/universities\/(\d+)$/.exec(path);
  if (method === 'GET' && card) {
    const id = Number(card[1]);
    const found = university(id);
    if (found === null) return undefined;
    return {
      university: found,
      programs: matchesFor(state.scores, id),
      tracked: state.tracked.has(id),
      demo_fields: DEMO_FIELDS,
    };
  }

  const track = /^\/api\/v1\/vuz-selection\/track\/(\d+)$/.exec(path);
  if (method === 'POST' && track) {
    const id = Number(track[1]);
    const found = university(id);
    if (found === null) return undefined;
    state.tracked.add(id);
    const code = (body as { direction?: string | null }).direction ?? null;
    return {
      university: found,
      direction: CATALOGUE_DIRECTIONS.find((item) => item.code === code) ?? null,
    };
  }

  return undefined;
}

function scoresBody(scores: Record<string, number>) {
  return {
    scores,
    total: Object.values(scores).reduce((sum, score) => sum + score, 0),
    min_subjects: SUBJECTS.min_subjects,
  };
}

export async function installApiStub(page: Page): Promise<void> {
  // Состояние своё на каждый тест: иначе отслеженный вуз из одного теста
  // влиял бы на надпись кнопки в другом.
  const state: StubState = { scores: {}, tracked: new Set<number>() };

  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    // Запрос с телом и заголовком опознания браузер предваряет preflight —
    // без ответа на него до самого запроса дело не дойдёт.
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }

    const path = new URL(request.url()).pathname;
    const payload = request.method() === 'POST' ? safeJson(request.postData()) : undefined;
    const body = response(request.method(), path, payload, state);
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

function safeJson(raw: string | null): unknown {
  if (raw === null || raw === '') return undefined;
  try {
    return JSON.parse(raw);
  } catch {
    return undefined;
  }
}
