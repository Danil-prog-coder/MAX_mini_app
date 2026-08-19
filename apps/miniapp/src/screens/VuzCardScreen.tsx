/**
 * Карточка вуза (ТЗ 2.6, 2.7).
 *
 * Бюджетные места, стоимость платного обучения, наличие общежития и дата
 * окончания приёма документов плюс кнопка «Отслеживать этот вуз», которая
 * наполняет блок 3.
 *
 * Цифры приёмной кампании подписаны как демонстрационные (уточнения У4, Д3):
 * настоящие здесь только название, адрес и координаты вуза.
 */
import { Link, useParams, useSearchParams } from 'react-router-dom';

import {
  useTrackUniversity,
  useUniversityCard,
  type Match,
  type UniversityCard,
} from '@/shared/api/vuzSelection';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ChanceDots } from '@/shared/ui/ChanceLabel';
import { CHANCE_VIEW } from '@/shared/ui/chanceView';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

export function VuzCardScreen() {
  const { universityId } = useParams();
  const [params] = useSearchParams();
  const parsed = Number(universityId);
  const id = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  const card = useUniversityCard(id);
  const programs = card.data?.programs ?? [];
  // Программа, из карточки которой пришли. Если адрес открыт напрямую — первая
  // в списке: он уже отсортирован по шансу.
  const program =
    programs.find((item) => item.direction.code === params.get('direction')) ?? programs[0] ?? null;

  return (
    <>
      <ScreenHeader
        title={program === null ? 'Карточка вуза' : CHANCE_VIEW[program.chance].label}
      />

      {card.isPending && <Hint>Загружаю карточку…</Hint>}
      {card.isError && <Hint>Не удалось загрузить карточку вуза. Проверьте связь.</Hint>}

      {(id === null || (card.isSuccess && card.data === null)) && (
        <>
          <Hint>Такого вуза в справочнике нет — возможно, ссылка устарела.</Hint>
          <Link
            to="/vuz-selection/results"
            className={buttonClass('accent', 'mt-4 w-full px-[10px] py-[17px] text-[14px]')}
          >
            К списку вузов
          </Link>
        </>
      )}

      {card.data != null && <CardView card={card.data} program={program} />}
    </>
  );
}

function CardView({
  card,
  program,
}: {
  readonly card: UniversityCard;
  readonly program: Match | null;
}) {
  const track = useTrackUniversity();
  const { university } = card;
  // Пока запрос летит, кнопку уже можно показать в конечном состоянии: она
  // идемпотентна, и мигать надписью туда-обратно незачем.
  const tracked = card.tracked || track.isSuccess;

  return (
    <>
      {program !== null && (
        <div className="mt-4">
          <ChanceDots dots={CHANCE_VIEW[program.chance].dots} />
        </div>
      )}

      <h1 className="mt-6 font-heading text-[44px] leading-[0.98] tracking-[-0.04em]">
        {university.short_name}
      </h1>
      <p className="mt-[10px] text-[14px] text-neutral-700">
        {program?.direction.name ?? university.name}
      </p>
      <p className="mt-1 text-[12px] text-neutral-600">
        {university.city}, {university.address}
      </p>

      <div className="mt-[22px] grid grid-cols-2 gap-[10px]">
        <div className="rounded-[28px] bg-text px-5 py-[18px] text-neutral-200">
          <div className="text-[10px] font-bold tracking-[0.16em] text-accent-300">БЮДЖЕТ</div>
          <div className="mt-[2px] font-heading text-[40px] leading-[1.1] tracking-[-0.04em]">
            {program?.budget_places ?? university.budget_places ?? '—'}
          </div>
          <div className="text-[11px] text-neutral-500">мест</div>
        </div>
        <Tile label="ПЛАТНО" value={formatPrice(university.tuition_price)} unit="тыс ₽ / год" />
        <Tile label="ОБЩЕЖИТИЕ" value={university.has_dormitory ? 'Есть' : 'Нет'} small />
        <Tile label="ПРИЁМ ДО" value={formatDeadline(university.admission_deadline)} small />
      </div>

      <p className="mt-3 text-[12px] text-neutral-600">
        Бюджетные места, стоимость, общежитие и дата приёма — демонстрационные данные, а не
        официальные цифры приёмной кампании.
      </p>

      {program !== null && (
        <p className="mt-2 text-[12px] text-neutral-600">
          Ваши {program.applicant_score} · проходной прошлого года — {program.passing_score} (демо)
        </p>
      )}

      <Button
        variant={tracked ? 'outline' : 'accent'}
        disabled={tracked || track.isPending}
        onClick={() => {
          track.mutate({
            universityId: university.id,
            direction: program?.direction.code ?? null,
          });
        }}
        className="mt-4 w-full px-[10px] py-[17px] text-[14px] disabled:opacity-100"
      >
        {tracked ? 'Уже отслеживается' : 'Отслеживать этот вуз'}
      </Button>

      {track.isError && <Hint>Не удалось добавить вуз в отслеживаемые. Попробуйте ещё раз.</Hint>}

      {tracked && (
        <Link
          to="/tracker"
          className={buttonClass('dark', 'mt-[10px] w-full px-[10px] py-[17px] text-[14px]')}
        >
          Перейти в трекер
        </Link>
      )}

      {card.programs.length === 0 && (
        <>
          <Hint>
            Шанс поступления не посчитан: баллы ЕГЭ ещё не введены или сданных предметов не хватает
            ни на одно направление этого вуза.
          </Hint>
          <Link
            to="/vuz-selection"
            className={buttonClass('outline', 'mt-3 w-full px-[10px] py-[17px] text-[14px]')}
          >
            Ввести баллы ЕГЭ
          </Link>
        </>
      )}
    </>
  );
}

function Tile({
  label,
  value,
  unit,
  small = false,
}: {
  readonly label: string;
  readonly value: string;
  readonly unit?: string;
  readonly small?: boolean;
}) {
  return (
    <div className="rounded-[28px] border-[1.5px] border-neutral-400 px-5 py-[18px]">
      <div className="text-[10px] font-bold tracking-[0.16em] text-neutral-600">{label}</div>
      <div
        className={`mt-[2px] font-heading tracking-[-0.03em] ${
          small ? 'text-[30px] leading-[1.35]' : 'text-[40px] leading-[1.1] tracking-[-0.04em]'
        }`}
      >
        {value}
      </div>
      {unit !== undefined && <div className="text-[11px] text-neutral-600">{unit}</div>}
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

/** Стоимость обучения хранится в рублях, а в макете показана в тысячах. */
function formatPrice(price: number | null): string {
  if (price === null) return '—';
  return String(Math.round(price / 1000));
}

function formatDeadline(deadline: string | null): string {
  if (deadline === null) return '—';
  const parsed = new Date(deadline);
  if (Number.isNaN(parsed.getTime())) return '—';
  return parsed.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}
