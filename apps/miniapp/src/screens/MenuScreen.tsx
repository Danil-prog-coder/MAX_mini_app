/**
 * Главное меню — точка входа и точка возврата (ТЗ 1.2).
 *
 * Пока это оболочка: список разделов и переход в профиль работают, а
 * календарь-решётка (уточнение У10), пилюля статуса и блокировка разделов 4 и
 * 7 появятся, когда экран получит профиль с сервера. Разделы перечислены
 * ровно так, как в макете (`docs/design/source/app.jsx`, массив `MENU`).
 */
import { Link } from 'react-router-dom';

import { ChevronRightIcon, UserIcon } from '@/shared/ui/icons';

interface MenuItem {
  readonly number: string;
  readonly title: string;
  readonly to: string;
}

const MENU: readonly MenuItem[] = [
  { number: '01', title: 'Профориентационный тест', to: '/career-test' },
  { number: '02', title: 'Подбор вуза по баллам ЕГЭ', to: '/vuz-selection' },
  { number: '03', title: 'Трекер конкурсных списков', to: '/tracker' },
  { number: '04', title: 'Расписание и дедлайны', to: '/schedule' },
  { number: '05', title: 'Спроси у старшекурсника', to: '/mentor-qa' },
  { number: '06', title: 'Рейтинг активности', to: '/leaderboard' },
  { number: '07', title: 'Где покушать?', to: '/food' },
  { number: '08', title: 'Поддержка / Предложить улучшение', to: '/support' },
];

export function MenuScreen() {
  return (
    <>
      <div className="flex items-center gap-[10px]">
        <span className="flex h-[34px] w-[34px] items-center justify-center rounded-full bg-text font-heading text-[15px] text-neutral-200">
          Н
        </span>
        <span className="text-[12px] font-bold tracking-[0.2em]">НАВИГАТОР</span>
      </div>

      <div className="mt-[26px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        РАЗДЕЛЫ
      </div>

      <div className="mt-3 flex flex-col gap-[10px]">
        {MENU.map((item) => (
          <Link
            key={item.number}
            to={item.to}
            className="flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-4 transition-colors hover:bg-text/6"
          >
            <span className="flex h-[30px] w-[30px] flex-none items-center justify-center rounded-full border-[1.5px] border-neutral-400 font-heading text-[13px]">
              {item.number}
            </span>
            <span className="flex-1 text-[15px]">{item.title}</span>
            <ChevronRightIcon />
          </Link>
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
