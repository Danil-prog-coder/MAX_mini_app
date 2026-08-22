/**
 * Шансы поступления — список направлений в вузах (ТЗ 2.5).
 *
 * Метки шанса собраны в `ChanceLabel`: три точки, caps-подпись и эмодзи
 * 🟢/🟡/🔴 (уточнения У11, Д1). Расчёт целиком на сервере — здесь только
 * отрисовка, иначе формула У12 разъехалась бы между клиентом и бэкендом.
 *
 * Цифры приёмной кампании подписаны как демонстрационные: выдавать их за
 * официальные нельзя (уточнения У4, Д3).
 *
 * Порядок выдачи учитывает профориентационный тест, и экран обязан сказать это
 * прямо — плашкой над списком (уточнение У28). Список открывается первой
 * десяткой и растёт по пять: сорок карточек подряд читать невозможно, а
 * «показать все» одним нажатием прячет от человека, сколько их вообще.
 */
import { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';

import { useDirections, useMatches, type Match } from '@/shared/api/vuzSelection';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ChanceLabel } from '@/shared/ui/ChanceLabel';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

/** Сколько карточек видно сразу и на сколько растёт список (уточнение У28). */
const FIRST_PAGE = 10;
const PAGE_STEP = 5;

export function VuzSelectionResultsScreen() {
  const [params] = useSearchParams();
  // Направление, с которым пришли из теста (ТЗ 1.5): выдача сужается до него,
  // но фильтр видно и его можно снять — иначе экран выглядел бы полупустым
  // без объяснения.
  const directionCode = params.get('direction');

  const matches = useMatches();
  const directions = useDirections();
  const direction = directions.data?.find((item) => item.code === directionCode) ?? null;

  const all = matches.data?.items ?? [];
  const items =
    directionCode === null ? all : all.filter((m) => m.direction.code === directionCode);

  const [visible, setVisible] = useState(FIRST_PAGE);
  // Смена фильтра — это новый список, и показывать его сразу развёрнутым
  // неправильно: человек не просил показать всё, он сменил направление.
  // Сброс идёт прямо в рендере, а не эффектом: это подстройка состояния под
  // изменившийся пропс, и эффект здесь дал бы лишний проход рендера.
  const [pagedFor, setPagedFor] = useState(directionCode);
  if (pagedFor !== directionCode) {
    setPagedFor(directionCode);
    setVisible(FIRST_PAGE);
  }

  const shown = items.slice(0, visible);
  const hidden = items.length - shown.length;

  return (
    <>
      <ScreenHeader title="Ваши шансы" />

      <div className="mt-[22px] flex items-baseline gap-[14px]">
        <span className="font-heading text-[104px] leading-[0.92] tracking-[-0.055em]">
          {matches.data?.total ?? 0}
        </span>
        <span className="text-[11px] font-bold tracking-[0.18em] text-neutral-600">БАЛЛА</span>
      </div>
      <p className="mt-1 text-[12px] text-neutral-600">
        Расчёт по данным приёмных кампаний прошлых лет. Проходные баллы и число мест —
        демонстрационные.
      </p>

      {direction !== null && (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <span className="rounded-full border-[1.5px] border-neutral-400 px-4 py-2 text-[12px]">
            Направление: {direction.name}
          </span>
          <Link
            to="/vuz-selection/results"
            className={buttonClass('outline', 'px-4 py-2 text-[12px]')}
          >
            Показать все
          </Link>
        </div>
      )}

      {matches.isPending && <Hint>Считаю шансы…</Hint>}
      {matches.isError && (
        <Hint>Не удалось подобрать вузы. Проверьте связь и попробуйте ещё раз.</Hint>
      )}

      {matches.isSuccess && all.length === 0 && (
        <>
          <Hint>
            Пока подбирать не по чему: баллы ЕГЭ не введены или ни одно направление не совпало с
            набором сданных предметов.
          </Hint>
          <Link
            to="/vuz-selection"
            className={buttonClass('accent', 'mt-4 w-full px-[10px] py-[17px] text-[14px]')}
          >
            Ввести баллы
          </Link>
        </>
      )}

      {matches.isSuccess && all.length > 0 && items.length === 0 && (
        <Hint>
          По этому направлению подходящих вузов не нашлось — возможно, не сданы его обязательные
          предметы. Снимите фильтр, чтобы увидеть остальные.
        </Hint>
      )}

      {items.length > 0 && (
        <>
          <CareerTestNote applied={matches.data?.career_test_applied ?? false} />

          <div className="mt-3 flex flex-col gap-[10px]">
            {shown.map((match, position) => (
              <MatchCard key={match.program_id} match={match} position={position} />
            ))}
          </div>

          {hidden > 0 && (
            <button
              type="button"
              onClick={() => {
                setVisible((current) => current + PAGE_STEP);
              }}
              className={buttonClass('outline', 'mt-3 w-full px-[10px] py-[15px] text-[13px]')}
            >
              Показать ещё {Math.min(PAGE_STEP, hidden)} из {hidden}
            </button>
          )}
        </>
      )}
    </>
  );
}

/**
 * Плашка над списком: учтён ли профориентационный тест (уточнение У28).
 *
 * Она есть в обоих состояниях. Показывать её только при пройденном тесте
 * бессмысленно: человек, который тест не проходил, как раз и не знает, что
 * выдачу можно улучшить, — поэтому второе состояние ведёт на тест.
 */
function CareerTestNote({ applied }: { readonly applied: boolean }) {
  if (applied) {
    return (
      <div className="mt-[22px] rounded-[22px] bg-accent-200 px-[18px] py-[13px]">
        <div className="text-[10px] font-bold tracking-[0.16em] text-accent-700">
          НА ОСНОВЕ ПРОФТЕСТИРОВАНИЯ
        </div>
        <p className="mt-1 text-[12px] text-pretty text-neutral-700">
          Сверху — направления, которые тест назвал самыми близкими. Внутри направления порядок по
          шансу поступить.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-[22px] rounded-[22px] border-[1.5px] border-neutral-400 px-[18px] py-[13px]">
      <div className="text-[10px] font-bold tracking-[0.16em] text-neutral-600">
        НЕ УЧИТЫВАЕТ ПРОФТЕСТИРОВАНИЕ
      </div>
      <p className="mt-1 text-[12px] text-pretty text-neutral-700">
        Список отсортирован только по шансу поступить. Пройдите тест — и сверху окажутся направления
        по вашей специфике.
      </p>
      <Link
        to="/career-test"
        className={buttonClass('accent', 'mt-3 inline-flex px-4 py-[9px] text-[12px]')}
      >
        Пройти тест
      </Link>
    </div>
  );
}

function MatchCard({ match, position }: { readonly match: Match; readonly position: number }) {
  // Тёмная карточка достаётся только высокому шансу: так первый экран сразу
  // показывает, куда человек реально проходит (макет, экран 6).
  const dark = match.chance === 'high';

  return (
    <Link
      to={`/vuz-selection/${String(match.university.id)}?direction=${encodeURIComponent(match.direction.code)}`}
      style={{ animationDelay: `${String(position * 60)}ms` }}
      className={`animate-card-in block w-full rounded-[30px] px-[22px] py-5 text-left transition-colors ${
        dark
          ? 'bg-text text-neutral-200 hover:bg-neutral-800'
          : 'border-[1.5px] border-neutral-400 hover:bg-text/6'
      }`}
    >
      <ChanceLabel chance={match.chance} onDark={dark} />
      <div className="mt-[6px] font-heading text-[24px] leading-[1.1] tracking-[-0.03em]">
        {match.university.short_name}
      </div>
      <div className={`mt-[6px] text-[13px] ${dark ? 'text-neutral-400' : 'text-neutral-700'}`}>
        {match.direction.name}
      </div>
      <div className={`mt-[10px] text-[12px] ${dark ? 'text-neutral-500' : 'text-neutral-600'}`}>
        ваши {match.applicant_score} · проходной прошлого года — {match.passing_score} (демо)
      </div>
    </Link>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}
