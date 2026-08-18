/**
 * Иконки Lucide, перенесённые из прототипа как inline-SVG.
 *
 * Библиотека иконок не подключается: в макете их считанные штуки (хендофф,
 * «Иконки»), а внутри WebView мини-приложения каждый лишний килобайт — это
 * задержка первого экрана на медленной сети (тех. ТЗ 8.5).
 *
 * Толщина штриха 2.75 и `currentColor` — из дизайн-системы: цвет иконка берёт
 * у родителя, поэтому тёмная и светлая кнопки используют одну и ту же.
 */

/**
 * Иконки декоративны: смысл несёт подпись или `aria-label` рядом, поэтому все
 * они помечены `aria-hidden` и в дерево доступности не попадают.
 */
interface IconProps {
  readonly size?: number;
  readonly className?: string;
}

function svgProps(size: number) {
  return {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 2.75,
    strokeLinecap: 'round',
    strokeLinejoin: 'round',
    'aria-hidden': true,
    focusable: false,
  } as const;
}

export function HomeIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1z" />
    </svg>
  );
}

export function UserIcon({ size = 20, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
      <circle cx="12" cy="7" r="4" />
    </svg>
  );
}

export function ChevronLeftIcon({ size = 18, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M15 18l-6-6 6-6" />
    </svg>
  );
}

export function ChevronRightIcon({ size = 17, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M9 6l6 6-6 6" />
    </svg>
  );
}

export function ArrowUpIcon({ size = 15, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M12 19V5M5 12l7-7 7 7" />
    </svg>
  );
}

export function BellIcon({ size = 17, className }: IconProps) {
  return (
    <svg {...svgProps(size)} className={className}>
      <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9" />
      <path d="M13.7 21a2 2 0 0 1-3.4 0" />
    </svg>
  );
}
