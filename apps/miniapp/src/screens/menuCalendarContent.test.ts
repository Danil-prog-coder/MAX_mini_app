/**
 * Тесты разметки календаря (уточнение У32).
 *
 * Даты — самое коварное место экрана: ошибка не видна глазом, сетка просто
 * встаёт на день левее, и события оказываются не в тех клетках. Поэтому
 * проверяются граничные случаи, а не «работает вообще».
 */
import { describe, expect, it } from 'vitest';

import {
  daysInMonth,
  firstWeekdayOf,
  isoDate,
  isoOf,
  monthGenitive,
  monthName,
  monthOf,
  monthRange,
  sameMonth,
  shiftMonth,
  weekdayOf,
} from './menuCalendarContent';

/** Месяцы в `Date` считаются от нуля: 7 — август. */
const AUGUST_2026 = { year: 2026, month: 7 };

describe('сетка месяца', () => {
  it('первое число попадает на правильный день недели', () => {
    // 1 августа 2026 — суббота, шестая колонка.
    expect(firstWeekdayOf(AUGUST_2026)).toBe(6);
    // 1 января 2026 — четверг.
    expect(firstWeekdayOf({ year: 2026, month: 0 })).toBe(4);
    // 1 марта 2026 — воскресенье: это седьмая колонка, а не нулевая.
    expect(firstWeekdayOf({ year: 2026, month: 2 })).toBe(7);
  });

  it('знает длину месяца, включая февраль високосного года', () => {
    expect(daysInMonth(AUGUST_2026)).toBe(31);
    expect(daysInMonth({ year: 2026, month: 3 })).toBe(30);
    expect(daysInMonth({ year: 2026, month: 1 })).toBe(28);
    expect(daysInMonth({ year: 2028, month: 1 })).toBe(29);
  });

  it('день недели числа совпадает с календарём', () => {
    expect(weekdayOf(AUGUST_2026, 1)).toBe('Сб');
    expect(weekdayOf(AUGUST_2026, 3)).toBe('Пн');
    expect(weekdayOf(AUGUST_2026, 9)).toBe('Вс');
  });

  it('листание переходит через границу года', () => {
    expect(shiftMonth({ year: 2026, month: 11 }, 1)).toEqual({ year: 2027, month: 0 });
    expect(shiftMonth({ year: 2026, month: 0 }, -1)).toEqual({ year: 2025, month: 11 });
  });

  it('различает месяцы одного номера в разных годах', () => {
    expect(sameMonth(AUGUST_2026, { year: 2026, month: 7 })).toBe(true);
    expect(sameMonth(AUGUST_2026, { year: 2027, month: 7 })).toBe(false);
  });
});

describe('даты для API', () => {
  it('дописывает ведущие нули', () => {
    expect(isoDate(2026, 0, 5)).toBe('2026-01-05');
    expect(isoDate(2026, 11, 31)).toBe('2026-12-31');
  });

  it('берёт местную дату, а не UTC', () => {
    // Вечер по местному времени — самый частый случай, когда toISOString()
    // отдаёт вчерашний день и событие уезжает в соседнюю клетку.
    const evening = new Date(2026, 7, 25, 23, 30);

    expect(isoOf(evening)).toBe('2026-08-25');
    expect(monthOf(evening)).toEqual(AUGUST_2026);
  });

  it('период месяца — от первого числа до последнего', () => {
    expect(monthRange(AUGUST_2026)).toEqual({ from: '2026-08-01', to: '2026-08-31' });
    expect(monthRange({ year: 2028, month: 1 })).toEqual({
      from: '2028-02-01',
      to: '2028-02-29',
    });
  });
});

describe('названия месяцев', () => {
  it('в шапке именительный, в заголовке дня родительный', () => {
    expect(monthName(AUGUST_2026)).toBe('АВГУСТ');
    expect(monthGenitive(AUGUST_2026)).toBe('АВГУСТА');
    expect(monthName({ year: 2026, month: 4 })).toBe('МАЙ');
    expect(monthGenitive({ year: 2026, month: 4 })).toBe('МАЯ');
  });
});
