/**
 * Главное меню — точка входа и точка возврата (ТЗ 1.2).
 *
 * Разделы перечислены ровно так, как в макете (`docs/design/source/app.jsx`,
 * массив `MENU`). Разделы 4 и 7 закрыты статусом: закрытый пункт не исчезает и
 * не гаснет надписью «недоступно», а ведёт на экран-гейт с кнопкой в профиль
 * (ТЗ 1.3, инвариант 4 в CLAUDE.md).
 *
 * Какие разделы открыты, решает сервер и отдаёт в поле `access` профиля
 * (решение Р19): меню его читает, но не выводит само.
 *
 * Над списком разделов — календарь-решётка (`MenuCalendar`): по хендоффу это
 * главный элемент экрана, а не украшение (уточнение У10).
 */
import { Link } from 'react-router-dom';

import { STATUS_LABELS, useProfile, type Profile } from '@/shared/api/profile';
import { ChevronRightIcon, UserIcon } from '@/shared/ui/icons';

import { MenuCalendar } from './MenuCalendar';

interface MenuItem {
  readonly number: string;
  readonly title: string;
  readonly to: string;
  /**
   * Ключ доступа в поле `access` профиля. Пусто — раздел открыт всем.
   * Значение — имя раздела для экрана-гейта.
   */
  readonly gate?: 'schedule' | 'food';
}

const MENU: readonly MenuItem[] = [
  { number: '01', title: 'Профориентационный тест', to: '/career-test' },
  { number: '02', title: 'Подбор вуза по баллам ЕГЭ', to: '/vuz-selection' },
  { number: '03', title: 'Трекер конкурсных списков', to: '/tracker' },
  { number: '04', title: 'Расписание и дедлайны', to: '/schedule', gate: 'schedule' },
  { number: '05', title: 'Спроси у старшекурсника', to: '/mentor-qa' },
  { number: '06', title: 'Рейтинг активности', to: '/leaderboard' },
  { number: '07', title: 'Где покушать?', to: '/food', gate: 'food' },
  { number: '08', title: 'Поддержка / Предложить улучшение', to: '/support' },
];

export function MenuScreen() {
  const profile = useProfile();

  return (
    <>
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-[10px]">
          <span className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-text font-heading text-[15px] text-neutral-200">
            Н
          </span>
          <span className="text-[12px] font-bold tracking-[0.2em]">НАВИГАТОР</span>
        </div>
        {profile.data !== undefined && <StatusPill profile={profile.data} />}
      </div>

      <MenuCalendar />

      <div className="mt-[26px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        РАЗДЕЛЫ
      </div>

      <div className="mt-3 flex flex-col gap-[10px]">
        {MENU.map((item) => (
          <MenuLink key={item.number} item={item} access={profile.data?.access} />
        ))}
      </div>

      <Link
        to="/profile"
        className="mt-[14px] flex items-center gap-[14px] rounded-[26px] bg-accent px-[18px] py-4 text-[15px] transition-colors hover:bg-accent-400 active:bg-accent-700"
      >
        <UserIcon />
        <span className="flex-1">Мой профиль</span>
        <ChevronRightIcon />
      </Link>
    </>
  );
}

function MenuLink({
  item,
  access,
}: {
  readonly item: MenuItem;
  readonly access: Profile['access'] | undefined;
}) {
  // Пока профиль не пришёл, пункт ведёт по своему адресу: экран раздела сам
  // уводит на гейт, если сервер откажет. Так меню не мигает на загрузке.
  const closed = item.gate !== undefined && access !== undefined && !access[item.gate];
  const to = closed ? `/gate/${item.gate ?? ''}` : item.to;

  return (
    <Link
      to={to}
      className="flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-4 transition-colors hover:bg-text/6"
    >
      <span className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full border-[1.5px] border-neutral-400 font-heading text-[13px]">
        {item.number}
      </span>
      <span className="flex-1 text-[15px]">{item.title}</span>
      {closed && (
        <span className="flex-none rounded-full border-[1.5px] border-neutral-400 px-[10px] py-[5px] text-[9px] font-bold tracking-[0.14em] text-neutral-600">
          ДЛЯ СТУДЕНТОВ
        </span>
      )}
      <ChevronRightIcon />
    </Link>
  );
}

function StatusPill({ profile }: { readonly profile: Profile }) {
  return (
    <Link
      to="/profile"
      className="flex-none rounded-full border-[1.5px] border-neutral-400 px-[14px] py-2 text-[10px] font-bold tracking-[0.16em] transition-colors hover:bg-text/6"
    >
      {STATUS_LABELS[profile.status].toUpperCase()}
    </Link>
  );
}
