/**
 * Трекер конкурсных списков — список отслеживаемых вузов (ТЗ 3.2, 3.3).
 *
 * Вузы попадают сюда из карточки блока 2. Пустой список — не ошибка и не
 * тупик: экран объясняет, как его наполнить, и ведёт в подбор (ТЗ 3.3).
 */
import { Link } from 'react-router-dom';

import { useTracked, type TrackedItem } from '@/shared/api/tracker';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ChevronRightIcon } from '@/shared/ui/icons';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

export function TrackerScreen() {
  const tracked = useTracked();
  const items = tracked.data?.items ?? [];

  return (
    <>
      <ScreenHeader title="Трекер списков" />

      <div className="mt-6 flex items-baseline gap-[14px]">
        <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">
          {tracked.data?.total ?? 0}
        </span>
        <span className="text-[11px] leading-[1.3] font-bold tracking-[0.18em] text-neutral-600">
          {plural(tracked.data?.total ?? 0)}
          <br />
          ОТСЛЕЖИВАЕТСЯ
        </span>
      </div>

      {tracked.isPending && <Hint>Загружаю список…</Hint>}
      {tracked.isError && <Hint>Не удалось загрузить список. Проверьте связь.</Hint>}

      {tracked.isSuccess && items.length === 0 && (
        <>
          <p className="mt-[22px] text-[16px] leading-[1.45] text-neutral-700">
            Пока пусто. Подберите вуз по баллам ЕГЭ и нажмите «Отслеживать» — дальше я сам слежу за
            списками.
          </p>
          <Link
            to="/vuz-selection"
            className={buttonClass('accent', 'mt-5 w-full px-6 py-[17px] text-[15px]')}
          >
            Подобрать вуз
          </Link>
        </>
      )}

      {items.length > 0 && (
        <div className="mt-[22px] flex flex-col gap-[10px]">
          {items.map((item, position) => (
            <TrackedCard key={item.university.id} item={item} position={position} />
          ))}
        </div>
      )}
    </>
  );
}

function TrackedCard({
  item,
  position,
}: {
  readonly item: TrackedItem;
  readonly position: number;
}) {
  // Известная позиция достаётся тёмной карточке с крупным числом; неизвестная —
  // обводке с шевроном (макет, экран 8).
  const known = item.position !== null;

  return (
    <Link
      to={`/tracker/${String(item.university.id)}`}
      style={{ animationDelay: `${String(position * 60)}ms` }}
      className={`animate-card-in flex w-full items-center gap-[14px] rounded-[28px] px-5 py-[18px] text-left transition-colors ${
        known
          ? 'bg-text text-neutral-200 hover:bg-neutral-800'
          : 'border-[1.5px] border-neutral-400 hover:bg-text/6'
      }`}
    >
      <div className="min-w-0 flex-1">
        <div
          className={`text-[10px] font-bold tracking-[0.18em] ${
            known ? 'text-accent-300' : 'text-neutral-600'
          }`}
        >
          {known ? 'ВАША ПОЗИЦИЯ' : 'ПОЗИЦИЯ НЕ УКАЗАНА'}
        </div>
        <div className="mt-[3px] font-heading text-[20px] tracking-[-0.025em]">
          {item.university.short_name}
        </div>
        <div className={`mt-1 text-[12px] ${known ? 'text-neutral-500' : 'text-neutral-600'}`}>
          {item.direction?.name ?? item.university.city}
          {item.university.admission_deadline !== null &&
            ` · приём до ${formatDeadline(item.university.admission_deadline)}`}
        </div>
      </div>
      {known ? (
        <span className="font-heading text-[44px] tracking-[-0.04em]">{item.position}</span>
      ) : (
        <ChevronRightIcon />
      )}
    </Link>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

/** «1 ВУЗ», «2 ВУЗА», «5 ВУЗОВ» — подпись под крупным числом (макет, экран 8). */
function plural(count: number): string {
  const tail = count % 100;
  if (tail >= 11 && tail <= 14) return 'ВУЗОВ';
  const last = count % 10;
  if (last === 1) return 'ВУЗ';
  if (last >= 2 && last <= 4) return 'ВУЗА';
  return 'ВУЗОВ';
}

function formatDeadline(deadline: string): string {
  const parsed = new Date(deadline);
  if (Number.isNaN(parsed.getTime())) return '—';
  return parsed.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
}
