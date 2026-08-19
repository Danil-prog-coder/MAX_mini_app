/**
 * Результат профориентационного теста (ТЗ 1.4–1.6).
 *
 * Топ-3 направления, переход в подбор вузов с предзаполненным направлением,
 * вакансии по профилю из открытых данных и сохранение результата в профиль
 * с начислением +50 баллов (уточнение У21).
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';

import {
  useLatestResult,
  useSaveResult,
  useVacancies,
  type TestResult,
} from '@/shared/api/careerTest';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';
import { Sheet } from '@/shared/ui/Sheet';

export function CareerTestResultsScreen() {
  const result = useLatestResult();
  const [vacanciesFor, setVacanciesFor] = useState<string | null>(null);

  return (
    <>
      <ScreenHeader title="Результат" />

      {result.isPending && <Hint>Загружаю результат…</Hint>}
      {result.isError && <Hint>Не удалось загрузить результат теста.</Hint>}

      {result.isSuccess && result.data === null && (
        <>
          <Hint>Тест ещё не пройден — десять вопросов и топ-3 направления в конце.</Hint>
          <Link
            to="/career-test"
            className={buttonClass('accent', 'mt-5 w-full px-[18px] py-4 text-[15px]')}
          >
            Пройти тест
          </Link>
        </>
      )}

      {result.isSuccess && result.data !== null && (
        <ResultView result={result.data} onShowVacancies={setVacanciesFor} />
      )}

      <VacanciesSheet
        direction={vacanciesFor}
        onClose={() => {
          setVacanciesFor(null);
        }}
      />
    </>
  );
}

function ResultView({
  result,
  onShowVacancies,
}: {
  readonly result: TestResult;
  readonly onShowVacancies: (direction: string) => void;
}) {
  const save = useSaveResult();
  const [first, ...rest] = result.top_directions;
  const saved = result.saved_to_profile;

  if (!first) {
    return <Hint>Результат посчитан, но справочник направлений пуст.</Hint>;
  }

  return (
    <>
      <div className="mt-6 text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        ВАШЕ НАПРАВЛЕНИЕ №1
      </div>
      <h1 className="mt-[6px] font-heading text-[46px] leading-[0.98] tracking-[-0.04em]">
        {first.name}
      </h1>

      <div className="mt-[18px] rounded-[32px] bg-text px-[22px] pt-5 pb-[22px] text-neutral-200">
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-heading text-[62px] leading-none tracking-[-0.05em]">
            {first.match_percent}
            <span className="text-[26px]">%</span>
          </span>
          <span className="text-[10px] font-bold tracking-[0.16em] text-accent-300">
            СОВПАДЕНИЕ
          </span>
        </div>
        <p className="mt-3 text-[14px] leading-[1.45] text-neutral-400 text-pretty">
          {/* Объяснение от LLM, если оно есть; иначе описание направления из
              справочника — недоступная модель не оставляет экран пустым. */}
          {result.explanation || first.summary}
        </p>
        <div className="mt-4 flex gap-[9px]">
          <Link
            to={`/vuz-selection?direction=${encodeURIComponent(first.code)}`}
            className={buttonClass('accent', 'flex-1 px-[10px] py-[14px] text-[13px]')}
          >
            Показать вузы
          </Link>
          <Button
            variant="ghostOnDark"
            className="flex-1 px-[10px] py-[14px] text-[13px]"
            onClick={() => {
              onShowVacancies(first.code);
            }}
          >
            Вакансии
          </Button>
        </div>
      </div>

      {rest.length > 0 && (
        <div className="mt-[18px] flex flex-col gap-[10px]">
          {rest.map((direction, position) => (
            <div
              key={direction.code}
              className="flex items-center gap-[14px] rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-4"
            >
              <span className="font-heading text-[26px] tracking-[-0.03em]">{position + 2}</span>
              <div className="min-w-0 flex-1">
                <div className="text-[15px]">{direction.name}</div>
                <div className="mt-[2px] text-[12px] text-neutral-600">
                  {direction.match_percent}% · {direction.summary}
                </div>
              </div>
              <Link
                to={`/vuz-selection?direction=${encodeURIComponent(direction.code)}`}
                className={buttonClass('outline', 'flex-none px-4 py-[10px] text-[12px]')}
              >
                Вузы
              </Link>
            </div>
          ))}
        </div>
      )}

      <Button
        variant={saved ? 'accent' : 'dark'}
        disabled={saved || save.isPending}
        onClick={() => {
          save.mutate(result.id);
        }}
        className="mt-4 w-full px-[10px] py-[17px] text-[14px] disabled:opacity-100"
      >
        {saved ? 'Сохранено в профиль · +50 баллов' : 'Сохранить в профиль'}
      </Button>

      {save.isError && <Hint>Не удалось сохранить результат. Попробуйте ещё раз.</Hint>}
    </>
  );
}

function VacanciesSheet({
  direction,
  onClose,
}: {
  readonly direction: string | null;
  readonly onClose: () => void;
}) {
  const vacancies = useVacancies(direction);

  return (
    <Sheet
      open={direction !== null}
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
      title="Вакансии по профилю · открытые данные"
    >
      {vacancies.isPending && <SheetHint>Загружаю…</SheetHint>}
      {vacancies.isError && <SheetHint>Не удалось получить данные о вакансиях.</SheetHint>}
      {vacancies.data?.items.length === 0 && (
        <SheetHint>
          Источник вакансий сейчас недоступен, а сохранённых данных ещё нет. Загляните позже.
        </SheetHint>
      )}
      {vacancies.data?.items.map((item) => (
        <div
          key={item.title}
          className="flex flex-none items-center justify-between gap-3 rounded-3xl border-[1.5px] border-neutral-400 px-5 py-4"
        >
          <span className="text-[15px]">{item.title}</span>
          <span className="font-heading text-[20px] tracking-[-0.03em]">
            {item.count.toLocaleString('ru-RU')}
          </span>
        </div>
      ))}
      {vacancies.data?.stale === true && (
        <SheetHint>Источник не ответил — показаны последние сохранённые данные.</SheetHint>
      )}
    </Sheet>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700 text-pretty">{children}</p>;
}

function SheetHint({ children }: { readonly children: React.ReactNode }) {
  return (
    <p className="flex-none text-[13px] leading-[1.45] text-neutral-700 text-pretty">{children}</p>
  );
}
