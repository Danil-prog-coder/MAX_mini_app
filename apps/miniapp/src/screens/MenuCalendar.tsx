/**
 * Календарь-решётка на главном экране.
 *
 * Главный элемент экрана по хендоффу («заменяет привычную сводку»), и часть
 * продукта по уточнению У10, а не украшение прототипа. Поэтому он живёт на
 * главной, а не внутри блока 4.
 *
 * Разметка и размеры перенесены из макета (`docs/design/source/app.css`, блок
 * `data-cal`): крупное число дня, день недели, месяц с годом, две круглые
 * стрелки, шапка дней недели, сетка точек 34px с шагом 11px.
 *
 * Состояние дня и месяца — локальное: это позиция в календаре, а не данные
 * пользователя (инвариант 3, Zustand копий серверных данных не держит).
 */
import { useState } from 'react';

import { useProfile } from '@/shared/api/profile';
import { Sheet } from '@/shared/ui/Sheet';
import { ChevronLeftIcon, ChevronRightIcon } from '@/shared/ui/icons';

import {
  CURRENT_MONTH_INDEX,
  MONTHS,
  TODAY,
  monthAt,
  WEEKDAYS,
  emptyDayNote,
  eventsOf,
  weekdayOf,
  type CalendarEvent,
} from './menuCalendarContent';

export function MenuCalendar() {
  const profile = useProfile();
  const isStudent = profile.data?.status === 'student';

  const [monthIndex, setMonthIndex] = useState(CURRENT_MONTH_INDEX);
  // `null` — день не выбирали: шапка показывает сегодняшнее число текущего
  // месяца, а в остальных месяцах первое (макет, `paintCal`).
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(null);

  const month = monthAt(monthIndex);
  const headDay = selectedDay ?? (monthIndex === CURRENT_MONTH_INDEX ? TODAY : 1);

  function shiftMonth(step: number): void {
    const next = monthIndex + step;
    if (next < 0 || next > MONTHS.length - 1) return;
    setMonthIndex(next);
    setSelectedDay(null);
  }

  return (
    <div className="mt-[18px]">
      <div className="flex items-start justify-between gap-3">
        <span className="font-heading text-[128px] leading-[0.86] tracking-[-0.055em]">
          {headDay}
        </span>
        <span className="mt-4 font-heading text-[26px] tracking-[-0.02em]">
          {weekdayOf(month, headDay)}
        </span>
      </div>

      <div className="mt-[10px] flex items-end justify-between gap-3">
        <div>
          <div className="text-[13px] font-bold tracking-[0.2em]">{month.name}</div>
          <div className="text-[13px] tracking-[0.2em] text-neutral-500">{month.year}</div>
        </div>
        <div className="flex gap-2">
          <MonthArrow
            label="Предыдущий месяц"
            disabled={monthIndex === 0}
            onClick={() => shiftMonth(-1)}
          >
            <ChevronLeftIcon />
          </MonthArrow>
          <MonthArrow
            label="Следующий месяц"
            disabled={monthIndex === MONTHS.length - 1}
            onClick={() => shiftMonth(1)}
          >
            <ChevronRightIcon size={18} />
          </MonthArrow>
        </div>
      </div>

      <div className="mt-5 grid grid-cols-7 justify-items-center text-[10px] font-semibold tracking-[0.06em] text-neutral-500">
        {WEEKDAYS.map((weekday) => (
          <span key={weekday}>{weekday.toUpperCase()}</span>
        ))}
      </div>

      <div className="mt-3 grid grid-cols-7 justify-items-center gap-[11px]">
        {/* Пустые ячейки до первого числа: сетка начинается с понедельника. */}
        {Array.from({ length: month.first - 1 }, (_, index) => (
          <span key={`gap-${String(index)}`} />
        ))}
        {Array.from({ length: month.days }, (_, index) => {
          const day = index + 1;
          return (
            <DayDot
              key={day}
              day={day}
              monthIndex={monthIndex}
              hasEvents={eventsOf(isStudent, monthIndex, day).length > 0}
              onOpen={() => {
                setSelectedDay(day);
                setOpenDay(day);
              }}
            />
          );
        })}
      </div>

      <p className="mt-4 text-[12px] text-pretty text-neutral-600">
        Нажмите на день — покажу, что в нём
      </p>

      <Sheet
        open={openDay !== null}
        onOpenChange={(open) => {
          if (!open) setOpenDay(null);
        }}
        title={
          openDay === null
            ? ''
            : `${String(openDay)} ${month.genitive} · ${weekdayOf(month, openDay).toUpperCase()}`
        }
      >
        {openDay !== null && (
          <DayEvents events={eventsOf(isStudent, monthIndex, openDay)} isStudent={isStudent} />
        )}
      </Sheet>
    </div>
  );
}

function MonthArrow({
  label,
  disabled,
  onClick,
  children,
}: {
  readonly label: string;
  readonly disabled: boolean;
  readonly onClick: () => void;
  readonly children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="flex h-[38px] w-[38px] items-center justify-center rounded-full border-[1.5px] border-neutral-400 transition-colors hover:bg-text/6 disabled:opacity-40 disabled:hover:bg-transparent"
    >
      {children}
    </button>
  );
}

/**
 * Точка дня. Четыре состояния из макета: сегодня — акцентная заливка, день с
 * событиями — тёмная, прошедший — серая, будущий пустой — только обводка.
 */
function DayDot({
  day,
  monthIndex,
  hasEvents,
  onOpen,
}: {
  readonly day: number;
  readonly monthIndex: number;
  readonly hasEvents: boolean;
  readonly onOpen: () => void;
}) {
  const isToday = monthIndex === CURRENT_MONTH_INDEX && day === TODAY;
  const isPast =
    monthIndex < CURRENT_MONTH_INDEX || (monthIndex === CURRENT_MONTH_INDEX && day < TODAY);

  const fill = isToday
    ? 'bg-accent'
    : hasEvents
      ? 'bg-text'
      : isPast
        ? 'bg-neutral-300'
        : 'border-[1.5px] border-neutral-400';

  return (
    <button
      type="button"
      onClick={onOpen}
      // Дата в подписи, а не только число: иначе кнопка называется «13» и
      // без соседних дней ничего не значит.
      aria-label={`${String(day)} ${monthAt(monthIndex).genitive.toLowerCase()}${
        hasEvents ? ', есть события' : ''
      }`}
      // Stagger 12ms на день: точки появляются волной, как в макете.
      style={{ animationDelay: `${String(day * 12)}ms` }}
      className={`animate-dot-in h-[34px] w-[34px] rounded-full transition-transform duration-200 ease-pop hover:scale-[1.16] ${fill}`}
    />
  );
}

function DayEvents({
  events,
  isStudent,
}: {
  readonly events: readonly CalendarEvent[];
  readonly isStudent: boolean;
}) {
  if (events.length === 0) {
    return (
      <div className="flex-none rounded-[30px] border-[1.5px] border-neutral-400 px-6 py-[22px]">
        <div className="font-heading text-[30px] tracking-[-0.03em]">Ничего не запланировано</div>
        <div className="mt-2 text-[14px] text-pretty text-neutral-700">
          {emptyDayNote(isStudent)}
        </div>
      </div>
    );
  }

  return (
    <>
      {events.map((event, index) => {
        // Первое событие дня выделено заливкой — оно главное (макет, `openDay`).
        const dark = index === 0;
        return (
          <div
            key={event.title}
            className={`flex-none rounded-[30px] px-[22px] py-5 ${
              dark ? 'bg-text text-neutral-200' : 'border-[1.5px] border-neutral-400'
            }`}
          >
            <div className="font-heading text-[22px] leading-[1.15] tracking-[-0.025em]">
              {event.title}
            </div>
            <div
              className={`mt-1.5 text-[13px] leading-[1.45] text-pretty ${
                dark ? 'text-neutral-400' : 'text-neutral-700'
              }`}
            >
              {event.note}
            </div>
          </div>
        );
      })}
    </>
  );
}
