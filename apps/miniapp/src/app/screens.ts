/**
 * Реестр экранов — единственный источник правды о дереве роутов.
 *
 * Здесь нет ни React, ни компонентов: файл читают и роутер (`router.tsx`), и
 * e2e-тест обхода всех экранов (`tests/e2e/navigation.spec.ts`). Требование
 * ТЗ 1.1 «кнопка 🏠 Главное меню на каждом экране без исключений» проверяется
 * автоматически ровно потому, что список экранов один: новый экран, не
 * попавший в этот массив, не попадёт и в роутер, а попавший — будет проверен
 * тестом (тех. ТЗ 8.3, 9.5).
 */

/** Идентификатор экрана. Совпадает с `data-scr` прототипа, где тот есть. */
export type ScreenId =
  | 'menu'
  | 'profile'
  | 'career-test'
  | 'career-test-results'
  | 'vuz-selection'
  | 'vuz-selection-results'
  | 'vuz-card'
  | 'tracker'
  | 'tracker-detail'
  | 'gate'
  | 'schedule'
  | 'mentor-qa'
  | 'mentor-qa-feed'
  | 'leaderboard'
  | 'food'
  | 'support'
  | 'not-found';

export interface ScreenRoute {
  readonly id: ScreenId;
  /** Шаблон пути для React Router. */
  readonly path: string;
  /** Имя экрана: caps-заголовок в шапке и подпись в отчётах тестов. */
  readonly label: string;
  /**
   * Конкретный URL для обхода в e2e. Для экранов с параметрами это шаблон,
   * подставленный демонстрационным значением: тест ходит по настоящим
   * адресам, а не по шаблонам.
   */
  readonly e2ePath: string;
}

/**
 * Шестнадцать экранов дизайн-хендоффа плюс экран «адрес не найден».
 *
 * Семнадцатый экран нарисован не был, но без него требование «тупиковых
 * экранов нет» дырявое: по неизвестному адресу (старая ссылка, опечатка в
 * диплинке) пользователь оказался бы на пустой странице без выхода.
 */
export const SCREENS: readonly ScreenRoute[] = [
  { id: 'menu', path: '/', label: 'Главное меню', e2ePath: '/' },
  { id: 'profile', path: '/profile', label: 'Мой профиль', e2ePath: '/profile' },
  {
    id: 'career-test',
    path: '/career-test',
    label: 'Профориентационный тест',
    e2ePath: '/career-test',
  },
  {
    id: 'career-test-results',
    path: '/career-test/results',
    label: 'Результат теста',
    e2ePath: '/career-test/results',
  },
  {
    id: 'vuz-selection',
    path: '/vuz-selection',
    label: 'Подбор вуза по баллам ЕГЭ',
    e2ePath: '/vuz-selection',
  },
  {
    id: 'vuz-selection-results',
    path: '/vuz-selection/results',
    label: 'Шансы поступления',
    e2ePath: '/vuz-selection/results',
  },
  {
    id: 'vuz-card',
    path: '/vuz-selection/:universityId',
    label: 'Карточка вуза',
    e2ePath: '/vuz-selection/1',
  },
  { id: 'tracker', path: '/tracker', label: 'Трекер конкурсных списков', e2ePath: '/tracker' },
  {
    id: 'tracker-detail',
    path: '/tracker/:universityId',
    label: 'Позиция в списке',
    e2ePath: '/tracker/1',
  },
  {
    id: 'gate',
    path: '/gate/:section',
    label: 'Нужен статус студента',
    e2ePath: '/gate/schedule',
  },
  { id: 'schedule', path: '/schedule', label: 'Расписание и дедлайны', e2ePath: '/schedule' },
  {
    id: 'mentor-qa',
    path: '/mentor-qa',
    label: 'Спроси у старшекурсника',
    e2ePath: '/mentor-qa',
  },
  {
    id: 'mentor-qa-feed',
    path: '/mentor-qa/:universityId',
    label: 'Лента вопросов',
    e2ePath: '/mentor-qa/1',
  },
  { id: 'leaderboard', path: '/leaderboard', label: 'Рейтинг активности', e2ePath: '/leaderboard' },
  { id: 'food', path: '/food', label: 'Где покушать', e2ePath: '/food' },
  { id: 'support', path: '/support', label: 'Поддержка', e2ePath: '/support' },
  {
    id: 'not-found',
    path: '*',
    label: 'Адрес не найден',
    e2ePath: '/такого-адреса-нет',
  },
];
