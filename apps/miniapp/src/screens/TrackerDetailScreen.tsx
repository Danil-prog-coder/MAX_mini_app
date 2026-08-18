/**
 * Позиция в конкурсном списке (ТЗ 3.5–3.7).
 *
 * Два состояния одного экрана (макет, экран 9): места ещё нет — форма ввода;
 * место известно — крупное число, сравнение с прошлой проверкой, динамика за
 * неделю и напоминание о датах приёма.
 *
 * Место вводится вручную и хранится на сервере: ТЗ 3.5 требует, чтобы первое
 * значение назвал сам человек, а ТЗ 0.2 — чтобы оно не расходилось между
 * телефоном и десктопом.
 */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  usePositions,
  useSavePosition,
  type Positions,
  type WeekPoint,
} from '@/shared/api/tracker';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ArrowUpIcon, BellIcon } from '@/shared/ui/icons';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

export function TrackerDetailScreen() {
  const { universityId } = useParams();
  const parsed = Number(universityId);
  const id = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  const positions = usePositions(id);
  // «Обновить позицию вручную» возвращает экран в состояние ввода, не стирая
  // сохранённое: пока новое место не введено, старое остаётся верным.
  const [asking, setAsking] = useState(false);

  const data = positions.data ?? null;

  return (
    <>
      <ScreenHeader title={data?.university.short_name ?? 'Позиция в списке'} />

      {positions.isPending && <Hint>Загружаю позицию…</Hint>}
      {positions.isError && <Hint>Не удалось загрузить позицию. Проверьте связь.</Hint>}

      {(id === null || (positions.isSuccess && data === null)) && (
        <>
          <Hint>Этот вуз не в отслеживаемых — возможно, ссылка устарела.</Hint>
          <Link
            to="/tracker"
            className={buttonClass('accent', 'mt-4 w-full px-[10px] py-[17px] text-[14px]')}
          >
            К трекеру
          </Link>
        </>
      )}

      {data !== null &&
        (data.position === null || asking ? (
          <AskPosition
            universityId={id}
            positions={data}
            onSaved={() => {
              setAsking(false);
            }}
          />
        ) : (
          <KnownPosition
            positions={data}
            onAsk={() => {
              setAsking(true);
            }}
          />
        ))}
    </>
  );
}

function KnownPosition({
  positions,
  onAsk,
}: {
  readonly positions: Positions;
  readonly onAsk: () => void;
}) {
  const improvement = positions.improvement;

  return (
    <>
      <div className="mt-6 text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        ВАША ПОЗИЦИЯ СЕГОДНЯ
      </div>
      <div className="mt-[2px] flex flex-wrap items-baseline gap-4">
        <span className="font-heading text-[132px] leading-[0.88] tracking-[-0.055em]">
          {positions.position}
        </span>
        {improvement !== null && improvement > 0 && (
          <span className="flex items-center gap-[7px] rounded-full bg-accent px-[15px] py-[9px] text-[12px] font-bold tracking-[0.06em]">
            <ArrowUpIcon />
            на {improvement}
          </span>
        )}
      </div>

      <p className="mt-3 text-[15px] text-neutral-700">{comparison(positions)}</p>

      <WeekChart week={positions.week} />

      <div className="mt-3 flex flex-col gap-[10px]">
        <div className="flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-4">
          <span className="flex h-[34px] w-[34px] flex-none items-center justify-center rounded-full border-[1.5px] border-accent text-accent">
            <BellIcon />
          </span>
          {/* ТЗ 3.7: за 7 дней до старта приёма и за 1 день до окончания. */}
          <span className="flex-1 text-[13px] leading-[1.4]">
            Напомню за 7 дней до старта приёма и за 1 день до конца
          </span>
        </div>
        <Button
          variant="outline"
          onClick={onAsk}
          className="w-full px-[10px] py-[17px] text-[14px]"
        >
          Обновить позицию вручную
        </Button>
      </div>
    </>
  );
}

function WeekChart({ week }: { readonly week: readonly WeekPoint[] }) {
  const known = week.flatMap((point) => (point.position === null ? [] : [point.position]));
  // Место тем лучше, чем оно меньше, поэтому столбик рисуется «наоборот»:
  // самое высокое место — самый высокий столбик.
  const best = known.length > 0 ? Math.min(...known) : 0;
  const worst = known.length > 0 ? Math.max(...known) : 0;
  const lastKnown = [...week].reverse().find((point) => point.position !== null);

  return (
    <div className="mt-5 rounded-[34px] bg-text px-6 py-[22px] text-neutral-200">
      <div className="text-[10px] font-bold tracking-[0.18em] text-accent-300">
        ДИНАМИКА ЗА НЕДЕЛЮ
      </div>
      <div className="mt-4 flex h-[92px] items-end justify-between gap-[6px]">
        {week.map((point) => (
          <span
            key={point.weekday}
            className={`block flex-1 rounded-t-full ${
              point === lastKnown ? 'bg-accent' : 'bg-neutral-200/22'
            }`}
            style={{ height: `${String(heightPercent(point.position, best, worst))}%` }}
          />
        ))}
      </div>
      <div className="mt-[10px] flex justify-between text-[10px] tracking-[0.12em] text-neutral-500">
        {week.map((point) => (
          <span key={point.weekday}>{point.weekday}</span>
        ))}
      </div>
      {known.length < 2 && (
        <p className="mt-3 text-[11px] leading-[1.4] text-neutral-500">
          Столбики появятся, когда наберётся история проверок за эту неделю.
        </p>
      )}
    </div>
  );
}

function AskPosition({
  universityId,
  positions,
  onSaved,
}: {
  readonly universityId: number | null;
  readonly positions: Positions;
  readonly onSaved: () => void;
}) {
  const save = useSavePosition(universityId);
  const [value, setValue] = useState('');

  const valid = isValidPosition(value, positions.min_position, positions.max_position);
  const invalid = value !== '' && !valid;

  return (
    <>
      <h1 className="mt-9 font-heading text-[40px] leading-[1.02] tracking-[-0.04em] text-pretty">
        На каком вы месте в списке?
      </h1>
      <p className="mt-3 text-[14px] text-neutral-700">
        Введите один раз — дальше я сам сравню при каждом обновлении списков вуза.
      </p>

      <input
        type="number"
        inputMode="numeric"
        min={positions.min_position}
        max={positions.max_position}
        placeholder="например 116"
        value={value}
        aria-label="Ваше место в конкурсном списке"
        aria-invalid={invalid}
        onChange={(event) => {
          setValue(event.target.value);
        }}
        className={`mt-5 w-full rounded-full border-[1.5px] bg-transparent px-6 py-5 font-heading text-[30px] tracking-[-0.03em] ${
          invalid ? 'border-accent' : 'border-neutral-400'
        }`}
      />

      {invalid && (
        <p className="mt-2 text-[12px] text-accent-700" role="alert">
          Место от {positions.min_position} до {positions.max_position}
        </p>
      )}

      <Button
        variant="dark"
        disabled={!valid || save.isPending}
        onClick={() => {
          save.mutate(Number(value), { onSuccess: onSaved });
        }}
        className="mt-[14px] w-full px-[10px] py-[17px] text-[14px] disabled:border-neutral-400 disabled:bg-neutral-400 disabled:text-neutral-600 disabled:opacity-100"
      >
        Сохранить позицию
      </Button>

      {save.isError && <Hint>Не удалось сохранить позицию. Попробуйте ещё раз.</Hint>}

      {positions.position !== null && (
        <Button
          variant="outline"
          onClick={onSaved}
          className="mt-[10px] w-full px-[10px] py-[17px] text-[14px]"
        >
          Оставить {positions.position}
        </Button>
      )}
    </>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

/** Текст сравнения из макета, экран 9. */
function comparison(positions: Positions): string {
  const parts: string[] = [];
  if (positions.previous_position !== null) {
    parts.push(`В прошлый раз вы были ${positions.previous_position}-м.`);
  }
  if (positions.estimated_passing_score !== null && positions.position !== null) {
    const inside = positions.position <= positions.estimated_passing_score;
    parts.push(
      `Ориентировочный проходной — ${positions.estimated_passing_score} место, вы ${
        inside ? 'внутри' : 'ниже границы'
      }.`,
    );
  } else {
    parts.push('Ориентировочная граница списка появится, когда у отслеживания будет направление.');
  }
  return parts.join(' ');
}

/**
 * Высота столбика в процентах.
 *
 * Лучшее место за неделю — полная высота, худшее — четверть: иначе разница в
 * пару мест выглядела бы как обвал. День без проверки — нулевая высота.
 */
function heightPercent(position: number | null, best: number, worst: number): number {
  const MIN_HEIGHT = 25;
  if (position === null) return 0;
  if (best === worst) return 100;
  return MIN_HEIGHT + ((worst - position) / (worst - best)) * (100 - MIN_HEIGHT);
}

function isValidPosition(value: string, min: number, max: number): boolean {
  if (!/^\d+$/.test(value.trim())) return false;
  const position = Number(value);
  return position >= min && position <= max;
}
