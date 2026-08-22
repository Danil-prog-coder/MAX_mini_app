/**
 * Тесты содержимого календаря.
 *
 * Проверяется не вёрстка, а перенос макета: сетка дней недели и выбор набора
 * событий по статусу. Ошибка здесь незаметна глазом — точки просто встанут на
 * день влево, — поэтому она ловится тестом, а не приёмкой.
 */
import { describe, expect, it } from 'vitest';

import {
  CURRENT_MONTH_INDEX,
  MONTHS,
  TODAY,
  emptyDayNote,
  eventsOf,
  monthAt,
  weekdayOf,
} from './menuCalendarContent';

describe('сетка месяца', () => {
  it('первое число попадает на день недели из макета', () => {
    // Июль 2026 начинается в среду: `first: 3` в макете.
    expect(weekdayOf(monthAt(1), 1)).toBe('Ср');
    expect(weekdayOf(monthAt(0), 1)).toBe('Пн');
    expect(weekdayOf(monthAt(2), 1)).toBe('Сб');
  });

  it('сегодняшнее число — понедельник, как в шапке макета', () => {
    expect(weekdayOf(monthAt(CURRENT_MONTH_INDEX), TODAY)).toBe('Пн');
  });

  it('неделя закольцована: восьмой день повторяет день недели первого', () => {
    const month = monthAt(CURRENT_MONTH_INDEX);
    expect(weekdayOf(month, 8)).toBe(weekdayOf(month, 1));
  });

  it('индекс за границами не роняет календарь', () => {
    expect(monthAt(-1)).toBe(MONTHS[CURRENT_MONTH_INDEX]);
    expect(monthAt(MONTHS.length)).toBe(MONTHS[CURRENT_MONTH_INDEX]);
  });
});

describe('события дня', () => {
  it('у студента и абитуриента разные события в один и тот же день', () => {
    const applicant = eventsOf(false, CURRENT_MONTH_INDEX, TODAY);
    const student = eventsOf(true, CURRENT_MONTH_INDEX, TODAY);

    expect(applicant[0]?.title).toBe('Приём документов идёт');
    expect(student[0]?.title).toBe('4 пары · с 09:00');
  });

  it('день без событий отдаёт пустой список, а не undefined', () => {
    expect(eventsOf(false, CURRENT_MONTH_INDEX, 2)).toEqual([]);
    expect(eventsOf(true, CURRENT_MONTH_INDEX, 2)).toEqual([]);
  });

  it('текст пустого дня зависит от статуса', () => {
    expect(emptyDayNote(true)).toContain('Ни пар, ни дедлайнов');
    expect(emptyDayNote(false)).toContain('приёмной кампании');
  });
});
