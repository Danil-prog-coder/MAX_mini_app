/**
 * Расписание и дедлайны (ТЗ 4.1–4.6).
 *
 * Раздел закрыт статусом: сервер отвечает 403, пока в профиле нет статуса
 * «Студент» и вуза, и экран уводит на гейт — маршрут, а не отказ (ТЗ 4.2,
 * инвариант 4 в CLAUDE.md).
 */
import { useState } from 'react';
import { Link, Navigate } from 'react-router-dom';

import {
  CLOSED,
  useAddDeadline,
  useToday,
  type Deadline,
  type Lesson,
  type Today,
} from '@/shared/api/schedule';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { PlusIcon } from '@/shared/ui/icons';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';
import { Sheet } from '@/shared/ui/Sheet';

/** Сроки чипами в шторке добавления дедлайна (макет, экран 11). */
const DAY_CHIPS = [1, 3, 7, 14, 30] as const;

export function ScheduleScreen() {
  const today = useToday();
  const [adding, setAdding] = useState(false);

  const data = today.data;
  if (data === CLOSED) {
    return <Navigate to="/gate/schedule" replace />;
  }

  const summary: Today | undefined = data;

  return (
    <>
      <ScheduleHeader groupName={summary?.group_name ?? null} />

      {today.isPending && <Hint>Загружаю расписание…</Hint>}
      {today.isError && <Hint>Не удалось загрузить расписание. Проверьте связь.</Hint>}

      {summary !== undefined && (
        <>
          <div className="mt-6 flex items-baseline gap-[14px]">
            <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">
              {summary.lessons.length}
            </span>
            <span className="text-[11px] leading-[1.3] font-bold tracking-[0.18em] text-neutral-600">
              {pluralLessons(summary.lessons.length)}
              <br />
              СЕГОДНЯ
            </span>
          </div>

          {summary.group_name === null ? (
            <>
              <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">
                Группа не выбрана — расписания пока нет. Выберите её в профиле, и день соберётся
                сам.
              </p>
              <Link
                to="/profile"
                className={buttonClass('accent', 'mt-4 w-full px-[10px] py-[17px] text-[14px]')}
              >
                Выбрать группу
              </Link>
            </>
          ) : (
            <LessonList lessons={summary.lessons} />
          )}

          <div className="mt-[26px] flex items-center justify-between gap-3">
            <span className="text-[11px] font-bold tracking-[0.2em] text-neutral-600">
              ДЕДЛАЙНЫ
            </span>
            <button
              type="button"
              aria-label="Добавить дедлайн"
              onClick={() => {
                setAdding(true);
              }}
              className="flex h-10 w-10 items-center justify-center rounded-full bg-accent transition-colors hover:bg-accent-400"
            >
              <PlusIcon />
            </button>
          </div>

          <DeadlineList deadlines={summary.deadlines} today={summary.day} />
        </>
      )}

      <AddDeadlineSheet
        open={adding}
        onClose={() => {
          setAdding(false);
        }}
      />
    </>
  );
}

function ScheduleHeader({ groupName }: { readonly groupName: string | null }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <ScreenHeader title="Расписание" />
      <span className="flex-none rounded-full border-[1.5px] border-neutral-400 px-[14px] py-2 text-[10px] font-bold tracking-[0.16em]">
        {groupName ?? 'ГРУППА НЕ УКАЗАНА'}
      </span>
    </div>
  );
}

function LessonList({ lessons }: { readonly lessons: readonly Lesson[] }) {
  if (lessons.length === 0) {
    return (
      <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">
        Сегодня пар нет — выходной или окно в расписании группы.
      </p>
    );
  }

  return (
    <div className="mt-5 flex flex-col gap-[9px]">
      {lessons.map((lesson) => (
        <div
          key={`${lesson.starts_at}-${lesson.title}`}
          className={`flex items-center gap-[14px] rounded-[26px] px-[18px] py-[15px] ${
            lesson.is_now ? 'bg-text text-neutral-200' : 'border-[1.5px] border-neutral-400'
          }`}
        >
          <span className="font-heading text-[17px] tracking-[-0.02em]">
            {shortTime(lesson.starts_at)}
          </span>
          <div className="min-w-0 flex-1">
            <div className="text-[14px]">{lesson.title}</div>
            <div
              className={`text-[11px] ${lesson.is_now ? 'text-neutral-500' : 'text-neutral-600'}`}
            >
              ауд. {lesson.room} · {lesson.kind}
            </div>
          </div>
          {lesson.is_now && (
            <span className="flex-none rounded-full bg-accent px-[11px] py-[6px] text-[10px] font-bold tracking-[0.12em] text-text">
              СЕЙЧАС
            </span>
          )}
        </div>
      ))}
    </div>
  );
}

function DeadlineList({
  deadlines,
  today,
}: {
  readonly deadlines: readonly Deadline[];
  readonly today: string;
}) {
  if (deadlines.length === 0) {
    return (
      <p className="mt-3 text-[13px] leading-[1.45] text-neutral-600">
        Личных дедлайнов нет. Кнопка «+» добавит первый — напомню за сутки.
      </p>
    );
  }

  return (
    <div className="mt-3 flex flex-col gap-[10px]">
      {deadlines.map((deadline) => {
        const left = daysBetween(today, deadline.due_date);
        return (
          <div
            key={deadline.id}
            className="animate-card-in flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-4"
          >
            <span className="font-heading text-[28px] tracking-[-0.03em]">{left}</span>
            <div className="min-w-0 flex-1">
              <div className="text-[15px]">{deadline.title}</div>
              <div className="mt-[2px] text-[12px] text-neutral-600">
                {left === 0 ? 'сегодня' : `через ${String(left)} ${pluralDays(left)}`} · напомню за
                сутки
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function AddDeadlineSheet({
  open,
  onClose,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
}) {
  const add = useAddDeadline();
  const [title, setTitle] = useState('');
  const [days, setDays] = useState<number>(3);

  const valid = title.trim() !== '';

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title="Новый дедлайн"
    >
      <input
        value={title}
        aria-label="Название дедлайна"
        placeholder="Название"
        onChange={(event) => {
          setTitle(event.target.value);
        }}
        className={`flex-none rounded-full border-[1.5px] bg-transparent px-[22px] py-[18px] text-[16px] ${
          add.isError ? 'border-accent' : 'border-neutral-400'
        }`}
      />

      <div className="flex-none text-[10px] font-bold tracking-[0.18em] text-neutral-600">
        КОГДА
      </div>
      <div className="flex flex-none flex-wrap gap-2">
        {DAY_CHIPS.map((chip) => (
          <Button
            key={chip}
            variant={chip === days ? 'dark' : 'outline'}
            onClick={() => {
              setDays(chip);
            }}
            className="px-[18px] py-3 text-[14px]"
          >
            через {chip} {pluralDays(chip)}
          </Button>
        ))}
      </div>

      <Button
        variant="dark"
        disabled={!valid || add.isPending}
        onClick={() => {
          add.mutate(
            { title: title.trim(), dueDate: inDays(days) },
            {
              onSuccess: () => {
                setTitle('');
                setDays(3);
                onClose();
              },
            },
          );
        }}
        className="flex-none px-[10px] py-[17px] text-[14px] disabled:opacity-60"
      >
        Добавить
      </Button>

      {add.isError && <SheetHint>Не удалось добавить дедлайн. Попробуйте ещё раз.</SheetHint>}
    </Sheet>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

function SheetHint({ children }: { readonly children: React.ReactNode }) {
  return <p className="flex-none text-[13px] leading-[1.45] text-neutral-700">{children}</p>;
}

/** «09:00:00» с сервера показывается как «09:00»: секунды в макете не нужны. */
function shortTime(value: string): string {
  return value.slice(0, 5);
}

/** Дата через N дней в формате, который принимает API. */
function inDays(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() + days);
  return date.toISOString().slice(0, 10);
}

function daysBetween(from: string, to: string): number {
  const MS_IN_DAY = 24 * 60 * 60 * 1000;
  const start = Date.parse(`${from}T00:00:00Z`);
  const end = Date.parse(`${to}T00:00:00Z`);
  if (Number.isNaN(start) || Number.isNaN(end)) return 0;
  return Math.max(0, Math.round((end - start) / MS_IN_DAY));
}

function pluralDays(count: number): string {
  const tail = count % 100;
  if (tail >= 11 && tail <= 14) return 'дней';
  const last = count % 10;
  if (last === 1) return 'день';
  if (last >= 2 && last <= 4) return 'дня';
  return 'дней';
}

function pluralLessons(count: number): string {
  const tail = count % 100;
  if (tail >= 11 && tail <= 14) return 'ПАР';
  const last = count % 10;
  if (last === 1) return 'ПАРА';
  if (last >= 2 && last <= 4) return 'ПАРЫ';
  return 'ПАР';
}
