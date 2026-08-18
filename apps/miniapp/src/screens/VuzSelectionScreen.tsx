/**
 * Подбор вуза по баллам ЕГЭ — ввод предметов и баллов (ТЗ 2.2–2.4).
 *
 * Требование ТЗ 2.4 «выход в меню не теряет введённое» выполнено тем, что
 * баллы вообще не живут на клиенте: черновик уходит на сервер сам, с паузой
 * после последнего нажатия, и досохраняется при уходе с экрана. Побочно это
 * закрывает ТЗ 0.2 — введённое с телефона видно на десктопе.
 *
 * Список предметов и границы проверки приходят с сервера (ТЗ 2.2, 2.3): свой
 * список на клиенте разошёлся бы со справочником направлений при первом же его
 * изменении, и направление стало бы недостижимым.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { useDirections, useSaveScores, useScores, useSubjects } from '@/shared/api/vuzSelection';
import { Button } from '@/shared/ui/Button';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

/** Пауза после последнего нажатия, после которой черновик уходит на сервер. */
const AUTOSAVE_DELAY_MS = 500;

/** Черновик: у выбранного предмета балл либо введён, либо ещё нет. */
type Draft = Record<string, string>;

export function VuzSelectionScreen() {
  const navigate = useNavigate();
  const [params] = useSearchParams();
  // Направление из блока 1 (ТЗ 1.5): им предзаполняется набор предметов.
  const directionCode = params.get('direction');

  const subjects = useSubjects();
  const scores = useScores();
  const directions = useDirections();
  const save = useSaveScores();

  // Правки пользователя. Пока их нет, экран показывает то, что пришло с
  // сервера, — состояние заводится не в эффекте, а появляется при первой
  // правке: копия серверных данных на клиенте не нужна (тех. ТЗ 8.2).
  const [edited, setEdited] = useState<Draft | null>(null);

  const direction = directions.data?.find((item) => item.code === directionCode) ?? null;

  const initial = useMemo<Draft | null>(() => {
    if (!scores.isSuccess) return null;
    const saved = Object.entries(scores.data.scores);
    if (saved.length > 0) {
      return Object.fromEntries(saved.map(([subject, score]) => [subject, String(score)]));
    }
    // Направление из теста предзаполняет свои обязательные предметы (ТЗ 1.5).
    // Пока справочник не пришёл, черновика нет: иначе он завёлся бы пустым и
    // предзаполнение уже не сработало бы.
    if (directionCode !== null && direction === null) return null;
    return Object.fromEntries((direction?.required_subjects ?? []).map((subject) => [subject, '']));
  }, [scores.isSuccess, scores.data, directionCode, direction]);

  const draft = edited ?? initial;
  const limits = subjects.data;
  const valid = useMemo(() => validScores(draft ?? {}, limits), [draft, limits]);
  const total = Object.values(valid).reduce((sum, score) => sum + score, 0);
  const selected = Object.keys(draft ?? {});
  const minSubjects = limits?.min_subjects ?? 3;
  const ready = selected.length >= minSubjects && Object.keys(valid).length === selected.length;

  useAutosave(valid, draft !== null, save.mutate);

  const toggle = (subject: string) => {
    const next = { ...(draft ?? {}) };
    if (subject in next) delete next[subject];
    else next[subject] = '';
    setEdited(next);
  };

  const setScore = (subject: string, value: string) => {
    setEdited({ ...(draft ?? {}), [subject]: value });
  };

  return (
    <>
      <ScreenHeader title="Подбор по ЕГЭ" />

      <div className="mt-6 flex items-baseline gap-[14px]">
        <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">{total}</span>
        <span className="text-[11px] font-bold tracking-[0.18em] text-neutral-600">
          СУММА БАЛЛОВ
        </span>
      </div>

      {direction !== null && (
        <p className="mt-1 text-[12px] text-neutral-600">
          Предметы выбраны под направление «{direction.name}» — их можно изменить.
        </p>
      )}

      <div className="mt-5 text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        СДАННЫЕ ПРЕДМЕТЫ
      </div>

      {subjects.isError && <Hint>Не удалось загрузить список предметов. Проверьте связь.</Hint>}

      <div className="mt-3 flex flex-wrap gap-2">
        {(limits?.subjects ?? []).map((subject) => {
          const on = draft !== null && subject in draft;
          return (
            <button
              key={subject}
              type="button"
              aria-pressed={on}
              onClick={() => {
                toggle(subject);
              }}
              className={`rounded-full border-[1.5px] px-[18px] py-3 text-[14px] transition-colors ${
                on
                  ? 'border-text bg-text text-neutral-200'
                  : 'border-neutral-400 text-text hover:bg-text/6'
              }`}
            >
              {subject}
            </button>
          );
        })}
      </div>

      <div className="mt-[18px] flex flex-col gap-[10px]">
        {selected.map((subject) => (
          <ScoreRow
            key={subject}
            subject={subject}
            value={draft?.[subject] ?? ''}
            min={limits?.min_score ?? 0}
            max={limits?.max_score ?? 100}
            onChange={(value) => {
              setScore(subject, value);
            }}
          />
        ))}
      </div>

      {selected.length === 0 && (
        <p className="mt-4 text-[12px] text-neutral-600">
          Выберите предметы и введите баллы. Введённое сохраняется — можно выйти в меню и вернуться.
        </p>
      )}

      {save.isError && (
        <Hint>
          Баллы не сохранились на сервере. Проверьте связь — введённое на экране осталось.
        </Hint>
      )}

      <Button
        variant={ready ? 'dark' : 'outline'}
        disabled={!ready}
        onClick={() => {
          // Сохраняем перед уходом: иначе выдача посчиталась бы по прошлому
          // набору, если автосохранение ещё не успело сработать.
          save.mutate(valid, {
            onSettled: () => {
              void navigate(
                directionCode === null
                  ? '/vuz-selection/results'
                  : `/vuz-selection/results?direction=${encodeURIComponent(directionCode)}`,
              );
            },
          });
        }}
        className="mt-[18px] w-full px-[10px] py-[17px] text-[14px] disabled:border-neutral-400 disabled:bg-neutral-400 disabled:text-neutral-600 disabled:opacity-100"
      >
        {ready
          ? 'Подобрать вузы'
          : `Выберите минимум ${String(minSubjects)} предмета и введите баллы`}
      </Button>
    </>
  );
}

function ScoreRow({
  subject,
  value,
  min,
  max,
  onChange,
}: {
  readonly subject: string;
  readonly value: string;
  readonly min: number;
  readonly max: number;
  readonly onChange: (value: string) => void;
}) {
  const invalid = value !== '' && !isValidScore(value, min, max);

  return (
    <label className="animate-card-in flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 py-3 pr-[14px] pl-5">
      <span className="min-w-0 flex-1 text-[15px]">{subject}</span>
      {invalid && (
        <span className="flex-none text-[11px] text-accent-700" role="alert">
          {min}–{max}
        </span>
      )}
      <input
        type="number"
        inputMode="numeric"
        min={min}
        max={max}
        placeholder="0"
        value={value}
        aria-label={`Балл ЕГЭ, ${subject}`}
        aria-invalid={invalid}
        onChange={(event) => {
          onChange(event.target.value);
        }}
        className={`w-24 flex-none rounded-full border-[1.5px] bg-transparent px-[14px] py-3 text-center font-heading text-[22px] tracking-[-0.03em] ${
          invalid ? 'border-accent' : 'border-neutral-400'
        }`}
      />
    </label>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

function isValidScore(value: string, min: number, max: number): boolean {
  // `Number('')` — ноль, а пустая строка баллом не является.
  if (!/^\d+$/.test(value.trim())) return false;
  const score = Number(value);
  return score >= min && score <= max;
}

function validScores(
  draft: Draft,
  limits: { min_score: number; max_score: number } | undefined,
): Record<string, number> {
  const min = limits?.min_score ?? 0;
  const max = limits?.max_score ?? 100;
  return Object.fromEntries(
    Object.entries(draft)
      .filter(([, value]) => isValidScore(value, min, max))
      .map(([subject, value]) => [subject, Number(value)]),
  );
}

/**
 * Отправляет черновик на сервер с паузой после последнего нажатия и
 * досохраняет его при уходе с экрана (ТЗ 2.4).
 *
 * Без досохранения человек, нажавший «Главное меню» сразу после ввода
 * последней цифры, терял бы её — а именно этого требование и запрещает.
 */
function useAutosave(
  scores: Record<string, number>,
  enabled: boolean,
  save: (scores: Record<string, number>) => void,
) {
  const serialized = JSON.stringify(scores);
  const pending = useRef<string | null>(null);
  const saveRef = useRef(save);
  // Первое значение считается уже сохранённым: оно и пришло с сервера.
  const lastSent = useRef<string | null>(null);

  useEffect(() => {
    saveRef.current = save;
  }, [save]);

  useEffect(() => {
    if (!enabled) return;
    if (lastSent.current === null) {
      lastSent.current = serialized;
      return;
    }
    if (lastSent.current === serialized) return;

    pending.current = serialized;
    const timer = setTimeout(() => {
      lastSent.current = serialized;
      pending.current = null;
      saveRef.current(JSON.parse(serialized) as Record<string, number>);
    }, AUTOSAVE_DELAY_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [serialized, enabled]);

  useEffect(() => {
    return () => {
      const unsaved = pending.current;
      if (unsaved !== null) {
        saveRef.current(JSON.parse(unsaved) as Record<string, number>);
      }
    };
  }, []);
}
