/**
 * Шторка снизу — сквозной элемент макета.
 *
 * Один компонент на всё приложение: в макете шторкой открываются события дня,
 * выбор вуза, выбор группы, список вакансий и добавление дедлайна. Внешний вид
 * у всех один, меняется только содержимое.
 *
 * Построена на Radix Dialog (тех. ТЗ 8.8): доступность из коробки — фокус
 * запирается внутри, Esc закрывает, фон получает `aria-hidden`. Своими руками
 * это пишется долго и всё равно хуже.
 */
import * as Dialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

interface SheetProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  /** Caps-заголовок шторки. Он же — доступное имя диалога. */
  readonly title: string;
  readonly children: ReactNode;
}

export function Sheet({ open, onOpenChange, title, children }: SheetProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        {/* Затемнение и панель позиционируются внутри корпуса приложения:
            `fixed` растянул бы их на весь экран десктопа, мимо рамки макета. */}
        <Dialog.Overlay className="fixed inset-0 z-40 flex items-center justify-center">
          <div className="relative h-[min(100dvh,940px)] w-[440px] max-w-[100vw] overflow-hidden rounded-[46px] max-[520px]:h-[100dvh] max-[520px]:w-[100vw] max-[520px]:rounded-none">
            <div className="absolute inset-0 bg-text/45" />
          </div>
        </Dialog.Overlay>
        <div className="pointer-events-none fixed inset-0 z-50 flex items-center justify-center">
          <div className="relative h-[min(100dvh,940px)] w-[440px] max-w-[100vw] overflow-hidden rounded-[46px] max-[520px]:h-[100dvh] max-[520px]:w-[100vw] max-[520px]:rounded-none">
            <Dialog.Content
              aria-describedby={undefined}
              className="animate-sheet-in pointer-events-auto absolute inset-x-0 bottom-0 flex max-h-[74%] flex-col rounded-t-[42px] bg-neutral-200 px-[22px] pt-[18px] pb-[26px] shadow-sheet"
            >
              {/* Ручка — декоративная: закрывают шторку по фону, Esc или кнопке. */}
              <div
                aria-hidden
                className="h-[5px] w-[46px] flex-none self-center rounded-full bg-neutral-400"
              />
              <Dialog.Title className="mt-4 flex-none text-[10px] font-bold tracking-[0.18em] text-neutral-600 uppercase">
                {title}
              </Dialog.Title>
              <div className="mt-3 flex min-h-0 flex-1 flex-col gap-[9px] overflow-y-auto [scrollbar-width:none] [&::-webkit-scrollbar]:hidden">
                {children}
              </div>
              <Dialog.Close className="sr-only">Закрыть</Dialog.Close>
            </Dialog.Content>
          </div>
        </div>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
