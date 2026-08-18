/**
 * Профориентационный тест (ТЗ 2, блок 1).
 *
 * Прогресс живёт в обычном локальном состоянии экрана и нигде не сохраняется:
 * выход в меню обнуляет тест, при следующем входе он начинается заново
 * (ТЗ 1.3). Это требование, а не недоделка — persist здесь добавлять нельзя.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useQuestions, useSubmitTest } from '@/shared/api/careerTest';
import { Button } from '@/shared/ui/Button';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

/** Пауза между выбором варианта и следующим вопросом (хендофф, экран 3). */
const NEXT_QUESTION_DELAY_MS = 180;

export function CareerTestScreen() {
  const navigate = useNavigate();
  const questions = useQuestions();
  const submit = useSubmitTest();

  const [answers, setAnswers] = useState<number[]>([]);
  const [picked, setPicked] = useState<number | null>(null);

  const items = questions.data ?? [];
  const index = answers.length;
  const current = items[index];

  const choose = (optionId: number) => {
    if (picked !== null || submit.isPending) return;
    setPicked(optionId);

    setTimeout(() => {
      const next = [...answers, optionId];
      setPicked(null);
      if (next.length < items.length) {
        setAnswers(next);
        return;
      }
      submit.mutate(next, {
        onSuccess: (result) => {
          void navigate('/career-test/results', { state: { resultId: result.id } });
        },
        // При ошибке остаёмся на месте: ответы ещё в памяти экрана, и человек
        // может повторить последний шаг, а не проходить тест заново.
        onError: () => {
          setAnswers(answers);
        },
      });
    }, NEXT_QUESTION_DELAY_MS);
  };

  return (
    <>
      <ScreenHeader title="Профориентация" />

      {questions.isPending && <Hint>Загружаю вопросы…</Hint>}

      {questions.isError && (
        <Hint>
          Не удалось загрузить вопросы. Проверьте связь и попробуйте ещё раз — из меню тест
          открывается заново.
        </Hint>
      )}

      {current && (
        <>
          <div className="mt-[26px] flex items-baseline gap-[14px]">
            <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">
              {String(index + 1).padStart(2, '0')}
            </span>
            <span className="text-[11px] font-bold tracking-[0.18em] text-neutral-600">
              ИЗ {items.length}
            </span>
          </div>

          <div
            className="mt-[18px] flex gap-[7px]"
            role="progressbar"
            aria-label="Прогресс теста"
            aria-valuemin={1}
            aria-valuemax={items.length}
            aria-valuenow={index + 1}
          >
            {items.map((question, position) => (
              <span
                key={question.id}
                className={`block h-[5px] flex-1 rounded-full ${
                  position < index ? 'bg-text' : position === index ? 'bg-accent' : 'bg-neutral-400'
                }`}
              />
            ))}
          </div>

          <h1
            // key по вопросу: анимация входа переигрывается на каждом шаге.
            key={current.id}
            className="animate-card-in mt-[22px] font-heading text-[25px] leading-[1.15] tracking-[-0.02em] text-pretty"
          >
            {current.text}
          </h1>

          <div className="mt-5 flex flex-col gap-[10px]">
            {current.options.map((option, position) => (
              <Button
                key={option.id}
                variant={picked === option.id ? 'accent' : 'outline'}
                disabled={picked !== null || submit.isPending}
                onClick={() => {
                  choose(option.id);
                }}
                className="animate-card-in justify-start px-5 py-[17px] text-left text-[15px] leading-[1.35] disabled:opacity-100"
                style={{ animationDelay: `${String(position * 50)}ms` }}
              >
                {option.text}
              </Button>
            ))}
          </div>

          {submit.isError && <Hint>Не удалось отправить ответы. Нажмите вариант ещё раз.</Hint>}

          <p className="mt-[22px] text-[12px] text-neutral-600 text-pretty">
            Выйти можно на любом шаге — прогресс теста не сохраняется, в следующий раз начнём
            заново.
          </p>
        </>
      )}
    </>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700 text-pretty">{children}</p>;
}
