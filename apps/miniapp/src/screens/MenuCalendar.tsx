/**
 * Календарь-решётка на главном экране.
 *
 * Главный элемент экрана по хендоффу («заменяет привычную сводку») и часть
 * продукта по уточнению У10. Разметка и размеры перенесены из макета
 * (`docs/design/source/app.css`, блок `data-cal`): крупное число дня, день
 * недели, месяц с годом, две круглые стрелки, шапка дней недели, сетка точек
 * 34px с шагом 11px.
 *
 * События приходят с сервера (уточнение У32): личные, дедлайны приёмной
 * кампании отслеживаемых вузов и пары по расписанию. Своё событие заводится
 * прямо здесь — оранжевым плюсом в шторке дня, — и это тот же личный дедлайн,
 * что и в разделе «Расписание и дедлайны»: хранилище одно, поэтому заведённое
 * там появляется здесь, и наоборот.
 *
 * Цвет точки (уточнение У32): оранжевая — сегодня, тёмная — есть планы или
 * дедлайны, белая — день свободен.
 */
import { useState } from 'react';

import {
  useAddCalendarEvent,
  useCalendarMonth,
  useDeleteCalendarEvent,
  type CalendarEvent,
} from '@/shared/api/calendar';
import { Button } from '@/shared/ui/Button';
import { PlusIcon } from '@/shared/ui/icons';
import { ChevronLeftIcon, ChevronRightIcon } from '@/shared/ui/icons';
import { Sheet } from '@/shared/ui/Sheet';

import {
  daysInMonth,
  firstWeekdayOf,
  isoDate,
  isoOf,
  monthGenitive,
  monthName,
  monthOf,
  monthRange,
  sameMonth,
  shiftMonth,
  weekdayOf,
  WEEKDAYS,
} from './menuCalendarContent';

export function MenuCalendar() {
  // «Сегодня» берётся один раз на монтирование: пересчёт на каждый рендер
  // означал бы, что дата меняется под руками у человека, открывшего экран
  // до полуночи.
  const [today] = useState(() => new Date());
  const todayIso = isoOf(today);

  const [month, setMonth] = useState(() => monthOf(today));
  const [selectedDay, setSelectedDay] = useState<number | null>(null);
  const [openDay, setOpenDay] = useState<number | null>(null);

  const range = monthRange(month);
  const events = useCalendarMonth(range.from, range.to);

  const byDay = new Map<string, CalendarEvent[]>();
  for (const event of events.data ?? []) {
    const list = byDay.get(event.day) ?? [];
    list.push(event);
    byDay.set(event.day, list);
  }

  const isCurrentMonth = sameMonth(month, monthOf(today));
  const headDay = selectedDay ?? (isCurrentMonth ? today.getDate() : 1);
  const total = daysInMonth(month);

  function goToMonth(step: number): void {
    setMonth((current) => shiftMonth(current, step));
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
          <div className="text-[13px] font-bold tracking-[0.2em]">{monthName(month)}</div>
          <div className="text-[13px] tracking-[0.2em] text-neutral-500">{month.year}</div>
        </div>
        <div className="flex gap-2">
          <MonthArrow
            label="Предыдущий месяц"
            onClick={() => {
              goToMonth(-1);
            }}
          >
            <ChevronLeftIcon />
          </MonthArrow>
          <MonthArrow
            label="Следующий месяц"
            onClick={() => {
              goToMonth(1);
            }}
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
        {Array.from({ length: firstWeekdayOf(month) - 1 }, (_, index) => (
          <span key={`gap-${String(index)}`} />
        ))}
        {Array.from({ length: total }, (_, index) => {
          const day = index + 1;
          const iso = isoDate(month.year, month.month, day);
          return (
            <DayDot
              key={day}
              day={day}
              genitive={monthGenitive(month)}
              isToday={iso === todayIso}
              count={byDay.get(iso)?.length ?? 0}
              onOpen={() => {
                setSelectedDay(day);
                setOpenDay(day);
              }}
            />
          );
        })}
      </div>

      <p className="mt-4 text-[12px] text-pretty text-neutral-600">
        {events.isError
          ? 'Не удалось загрузить события. Календарь работает, события появятся при следующей попытке.'
          : 'Нажмите на день — покажу, что в нём, и дам добавить своё'}
      </p>

      <DaySheet
        day={openDay}
        month={month}
        events={
          openDay === null ? [] : (byDay.get(isoDate(month.year, month.month, openDay)) ?? [])
        }
        onClose={() => {
          setOpenDay(null);
        }}
      />
    </div>
  );
}

function MonthArrow({
  label,
  onClick,
  children,
}: {
  readonly label: string;
  readonly onClick: () => void;
  readonly children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-label={label}
      onClick={onClick}
      className="flex h-[38px] w-[38px] items-center justify-center rounded-full border-[1.5px] border-neutral-400 transition-colors hover:bg-text/6"
    >
      {children}
    </button>
  );
}

/**
 * Точка дня. Три состояния по уточнению У32: сегодня — оранжевая, есть
 * события — тёмная, свободный день — белая с обводкой.
 */
function DayDot({
  day,
  genitive,
  isToday,
  count,
  onOpen,
}: {
  readonly day: number;
  readonly genitive: string;
  readonly isToday: boolean;
  readonly count: number;
  readonly onOpen: () => void;
}) {
  const fill = isToday ? 'bg-accent' : count > 0 ? 'bg-text' : 'border-[1.5px] border-neutral-400';

  return (
    <button
      type="button"
      onClick={onOpen}
      // Дата в подписи, а не только число: иначе кнопка называется «13» и без
      // соседних дней ничего не значит.
      aria-label={`${String(day)} ${genitive.toLowerCase()}${count > 0 ? ', есть события' : ''}`}
      // Stagger 12ms на день: точки появляются волной, как в макете.
      style={{ animationDelay: `${String(day * 12)}ms` }}
      className={`animate-dot-in ease-pop h-[34px] w-[34px] rounded-full transition-transform duration-200 hover:scale-[1.16] ${fill}`}
    />
  );
}

/** Шторка дня: что в нём и кнопка добавить своё. */
function DaySheet({
  day,
  month,
  events,
  onClose,
}: {
  readonly day: number | null;
  readonly month: { readonly year: number; readonly month: number };
  readonly events: readonly CalendarEvent[];
  readonly onClose: () => void;
}) {
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState('');
  const addEvent = useAddCalendarEvent();
  const deleteEvent = useDeleteCalendarEvent();

  // Форма живёт только пока открыт день: перешли на другой — снова список.
  const [openedDay, setOpenedDay] = useState(day);
  if (openedDay !== day) {
    setOpenedDay(day);
    setAdding(false);
    setTitle('');
    addEvent.reset();
  }

  if (day === null) {
    return (
      <Sheet open={false} onOpenChange={onClose} title="">
        <span />
      </Sheet>
    );
  }

  const iso = isoDate(month.year, month.month, day);

  return (
    <Sheet
      open
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title={`${String(day)} ${monthGenitive(month)} · ${weekdayOf(month, day).toUpperCase()}`}
    >
      {events.length === 0 && !adding && (
        <div className="flex-none rounded-[30px] border-[1.5px] border-neutral-400 px-6 py-[22px]">
          <div className="font-heading text-[30px] tracking-[-0.03em]">Ничего не запланировано</div>
          <div className="mt-2 text-[14px] text-pretty text-neutral-700">
            Ни пар, ни дедлайнов. Добавьте своё событие — напомню за сутки.
          </div>
        </div>
      )}

      {events.map((event, index) => (
        <DayEventCard
          key={`${event.kind}-${String(event.event_id ?? index)}-${event.title}`}
          event={event}
          dark={index === 0}
          onDelete={
            event.event_id === null
              ? undefined
              : () => {
                  deleteEvent.mutate(event.event_id ?? 0);
                }
          }
        />
      ))}

      {adding ? (
        <form
          className="flex-none"
          onSubmit={(submit) => {
            submit.preventDefault();
            const cleaned = title.trim();
            if (cleaned === '') return;
            addEvent.mutate(
              { title: cleaned, day: iso },
              {
                onSuccess: () => {
                  setTitle('');
                  setAdding(false);
                },
              },
            );
          }}
        >
          <input
            value={title}
            onChange={(change) => {
              setTitle(change.target.value);
            }}
            placeholder="Что за событие?"
            aria-label="Название события"
            maxLength={256}
            autoFocus
            className="w-full rounded-full border-[1.5px] border-neutral-400 bg-transparent px-5 py-[13px] text-[15px] outline-none focus:border-text"
          />
          <div className="mt-2 flex gap-2">
            <Button
              type="submit"
              variant="accent"
              disabled={title.trim() === '' || addEvent.isPending}
              className="flex-1 px-4 py-[13px] text-[14px] disabled:opacity-60"
            >
              {addEvent.isPending ? 'Сохраняю…' : 'Добавить'}
            </Button>
            <Button
              type="button"
              variant="outline"
              className="flex-none px-4 py-[13px] text-[14px]"
              onClick={() => {
                setAdding(false);
                setTitle('');
              }}
            >
              Отмена
            </Button>
          </div>
          {addEvent.isError && (
            <p className="mt-2 text-[12px] text-neutral-700">
              Не удалось сохранить. Дата не должна быть в прошлом и дальше чем через год.
            </p>
          )}
        </form>
      ) : (
        <button
          type="button"
          onClick={() => {
            setAdding(true);
          }}
          aria-label="Добавить событие"
          className="flex flex-none items-center gap-3 rounded-[26px] bg-accent px-[18px] py-4 text-[15px] transition-colors hover:bg-accent-400 active:bg-accent-700"
        >
          <PlusIcon />
          <span>Добавить событие</span>
        </button>
      )}
    </Sheet>
  );
}

function DayEventCard({
  event,
  dark,
  onDelete,
}: {
  readonly event: CalendarEvent;
  readonly dark: boolean;
  /** Есть только у своих событий: пару из расписания удалять нечем. */
  readonly onDelete: (() => void) | undefined;
}) {
  return (
    <div
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
      {onDelete !== undefined && (
        <button
          type="button"
          onClick={onDelete}
          className={`mt-3 rounded-full px-4 py-2 text-[12px] transition-colors ${
            dark
              ? 'border-[1.5px] border-neutral-200/30 hover:bg-neutral-200/12'
              : 'border-[1.5px] border-neutral-400 hover:bg-text/6'
          }`}
        >
          Удалить
        </button>
      )}
    </div>
  );
}
