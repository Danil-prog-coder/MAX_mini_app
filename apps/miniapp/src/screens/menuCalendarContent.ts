/**
 * Разметка календаря на главной: месяцы, дни недели, границы периода.
 *
 * Здесь только чистые функции над датами — ни React, ни запросов. Ошибка в
 * этой арифметике не видна глазом: сетка просто встаёт на день левее, и
 * события оказываются не в тех клетках, поэтому она закрыта тестами.
 *
 * Даты настоящие. Раньше календарь показывал три месяца из макета и считал
 * «сегодня» 13 июля 2026 — это имело смысл, пока события были выдуманными.
 * Теперь события приходят с сервера (уточнение У32): свои, дедлайны приёмной
 * кампании и пары, — и календарь обязан жить в настоящем времени.
 *
 * Всё считается в местном времени браузера. Часовой пояс продукта один
 * (`SCHEDULE_TIMEZONE` на бэкенде), и открытый вопрос про пояса вузов записан
 * в PLAN.md; на границе суток календарь может разойтись с сервером на день —
 * это известная цена, а не недосмотр.
 */

/** Дни недели с понедельника: сетка начинается с него, как в макете. */
export const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'] as const;

const MONTH_NAMES = [
  'ЯНВАРЬ',
  'ФЕВРАЛЬ',
  'МАРТ',
  'АПРЕЛЬ',
  'МАЙ',
  'ИЮНЬ',
  'ИЮЛЬ',
  'АВГУСТ',
  'СЕНТЯБРЬ',
  'ОКТЯБРЬ',
  'НОЯБРЬ',
  'ДЕКАБРЬ',
] as const;

/** Родительный падеж для заголовка шторки: «25 АВГУСТА · ВТ». */
const MONTH_GENITIVE = [
  'ЯНВАРЯ',
  'ФЕВРАЛЯ',
  'МАРТА',
  'АПРЕЛЯ',
  'МАЯ',
  'ИЮНЯ',
  'ИЮЛЯ',
  'АВГУСТА',
  'СЕНТЯБРЯ',
  'ОКТЯБРЯ',
  'НОЯБРЯ',
  'ДЕКАБРЯ',
] as const;

/** Месяц календаря: год и номер месяца от нуля, как в `Date`. */
export interface CalendarMonth {
  readonly year: number;
  readonly month: number;
}

export function monthName(month: CalendarMonth): string {
  return MONTH_NAMES[month.month] ?? '';
}

export function monthGenitive(month: CalendarMonth): string {
  return MONTH_GENITIVE[month.month] ?? '';
}

/** Сколько дней в месяце. Нулевой день следующего месяца — последний этого. */
export function daysInMonth(month: CalendarMonth): number {
  return new Date(month.year, month.month + 1, 0).getDate();
}

/**
 * Номер дня недели первого числа: 1 — понедельник, 7 — воскресенье.
 *
 * `Date.getDay()` считает от воскресенья, и это самый частый источник сдвига
 * сетки на день, поэтому пересчёт живёт в одном месте.
 */
export function firstWeekdayOf(month: CalendarMonth): number {
  const sundayBased = new Date(month.year, month.month, 1).getDay();
  return sundayBased === 0 ? 7 : sundayBased;
}

/** День недели числа — подпись рядом с крупной цифрой. */
export function weekdayOf(month: CalendarMonth, day: number): string {
  const sundayBased = new Date(month.year, month.month, day).getDay();
  return WEEKDAYS[(sundayBased + 6) % 7] ?? WEEKDAYS[0];
}

/** Месяц, в котором лежит эта дата. */
export function monthOf(date: Date): CalendarMonth {
  return { year: date.getFullYear(), month: date.getMonth() };
}

/** Соседний месяц: `step` в месяцах, со сменой года на границах. */
export function shiftMonth(month: CalendarMonth, step: number): CalendarMonth {
  const shifted = new Date(month.year, month.month + step, 1);
  return monthOf(shifted);
}

/**
 * Дата в виде `YYYY-MM-DD` — в этом виде её ждёт и отдаёт API.
 *
 * Собирается вручную, а не через `toISOString()`: тот переводит в UTC, и для
 * пользователя восточнее Гринвича вечернее событие уезжает на день назад.
 */
export function isoDate(year: number, month: number, day: number): string {
  return `${String(year)}-${pad(month + 1)}-${pad(day)}`;
}

export function isoOf(date: Date): string {
  return isoDate(date.getFullYear(), date.getMonth(), date.getDate());
}

/** Первое и последнее число месяца в формате API — границы запроса событий. */
export function monthRange(month: CalendarMonth): { from: string; to: string } {
  return {
    from: isoDate(month.year, month.month, 1),
    to: isoDate(month.year, month.month, daysInMonth(month)),
  };
}

/** Один и тот же ли это месяц. */
export function sameMonth(a: CalendarMonth, b: CalendarMonth): boolean {
  return a.year === b.year && a.month === b.month;
}

function pad(value: number): string {
  return String(value).padStart(2, '0');
}
