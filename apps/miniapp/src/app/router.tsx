/**
 * Дерево роутов.
 *
 * Собирается из реестра `screens.ts`: каждому идентификатору экрана — свой
 * компонент. Карта компонентов объявлена как `Record<ScreenId, ...>`, поэтому
 * забытый экран — ошибка компиляции, а не пустая страница в проде.
 *
 * Все роуты без исключения вложены в `AppLayout` — так требование ТЗ 1.1
 * («кнопка 🏠 Главное меню на каждом экране») выполняется архитектурно
 * (тех. ТЗ 8.3).
 *
 * Разбиение бандла по роутам (`React.lazy`) появится вместе с настоящим
 * содержимым экранов: делить бандл на семнадцать заглушек по десять строк
 * значит платить за это лишними запросами и ничего не выигрывать.
 */
import type { ComponentType } from 'react';
import { createBrowserRouter, type RouteObject } from 'react-router-dom';

import { CareerTestResultsScreen } from '@/screens/CareerTestResultsScreen';
import { CareerTestScreen } from '@/screens/CareerTestScreen';
import { FoodScreen } from '@/screens/FoodScreen';
import { GateScreen } from '@/screens/GateScreen';
import { LeaderboardScreen } from '@/screens/LeaderboardScreen';
import { MentorQaFeedScreen } from '@/screens/MentorQaFeedScreen';
import { MentorQaScreen } from '@/screens/MentorQaScreen';
import { MenuScreen } from '@/screens/MenuScreen';
import { NotFoundScreen } from '@/screens/NotFoundScreen';
import { ProfileScreen } from '@/screens/ProfileScreen';
import { ScheduleScreen } from '@/screens/ScheduleScreen';
import { SupportScreen } from '@/screens/SupportScreen';
import { TrackerDetailScreen } from '@/screens/TrackerDetailScreen';
import { TrackerScreen } from '@/screens/TrackerScreen';
import { VuzCardScreen } from '@/screens/VuzCardScreen';
import { VuzSelectionResultsScreen } from '@/screens/VuzSelectionResultsScreen';
import { VuzSelectionScreen } from '@/screens/VuzSelectionScreen';

import { AppLayout, type ScreenHandle } from './AppLayout';
import { SCREENS, type ScreenId } from './screens';

const COMPONENTS: Record<ScreenId, ComponentType> = {
  menu: MenuScreen,
  profile: ProfileScreen,
  'career-test': CareerTestScreen,
  'career-test-results': CareerTestResultsScreen,
  'vuz-selection': VuzSelectionScreen,
  'vuz-selection-results': VuzSelectionResultsScreen,
  'vuz-card': VuzCardScreen,
  tracker: TrackerScreen,
  'tracker-detail': TrackerDetailScreen,
  gate: GateScreen,
  schedule: ScheduleScreen,
  'mentor-qa': MentorQaScreen,
  'mentor-qa-feed': MentorQaFeedScreen,
  leaderboard: LeaderboardScreen,
  food: FoodScreen,
  support: SupportScreen,
  'not-found': NotFoundScreen,
};

/** Роуты в форме, пригодной и для браузера, и для тестов с памятью истории. */
export function buildRoutes(): RouteObject[] {
  return [
    {
      element: <AppLayout />,
      children: SCREENS.map((screen) => {
        const Screen = COMPONENTS[screen.id];
        const handle: ScreenHandle = { screenId: screen.id };
        return { path: screen.path, element: <Screen />, handle };
      }),
    },
  ];
}

export function createRouter() {
  return createBrowserRouter(buildRoutes());
}
