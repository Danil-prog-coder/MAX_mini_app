/**
 * Кнопка-пилюля дизайн-системы Organic.
 *
 * Компонент, а не набор классов в каждом экране: иначе hover, pressed и
 * disabled разъедутся между блоками, а их в макете ровно по одному варианту.
 * Классы живут рядом, в `buttonStyles`, — их разделяет со ссылками-кнопками.
 */
import type { ButtonHTMLAttributes, ReactNode } from 'react';

import { buttonClass, type ButtonVariant } from './buttonStyles';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  readonly variant?: ButtonVariant;
  readonly children: ReactNode;
}

export function Button({
  variant = 'outline',
  className = '',
  type = 'button',
  children,
  ...rest
}: ButtonProps) {
  return (
    <button
      // Тип задаётся явно: кнопка внутри формы по умолчанию отправляет её.
      type={type}
      className={buttonClass(variant, className)}
      {...rest}
    >
      {children}
    </button>
  );
}
