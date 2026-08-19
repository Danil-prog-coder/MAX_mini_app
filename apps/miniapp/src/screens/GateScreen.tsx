/**
 * Раздел требует статуса «Студент» (ТЗ 1.3, 4.2, 7.2).
 *
 * Это маршрут, а не отказ (инвариант 4 в CLAUDE.md): экран объясняет, чего не
 * хватает, и ведёт в профиль — там оба недостающих поля и заполняются.
 *
 * Тексты для расписания и еды разные и перенесены из макета дословно.
 */
import { Link, useParams } from 'react-router-dom';

import { buttonClass } from '@/shared/ui/buttonStyles';
import { ChevronRightIcon } from '@/shared/ui/icons';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

interface GateCopy {
  readonly kicker: string;
  readonly text: string;
}

const GATES: Record<string, GateCopy> = {
  schedule: {
    kicker: 'Расписание и дедлайны',
    text: 'Этот раздел собирает расписание вашей группы. Укажите в профиле статус «Студент» и вуз — и он откроется.',
  },
  food: {
    kicker: 'Где покушать',
    text: 'Точки питания подбираются рядом с вашим вузом. Укажите в профиле статус «Студент» и вуз — и раздел откроется.',
  },
};

const FALLBACK: GateCopy = {
  kicker: 'Нужен статус студента',
  text: 'Этот раздел открывается студентам. Укажите в профиле статус «Студент» и вуз — и он станет доступен.',
};

export function GateScreen() {
  const { section } = useParams();
  // Незнакомый раздел — не повод показывать пустой экран: общий текст ведёт
  // туда же, куда и любой другой (ТЗ 1.1).
  const copy = (section !== undefined ? GATES[section] : undefined) ?? FALLBACK;

  return (
    <>
      <ScreenHeader title={copy.kicker} />

      <h1 className="mt-10 font-heading text-[116px] leading-[0.88] tracking-[-0.055em]">Почти</h1>

      <p className="mt-[18px] max-w-[300px] text-[16px] leading-[1.45] text-neutral-700">
        {copy.text}
      </p>

      <Link to="/profile" className={buttonClass('accent', 'mt-[26px] px-6 py-[17px] text-[15px]')}>
        Перейти в профиль
        <ChevronRightIcon size={18} />
      </Link>
    </>
  );
}
