/**
 * Классы кнопок дизайн-системы Organic.
 *
 * Отдельным модулем от компонента: переход на другой адрес — это ссылка
 * (решение Р32), но выглядит она в макете как кнопка, и классы у них должны
 * быть общими. Держать их в файле с компонентом мешает горячей перезагрузке.
 *
 * Четыре вида взяты из макета и повторяются на каждом экране: `accent` —
 * главное действие, `dark` — второе по значимости, `outline` — обычное,
 * `ghostOnDark` — обводка поверх тёмной карточки.
 */

export type ButtonVariant = 'accent' | 'dark' | 'outline' | 'ghostOnDark';

const BASE =
  'flex items-center justify-center gap-[10px] rounded-full text-center transition-colors disabled:cursor-not-allowed';

const VARIANTS: Record<ButtonVariant, string> = {
  accent: 'bg-accent text-text hover:bg-accent-400 active:bg-accent-700',
  dark: 'bg-text text-neutral-200 hover:bg-neutral-800',
  outline: 'border-[1.5px] border-neutral-400 text-text hover:bg-text/6 active:bg-text/12',
  ghostOnDark: 'border-[1.5px] border-neutral-200/30 text-neutral-200 hover:bg-neutral-200/12',
};

export function buttonClass(variant: ButtonVariant, extra = ''): string {
  return `${BASE} ${VARIANTS[variant]} ${extra}`;
}
