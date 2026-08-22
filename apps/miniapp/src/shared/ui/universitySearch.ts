/**
 * Поиск по справочнику вузов (уточнение У31).
 *
 * Чистые функции без React: их можно прогнать тестами и не гадать, почему в
 * шторке «не то сверху». Справочник маленький и целиком лежит на клиенте,
 * поэтому поиск идёт в памяти — сетевого запроса на каждый символ нет.
 *
 * Что считается совпадением:
 *
 * - подстрока в аббревиатуре, полном названии или городе — «мгу», «политех»,
 *   «владивосток» находят вуз одинаково;
 * - раскладка: «vue,» набранное латиницей, приводится к «мгу» — человек
 *   замечает забытую раскладку позже, чем начинает печатать;
 * - «ё» и «е» не различаются: иначе «Королёв» не находится по «королев».
 *
 * Порядок выдачи важнее самого факта совпадения: при вводе «м» вузов
 * совпадает много, и сверху должен оказаться тот, у кого совпало начало
 * аббревиатуры, а не тот, у кого буква нашлась в середине города.
 */

/** Вуз в том виде, в каком его отдаёт справочник. */
export interface SearchableUniversity {
  readonly short_name: string;
  readonly name: string;
  readonly city: string;
}

/** Раскладка: латинская буква → русская на той же клавише. */
const KEYBOARD: Readonly<Record<string, string>> = {
  q: 'й',
  w: 'ц',
  e: 'у',
  r: 'к',
  t: 'е',
  y: 'н',
  u: 'г',
  i: 'ш',
  o: 'щ',
  p: 'з',
  '[': 'х',
  ']': 'ъ',
  a: 'ф',
  s: 'ы',
  d: 'в',
  f: 'а',
  g: 'п',
  h: 'р',
  j: 'о',
  k: 'л',
  l: 'д',
  ';': 'ж',
  "'": 'э',
  z: 'я',
  x: 'ч',
  c: 'с',
  v: 'м',
  b: 'и',
  n: 'т',
  m: 'ь',
  ',': 'б',
  '.': 'ю',
};

/** Приводит строку к виду, в котором сравнение не зависит от мелочей. */
export function normalise(value: string): string {
  return value.toLowerCase().replaceAll('ё', 'е').trim();
}

/** Та же строка, но с латиницы переложенная на русскую раскладку. */
export function fromLatinLayout(value: string): string {
  return [...value].map((symbol) => KEYBOARD[symbol] ?? symbol).join('');
}

/**
 * Насколько запрос подходит вузу. Больше — выше в списке, ноль — не показывать.
 *
 * Веса подобраны так, чтобы совпадение в аббревиатуре всегда било совпадение в
 * городе: человек ищет вуз, а город — лишь способ его узнать.
 */
export function scoreUniversity(university: SearchableUniversity, query: string): number {
  const needle = normalise(query);
  if (needle === '') return 1;

  const short = normalise(university.short_name);
  const full = normalise(university.name);
  const city = normalise(university.city);

  if (short.startsWith(needle)) return 100;
  if (startsAnyWord(full, needle)) return 80;
  if (short.includes(needle)) return 60;
  if (full.includes(needle)) return 40;
  if (city.startsWith(needle)) return 30;
  if (city.includes(needle)) return 20;
  return 0;
}

/** Совпадение с началом любого слова: «политех» в «Северный политехнический». */
function startsAnyWord(haystack: string, needle: string): boolean {
  return haystack.split(/[\s(),.«»-]+/).some((word) => word.startsWith(needle));
}

/**
 * Отфильтрованный и отсортированный справочник.
 *
 * Пустой запрос отдаёт **весь** список в исходном порядке: шторка обязана
 * показать варианты сразу, ещё до первого символа.
 *
 * При неудаче ищет ещё раз, переложив запрос с латиницы: подсказка «похоже,
 * забыта раскладка» без отдельной кнопки.
 */
export function searchUniversities<T extends SearchableUniversity>(
  universities: readonly T[],
  query: string,
): T[] {
  const found = rank(universities, query);
  if (found.length > 0 || normalise(query) === '') return found;
  return rank(universities, fromLatinLayout(query));
}

function rank<T extends SearchableUniversity>(universities: readonly T[], query: string): T[] {
  return (
    universities
      .map((university, position) => ({
        university,
        score: scoreUniversity(university, query),
        position,
      }))
      .filter((item) => item.score > 0)
      // При равном весе сохраняется порядок справочника: он курируется руками,
      // и алфавит внутри группы был бы хуже, чем задуманный составителем.
      .sort((a, b) => b.score - a.score || a.position - b.position)
      .map((item) => item.university)
  );
}
