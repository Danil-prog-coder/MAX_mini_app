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

export const UNIVERSITIES = [
  {
    id: 1,
    name: 'Московский государственный университет',
    short_name: 'МГУ',
    city: 'Москва',
    address: 'Ленинские горы, 1',
    latitude: 55.7,
    longitude: 37.53,
    budget_places: 120,
    tuition_price: 498000,
    has_dormitory: true,
    admission_deadline: '2026-07-25',
    demo_fields: ['budget_places', 'tuition_price', 'has_dormitory', 'admission_deadline'],
  },
];

/**
 * Профиль студента с вузом — стартовое состояние заглушки.
 *
 * Именно студент, а не абитуриент по умолчанию: обход всех роутов требует,
 * чтобы каждый адрес показывал **свой** экран, а закрытые разделы 4 и 7
 * уводят абитуриента на гейт. Тесты гейта просят абитуриента явно.
 */
export const STUDENT_PROFILE = {
  status: 'student',
  university: UNIVERSITIES[0] ?? null,
};

/** Абитуриент без вуза: разделы 4 и 7 для него закрыты (ТЗ 4.2, 7.2). */
export const APPLICANT_PROFILE = {
  status: 'applicant',
  university: null,
};

/** Группы вуза — как их отдаёт настоящий API (ТЗ 4.3, уточнение У13). */
export const GROUPS = [
  { name: 'ИС-231' },
  { name: 'ИС-232' },
  { name: 'ПД-204' },
  { name: 'ПМ-211' },
];

export const PROFILE = {
  max_user_id: 'e2e-user',
  display_name: 'Артём',
  needs_display_name: false,
  status: 'student',
  university: UNIVERSITIES[0] as (typeof UNIVERSITIES)[number] | null,
  group_name: null as string | null,
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

function university(id: number, programs: typeof PROGRAMS = PROGRAMS) {
  // Ищем в переданном списке, а не в глобальном: тесты пагинации подставляют
  // свои программы, и вуз из них глобальному списку неизвестен.
  const program =
    programs.find((item) => item.university === id) ??
    PROGRAMS.find((item) => item.university === id);
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

/** Направление, которое «поднял» тест: заглушке хватает одного. */
const CAREER_TEST_TOP_DIRECTION = 'applied_mathematics';

const CHANCE_ORDER: Record<string, number> = { high: 0, borderline: 1, unlikely: 2 };

/** Порядок метки. Неизвестной метки быть не может, но `noUncheckedIndexedAccess` об этом не знает. */
function chanceOrder(chance: string): number {
  return CHANCE_ORDER[chance] ?? CHANCE_ORDER.unlikely ?? 2;
}

function matchesFor(
  scores: Record<string, number>,
  universityId?: number,
  programs: typeof PROGRAMS = PROGRAMS,
) {
  return programs
    .filter((program) => universityId === undefined || program.university === universityId)
    .flatMap((program) => {
      const required = REQUIRED_SUBJECTS[program.direction] ?? [];
      if (!required.every((subject) => subject in scores)) return [];
      const total = required.reduce((sum, subject) => sum + (scores[subject] ?? 0), 0);
      const direction = CATALOGUE_DIRECTIONS.find((item) => item.code === program.direction);
      return [
        {
          program_id: program.program_id,
          university: university(program.university, programs),
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

/** Подписи столбиков динамики за неделю — как их отдаёт настоящий API. */
const WEEKDAYS = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'];

const MIN_POSITION = 1;
const MAX_POSITION = 9999;

/** Пары на сегодня — день группы ИС-231 из макета, экран 11. */
export const LESSONS = [
  {
    starts_at: '09:00',
    ends_at: '10:30',
    title: 'Базы данных',
    room: '312',
    kind: 'лекция',
    is_now: true,
  },
  {
    starts_at: '10:40',
    ends_at: '12:10',
    title: 'Дискретная математика',
    room: '118',
    kind: 'семинар',
    is_now: false,
  },
  {
    starts_at: '12:20',
    ends_at: '13:50',
    title: 'Проектирование интерфейсов',
    room: '405',
    kind: 'практика',
    is_now: false,
  },
  {
    starts_at: '14:10',
    ends_at: '15:40',
    title: 'Иностранный язык',
    room: '207',
    kind: 'семинар',
    is_now: false,
  },
];

/** Темы вопросов — как их отдаёт настоящий API (ТЗ 5.2). */
export const TOPICS = [
  { code: 'admission', label: 'Поступление' },
  { code: 'study', label: 'Учёба' },
  { code: 'student_life', label: 'Студенческая жизнь' },
];

interface StubQuestion {
  id: number;
  topic: string;
  topic_label: string;
  text: string;
  moderation_status: string;
  moderation_reason: string;
  mine: boolean;
  university_id: number;
  answers: {
    id: number;
    text: string;
    author_name: string;
    likes_count: number;
    liked_by_me: boolean;
    created_at: string;
  }[];
  created_at: string;
}

/** Один готовый вопрос в ленте: без него лента пуста на каждом обходе роутов. */
export const SEEDED_QUESTION: StubQuestion = {
  id: 1,
  topic: 'admission',
  topic_label: 'Поступление',
  text: 'Сколько реально стоит жизнь в общежитии за месяц?',
  moderation_status: 'published',
  moderation_reason: '',
  mine: false,
  university_id: 1,
  answers: [
    {
      id: 1,
      text: 'Общежитие — около 900 ₽ в месяц, плюс еда. У меня выходит 9–11 тысяч.',
      author_name: 'Марина',
      likes_count: 24,
      liked_by_me: false,
      created_at: '2026-08-17T10:00:00Z',
    },
  ],
  created_at: '2026-08-17T09:00:00Z',
};

/** Слова, на которых заглушка модерации отклоняет вопрос (уточнение У18). */
const REJECT_WORDS = ['тупые', 'идиот'];
const REVIEW_WORDS = ['куплю', 'продам', '@'];

/** Состояние заглушки: профиль, баллы, трекер, позиции, дедлайны и лента. */
interface StubState {
  profile: typeof PROFILE;
  scores: Record<string, number>;
  tracked: Set<number>;
  /** Введённые места по вузу, от старых к новым. */
  positions: Map<number, number[]>;
  deadlines: { id: number; title: string; due_date: string }[];
  questions: StubQuestion[];
  checkedInToday: boolean;
  rewards: Set<string>;
  notifications: typeof NOTIFICATIONS;
  digestHour: number;
  mutedKinds: Set<string>;
  /** Пройден ли профориентационный тест (уточнение У28). */
  careerTestApplied: boolean;
  /** Программы, из которых собирается выдача подбора. */
  programs: typeof PROGRAMS;
  tickets: {
    id: number;
    category: string;
    category_label: string;
    text: string;
    auto_reply: string;
    admin_reply: string | null;
    admin_replied_at: string | null;
    sender: string;
    created_at: string;
  }[];
}

/** Типы уведомлений с подписями — как их отдаёт настоящий API (уточнение У9). */
export const NOTIFICATION_KINDS = [
  { code: 'admission_start', label: 'Старт приёма документов' },
  { code: 'admission_end', label: 'Окончание приёма документов' },
  { code: 'position_changed', label: 'Изменилась позиция в списке' },
  { code: 'schedule_digest', label: 'Ежедневная сводка расписания' },
  { code: 'deadline_soon', label: 'Скоро дедлайн' },
  { code: 'question_answered', label: 'Ответили на ваш вопрос' },
  { code: 'monthly_title', label: 'Статус месяца' },
  { code: 'support_reply', label: 'Ответ поддержки' },
];

/** Одно непрочитанное уведомление: бейдж и лента должны быть чем проверять. */
export const NOTIFICATIONS = [
  {
    id: 1,
    kind: 'deadline_soon',
    kind_label: 'Скоро дедлайн',
    title: 'Курсовая завтра',
    body: 'Курсовая по базам данных — завтра до 18:00.',
    payload: { screen: 'schedule' },
    read_at: null as string | null,
    created_at: '2026-08-18T09:00:00Z',
  },
];

/** Типы обращений (ТЗ 8.2) и по одной отписке из каждого пула (ТЗ 8.4). */
export const SUPPORT_CATEGORIES = [
  { code: 'bug', label: 'Что-то не работает' },
  { code: 'idea', label: 'Есть идея по улучшению' },
  { code: 'other', label: 'Другой вопрос' },
];

export const SUPPORT_REPLIES: Record<string, string> = {
  bug: 'Поймали, спасибо. Передал команде — обычно чиним в течение дня, о результате напишу сюда же.',
  idea: 'Отличная мысль, спасибо. Идеи собираем в общий список и раз в неделю разбираем с командой.',
  other: 'Спасибо за сообщение — оно ушло команде, ответ придёт сюда от имени «Поддержки».',
};

/** Точки питания — как их отдаёт настоящий API (ТЗ 7.5). */
export const SPOTS = [
  {
    id: 1,
    name: 'Столовая корпуса',
    kind: 'catering',
    place_type: 'столовая',
    address: 'Ленинские горы, 1, стр. 1',
    map_deeplink:
      'https://yandex.ru/maps/?ll=37.531900,55.700000&z=17&pt=37.531900,55.700000,pm2rdm',
    distance_score: 5,
    walk_minutes: 3,
    rating: 4.4,
    menu: 'комплексные обеды, супы, выпечка',
    has_bakery: null,
    assortment: null,
  },
  {
    id: 2,
    name: 'Продукты у корпуса',
    kind: 'shop',
    place_type: 'магазин',
    address: 'Ленинские горы, 1, стр. 2',
    map_deeplink:
      'https://yandex.ru/maps/?ll=37.526200,55.700000&z=17&pt=37.526200,55.700000,pm2rdm',
    distance_score: 4,
    walk_minutes: 6,
    rating: null,
    menu: null,
    has_bakery: true,
    assortment: 'средний',
  },
];

/** Награды с ценами уточнения У23. */
export const REWARDS = [
  { code: 'question_priority', title: 'Приоритет показа вопроса', price: 300 },
  { code: 'profile_badge', title: 'Бейдж в профиле', price: 500 },
];

/** Рейтинг за неделю. Вуза в нём нет и быть не должно (уточнение У19). */
export const LEADERBOARD = [
  { place: 1, display_name: 'Кирилл М.', points: 1480, has_title: true, mine: false },
  { place: 2, display_name: 'Мария Л.', points: 1190, has_title: false, mine: false },
  { place: 3, display_name: 'Даниил П.', points: 980, has_title: false, mine: false },
];

/** Права считает сервер (решение Р19) — заглушка повторяет ту же функцию. */
function accessOf(profile: typeof PROFILE) {
  const isStudent = profile.status === 'student' && profile.university !== null;
  return {
    schedule: isStudent,
    food: isStudent,
    answer_questions: isStudent && profile.is_verified_student,
  };
}

function withAccess(profile: typeof PROFILE) {
  return { ...profile, access: accessOf(profile) };
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10);
}

function trackedDirection(universityId: number) {
  const program = PROGRAMS.find((item) => item.university === universityId);
  if (program === undefined) return null;
  return CATALOGUE_DIRECTIONS.find((item) => item.code === program.direction) ?? null;
}

function trackedBrief(universityId: number) {
  const full = university(universityId);
  if (full === null) return null;
  return {
    id: full.id,
    short_name: full.short_name,
    city: full.city,
    admission_deadline: full.admission_deadline,
  };
}

function positionsBody(universityId: number, state: StubState) {
  const brief = trackedBrief(universityId);
  if (brief === null) return undefined;
  const history = state.positions.get(universityId) ?? [];
  const position = history.at(-1) ?? null;
  const previous = history.at(-2) ?? null;
  // Все записи заглушки делаются «сегодня», поэтому занят один столбик недели.
  const today = new Date().getDay();
  const index = today === 0 ? 6 : today - 1;

  return {
    university: brief,
    direction: trackedDirection(universityId),
    position,
    previous_position: previous,
    improvement: position !== null && previous !== null ? previous - position : null,
    estimated_passing_score: position === null ? null : 120,
    checked_at: position === null ? null : new Date().toISOString(),
    week: WEEKDAYS.map((weekday, at) => ({
      weekday,
      position: at === index ? position : null,
    })),
    history: history.map((value) => ({
      position: value,
      estimated_passing_score: 120,
      checked_at: new Date().toISOString(),
    })),
    min_position: MIN_POSITION,
    max_position: MAX_POSITION,
  };
}

/** Раздел закрыт по статусу: заглушка отвечает 403, как настоящий API. */
const FORBIDDEN = Symbol('forbidden');

/** Что отдавать на какой путь. Ключ — метод и путь без строки запроса. */
function response(method: string, path: string, body: unknown, state: StubState): unknown {
  if (method === 'GET' && path === '/api/v1/users/me') return withAccess(state.profile);
  if (method === 'PATCH' && path === '/api/v1/users/me') {
    const patch = body as {
      status?: string;
      university_id?: number;
      group_name?: string;
      display_name?: string;
    };
    if (patch.status !== undefined) state.profile.status = patch.status;
    if (patch.display_name !== undefined) {
      state.profile.display_name = patch.display_name;
      // Настоящий API пересчитывает признак: имя введено — строка ввода уходит.
      state.profile.needs_display_name = patch.display_name === '';
    }
    if (patch.university_id !== undefined) {
      state.profile.university =
        UNIVERSITIES.find((item) => item.id === patch.university_id) ?? null;
    }
    if (patch.group_name !== undefined) state.profile.group_name = patch.group_name;
    return withAccess(state.profile);
  }
  if (method === 'POST' && path === '/api/v1/users/me/verification') {
    state.profile.is_verified_student = true;
    return withAccess(state.profile);
  }
  if (method === 'GET' && path === '/api/v1/universities') return UNIVERSITIES;

  if (path.startsWith('/api/v1/schedule')) {
    // Гейт ТЗ 4.2 отвечает 403 на весь раздел, а не только прячет пункт меню.
    if (!accessOf(state.profile).schedule) return FORBIDDEN;
    if (method === 'GET' && path === '/api/v1/schedule/groups') return GROUPS;
    if (method === 'POST' && path === '/api/v1/schedule/source') {
      const name = (body as { group_name?: string }).group_name ?? '';
      if (!GROUPS.some((group) => group.name === name)) return undefined;
      state.profile.group_name = name;
      return { name };
    }
    if (method === 'GET' && path === '/api/v1/schedule/today') {
      return {
        day: todayIso(),
        group_name: state.profile.group_name,
        lessons: state.profile.group_name === null ? [] : LESSONS,
        deadlines: state.deadlines,
      };
    }
    if (method === 'POST' && path === '/api/v1/schedule/deadlines') {
      const payload = body as { title?: string; due_date?: string };
      if (!payload.title?.trim() || payload.due_date === undefined) return undefined;
      const deadline = {
        id: state.deadlines.length + 1,
        title: payload.title.trim(),
        due_date: payload.due_date,
      };
      state.deadlines = [...state.deadlines, deadline].sort((a, b) =>
        a.due_date.localeCompare(b.due_date),
      );
      return deadline;
    }
  }
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
    const items = matchesFor(state.scores, undefined, state.programs);
    return {
      total: Object.values(state.scores).reduce((sum, score) => sum + score, 0),
      items,
      career_test_applied: state.careerTestApplied,
      career_test_directions: state.careerTestApplied ? [CAREER_TEST_TOP_DIRECTION] : [],
    };
  }

  const card = /^\/api\/v1\/vuz-selection\/universities\/(\d+)$/.exec(path);
  if (method === 'GET' && card) {
    const id = Number(card[1]);
    const found = university(id);
    if (found === null) return undefined;
    return {
      university: found,
      programs: matchesFor(state.scores, id, state.programs),
      tracked: state.tracked.has(id),
      demo_fields: DEMO_FIELDS,
    };
  }

  if (method === 'GET' && path === '/api/v1/tracker') {
    const items = [...state.tracked].flatMap((id) => {
      const brief = trackedBrief(id);
      if (brief === null) return [];
      return [
        {
          university: brief,
          direction: trackedDirection(id),
          position: state.positions.get(id)?.at(-1) ?? null,
        },
      ];
    });
    return { total: items.length, items };
  }

  if (method === 'GET' && path === '/api/v1/notifications') {
    return {
      total: state.notifications.length,
      unread: state.notifications.filter((item) => item.read_at === null).length,
      items: state.notifications,
    };
  }

  const read = /^\/api\/v1\/notifications\/(\d+)\/read$/.exec(path);
  if (method === 'POST' && read) {
    const item = state.notifications.find((row) => row.id === Number(read[1]));
    if (item === undefined) return undefined;
    item.read_at ??= new Date().toISOString();
    return item;
  }

  if (path === '/api/v1/notifications/settings') {
    if (method === 'PATCH') {
      const patch = body as { digest_hour?: number; muted_kinds?: string[] };
      if (patch.digest_hour !== undefined) state.digestHour = patch.digest_hour;
      if (patch.muted_kinds !== undefined) state.mutedKinds = new Set(patch.muted_kinds);
    }
    return {
      digest_hour: state.digestHour,
      kinds: NOTIFICATION_KINDS.map((kind) => ({
        ...kind,
        muted: state.mutedKinds.has(kind.code),
      })),
      min_hour: 0,
      max_hour: 23,
    };
  }

  if (method === 'GET' && path === '/api/v1/support/categories') return SUPPORT_CATEGORIES;

  if (method === 'GET' && path === '/api/v1/support/tickets') {
    return { total: state.tickets.length, items: state.tickets };
  }

  if (method === 'POST' && path === '/api/v1/support/tickets') {
    const payload = body as { category?: string; text?: string };
    const code = payload.category ?? 'other';
    const label = SUPPORT_CATEGORIES.find((item) => item.code === code)?.label ?? '';
    const reply = SUPPORT_REPLIES[code] ?? SUPPORT_REPLIES.other ?? '';
    const ticket = {
      id: state.tickets.length + 1,
      category: code,
      category_label: label,
      text: payload.text?.trim() ?? '',
      auto_reply: reply,
      admin_reply: null,
      admin_replied_at: null,
      sender: 'Поддержка',
      created_at: new Date().toISOString(),
    };
    state.tickets = [ticket, ...state.tickets];
    return { ticket, reply, sender: 'Поддержка' };
  }

  if (path.startsWith('/api/v1/food')) {
    // Гейт ТЗ 7.2 закрывает раздел целиком, а не только пункт меню.
    if (!accessOf(state.profile).food) return FORBIDDEN;
    if (method === 'GET' && path === '/api/v1/food/nearby') {
      return {
        total: SPOTS.length,
        university_address: 'Москва, Ленинские горы, 1',
        items: SPOTS,
        demo: true,
      };
    }
  }

  if (method === 'GET' && path === '/api/v1/gamification/me') {
    return {
      balance: state.profile.points_balance,
      checked_in_today: state.checkedInToday,
      title: null,
      rewards: REWARDS.map((reward) => ({ ...reward, owned: state.rewards.has(reward.code) })),
      history: [],
    };
  }

  if (method === 'GET' && path === '/api/v1/gamification/leaderboard') {
    const mine = {
      place: LEADERBOARD.length + 1,
      display_name: state.profile.display_name,
      points: state.profile.points_balance,
      has_title: false,
      mine: true,
    };
    return { rows: [...LEADERBOARD, mine], me: mine, to_next_place: 60 };
  }

  if (method === 'POST' && path === '/api/v1/gamification/checkin') {
    const granted = !state.checkedInToday;
    if (granted) {
      state.checkedInToday = true;
      state.profile.points_balance += 10;
    }
    return {
      granted,
      balance: state.profile.points_balance,
      day: todayIso(),
    };
  }

  const reward = /^\/api\/v1\/gamification\/rewards\/([\w-]+)$/.exec(path);
  if (method === 'POST' && reward) {
    const code = reward[1] ?? '';
    const found = REWARDS.find((item) => item.code === code);
    if (found === undefined) return undefined;
    if (state.rewards.has(code)) {
      return {
        code,
        bought: false,
        already: true,
        not_enough: false,
        balance: state.profile.points_balance,
      };
    }
    if (state.profile.points_balance < found.price) {
      return {
        code,
        bought: false,
        already: false,
        not_enough: true,
        balance: state.profile.points_balance,
      };
    }
    state.rewards.add(code);
    state.profile.points_balance -= found.price;
    return {
      code,
      bought: true,
      already: false,
      not_enough: false,
      balance: state.profile.points_balance,
    };
  }

  if (method === 'GET' && path === '/api/v1/mentor-qa/topics') return TOPICS;

  if (method === 'GET' && path === '/api/v1/mentor-qa/questions') {
    const items = state.questions;
    return { total: items.length, items };
  }

  if (method === 'POST' && path === '/api/v1/mentor-qa/questions') {
    const payload = body as { university_id?: number; topic?: string; text?: string };
    const text = payload.text?.trim() ?? '';
    const lowered = text.toLowerCase();
    // Повторяет три исхода уточнения У18, чтобы экран проверялся целиком.
    const status = REJECT_WORDS.some((word) => lowered.includes(word))
      ? 'rejected'
      : REVIEW_WORDS.some((word) => lowered.includes(word))
        ? 'manual_review'
        : 'published';
    const topic = TOPICS.find((item) => item.code === payload.topic) ?? TOPICS[0];
    const question: StubQuestion = {
      id: state.questions.length + 100,
      topic: topic?.code ?? 'admission',
      topic_label: topic?.label ?? 'Поступление',
      text,
      moderation_status: status,
      moderation_reason: status === 'published' ? '' : 'текст не прошёл проверку',
      mine: true,
      university_id: payload.university_id ?? 1,
      answers: [],
      created_at: new Date().toISOString(),
    };
    state.questions = [question, ...state.questions];
    return {
      id: question.id,
      moderation_status: status,
      published: status === 'published',
      moderation_reason: question.moderation_reason,
    };
  }

  const newAnswer = /^\/api\/v1\/mentor-qa\/questions\/(\d+)\/answers$/.exec(path);
  if (method === 'POST' && newAnswer) {
    const question = state.questions.find((item) => item.id === Number(newAnswer[1]));
    if (question === undefined) return undefined;
    if (!accessOf(state.profile).answer_questions) return FORBIDDEN;
    const text = (body as { text?: string }).text?.trim() ?? '';
    const answer = {
      id: question.answers.length + 100,
      text,
      author_name: state.profile.display_name,
      likes_count: 0,
      liked_by_me: false,
      created_at: new Date().toISOString(),
    };
    question.answers = [...question.answers, answer];
    state.profile.points_balance += 25;
    return {
      id: answer.id,
      text,
      points_granted: true,
      points_balance: state.profile.points_balance,
    };
  }

  const like = /^\/api\/v1\/mentor-qa\/answers\/(\d+)\/like$/.exec(path);
  if (method === 'POST' && like) {
    const id = Number(like[1]);
    for (const question of state.questions) {
      const answer = question.answers.find((item) => item.id === id);
      if (answer === undefined) continue;
      answer.liked_by_me = !answer.liked_by_me;
      answer.likes_count += answer.liked_by_me ? 1 : -1;
      return { liked: answer.liked_by_me, likes_count: answer.likes_count };
    }
    return undefined;
  }

  const positions = /^\/api\/v1\/tracker\/(\d+)\/positions$/.exec(path);
  if (positions) {
    const id = Number(positions[1]);
    // Не отслеживаемый вуз — 404, как в настоящем API.
    if (!state.tracked.has(id)) return undefined;
    if (method === 'POST') {
      const value = (body as { position?: number }).position;
      if (typeof value !== 'number' || value < MIN_POSITION || value > MAX_POSITION) {
        return undefined;
      }
      state.positions.set(id, [...(state.positions.get(id) ?? []), value]);
    }
    return positionsBody(id, state);
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

/**
 * Вуз, отслеживаемый по умолчанию.
 *
 * Обход всех роутов ходит по адресу `/tracker/1` и требует, чтобы **каждый**
 * экран отвечал без ошибок в консоли. Настоящий API на не отслеживаемый вуз
 * честно отвечает 404, и браузер пишет это в консоль — значит, у заглушки по
 * умолчанию один вуз в трекере уже есть. Тесты, которым нужен пустой трекер,
 * говорят об этом явно: `installApiStub(page, { tracked: [] })`.
 */
const DEFAULT_TRACKED = [1];

export interface StubOptions {
  /** Идентификаторы вузов в трекере на старте теста. */
  readonly tracked?: readonly number[];
  /** Чем отличается стартовый профиль от `PROFILE`. */
  readonly profile?: Partial<typeof PROFILE>;
  /** Что уже лежит в ленте вопросов на старте теста. */
  readonly questions?: StubQuestion[];
  /** Что уже лежит в ленте уведомлений на старте теста. */
  readonly notifications?: typeof NOTIFICATIONS;
  /**
   * Пройден ли профориентационный тест (уточнение У28). Меняет плашку над
   * выдачей подбора; на сам список заглушка порядок не наводит — порядок
   * считает сервер, и проверять его на заглушке нечего.
   */
  readonly careerTestApplied?: boolean;
  /** Программы подбора: тесты пагинации подставляют свой, длинный список. */
  readonly programs?: typeof PROGRAMS;
}

export async function installApiStub(page: Page, options: StubOptions = {}): Promise<void> {
  // Состояние своё на каждый тест: иначе отслеженный вуз из одного теста
  // влиял бы на надпись кнопки в другом.
  const state: StubState = {
    // Копия, а не сам объект: тест, сделавший себя студентом, не должен
    // менять стартовый профиль следующего.
    profile: { ...PROFILE, ...options.profile },
    scores: {},
    tracked: new Set<number>(options.tracked ?? DEFAULT_TRACKED),
    positions: new Map<number, number[]>(),
    deadlines: [],
    questions: options.questions ?? [SEEDED_QUESTION],
    checkedInToday: false,
    rewards: new Set<string>(),
    tickets: [],
    notifications: options.notifications ?? NOTIFICATIONS.map((item) => ({ ...item })),
    digestHour: 8,
    mutedKinds: new Set<string>(),
    careerTestApplied: options.careerTestApplied ?? false,
    programs: options.programs ?? PROGRAMS,
  };

  await page.route('**/api/v1/**', async (route: Route) => {
    const request = route.request();
    // Запрос с телом и заголовком опознания браузер предваряет preflight —
    // без ответа на него до самого запроса дело не дойдёт.
    if (request.method() === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: CORS_HEADERS });
      return;
    }

    const path = new URL(request.url()).pathname;
    const hasBody = request.method() === 'POST' || request.method() === 'PATCH';
    const payload = hasBody ? safeJson(request.postData()) : undefined;
    const body = response(request.method(), path, payload, state);
    if (body === FORBIDDEN) {
      await route.fulfill({
        status: 403,
        headers: { ...CORS_HEADERS, 'Content-Type': 'application/json' },
        body: JSON.stringify({ detail: 'нужен статус «Студент» и заполненный вуз' }),
      });
      return;
    }
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
