/**
 * Заглушка экрана на время сборки оболочки.
 *
 * Оболочка фронта закрывает навигацию и тему, а содержимое экранов приходит
 * вертикальными срезами: домен, эндпоинты и экран одного блока вместе
 * (PLAN.md, шаг 6). До этого экран честно говорит, что он ещё пустой, — это
 * лучше, чем недоделанная вёрстка, которую следующая сессия примет за готовую.
 *
 * Компонент временный и исчезнет вместе с последней заглушкой.
 */
import { ScreenHeader } from './ScreenHeader';

interface ScreenStubProps {
  readonly title: string;
  /** Что здесь появится и по какому пункту ТЗ. */
  readonly note: string;
}

export function ScreenStub({ title, note }: ScreenStubProps) {
  return (
    <>
      <ScreenHeader title={title} />
      <h1 className="mt-6 font-heading text-[40px] leading-[1.05] tracking-[-0.04em]">{title}</h1>
      <div className="mt-5 rounded-[26px] border-[1.5px] border-dashed border-neutral-400 p-5">
        <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600 uppercase">
          Экран ещё не собран
        </div>
        <p className="mt-2 text-[14px] leading-[1.5] text-neutral-700">{note}</p>
      </div>
    </>
  );
}
