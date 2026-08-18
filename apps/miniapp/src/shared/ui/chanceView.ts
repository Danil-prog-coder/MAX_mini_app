/**
 * Как выглядит метка шанса поступления (ТЗ 2.5, уточнения У11, Д1).
 *
 * Отдельным модулем от компонента: таблицу читают и карточка вуза, и шапка
 * экрана, где подпись стоит без точек. Держать её в файле с компонентом мешает
 * горячей перезагрузке (та же причина, что у `buttonStyles`).
 *
 * Носителей смысла три и все обязательны: индикатор из трёх точек,
 * caps-подпись и эмодзи 🟢/🟡/🔴 из ТЗ 2.5 рядом с ней. Заливка карточек
 * зелёным, жёлтым и красным не вводится — палитра остаётся сведённой к
 * «песок + чернила + терракота» (У11).
 */
import type { Chance } from '@/shared/api/vuzSelection';

export interface ChanceView {
  /** Заполненных точек из трёх. */
  readonly dots: number;
  readonly label: string;
  readonly emoji: string;
}

export const TOTAL_DOTS = 3;

export const CHANCE_VIEW: Record<Chance, ChanceView> = {
  high: { dots: 3, label: 'ВЫСОКИЙ ШАНС', emoji: '🟢' },
  borderline: { dots: 2, label: 'ПОГРАНИЧНЫЙ', emoji: '🟡' },
  unlikely: { dots: 1, label: 'МАЛОВЕРОЯТНО', emoji: '🔴' },
};
