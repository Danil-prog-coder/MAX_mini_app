/**
 * Метка шанса поступления: точки, caps-подпись и эмодзи (уточнения У11, Д1).
 *
 * Точки — единственная часть, которая не читается вслух, поэтому у обёртки
 * есть `aria-label`: без него скринридер услышал бы только эмодзи.
 */
import type { Chance } from '@/shared/api/vuzSelection';

import { CHANCE_VIEW, TOTAL_DOTS } from './chanceView';

interface ChanceLabelProps {
  readonly chance: Chance;
  /** Метка стоит на тёмной карточке: у неё другие цвета подписи и пустых точек. */
  readonly onDark?: boolean;
}

export function ChanceLabel({ chance, onDark = false }: ChanceLabelProps) {
  const view = CHANCE_VIEW[chance];

  return (
    <div
      className="flex items-center justify-between gap-3"
      aria-label={`Шанс поступления: ${view.label.toLowerCase()}`}
    >
      <span
        className={`text-[10px] font-bold tracking-[0.18em] ${
          onDark ? 'text-accent-300' : 'text-neutral-600'
        }`}
      >
        {view.emoji} {view.label}
      </span>
      <ChanceDots dots={view.dots} onDark={onDark} />
    </div>
  );
}

/** Те же три точки без подписи: в карточке вуза подпись стоит в шапке экрана. */
export function ChanceDots({
  dots,
  onDark = false,
}: {
  readonly dots: number;
  readonly onDark?: boolean;
}) {
  return (
    <span className="flex flex-none gap-[5px]" aria-hidden="true">
      {Array.from({ length: TOTAL_DOTS }, (_, index) => (
        <span
          key={index}
          className={`block h-[9px] w-[9px] rounded-full ${
            index < dots ? 'bg-accent' : onDark ? 'bg-neutral-200/25' : 'bg-neutral-400'
          }`}
        />
      ))}
    </span>
  );
}
