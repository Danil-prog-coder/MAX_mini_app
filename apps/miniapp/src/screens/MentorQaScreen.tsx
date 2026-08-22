/**
 * Спроси у старшекурсника — форма вопроса (ТЗ 5.1–5.5).
 *
 * Спросить может кто угодно и в ленту любого вуза (уточнение У15): в этом весь
 * смысл блока для абитуриента, поэтому гейта здесь нет. Вуз по умолчанию — из
 * профиля, но его можно сменить (ТЗ 5.3).
 *
 * Вопрос публикуется анонимно (ТЗ 5.5) и проходит модерацию (уточнение У18):
 * экран честно показывает все три исхода, а не делает вид, что вопрос уже в
 * ленте.
 */
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAsk, useTopics, type Asked, type QuestionTopic } from '@/shared/api/mentorQa';
import { useProfile, useUniversities } from '@/shared/api/profile';
import { Button } from '@/shared/ui/Button';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';
import { UniversityPicker } from '@/shared/ui/UniversityPicker';

/** Минимум из схемы сервера: короче — не вопрос, а обрывок. */
const MIN_TEXT_LENGTH = 10;

export function MentorQaScreen() {
  const navigate = useNavigate();
  const profile = useProfile();
  const topics = useTopics();
  const ask = useAsk();

  const [topic, setTopic] = useState<QuestionTopic>('admission');
  const [text, setText] = useState('');
  const [universityId, setUniversityId] = useState<number | null>(null);
  const [picking, setPicking] = useState(false);
  const [asked, setAsked] = useState<Asked | null>(null);

  const universities = useUniversities();
  const chosenId = universityId ?? profile.data?.university?.id ?? null;
  const chosen =
    universities.data?.find((item) => item.id === chosenId) ?? profile.data?.university ?? null;

  const valid = text.trim().length >= MIN_TEXT_LENGTH && chosenId !== null;

  return (
    <>
      <ScreenHeader title="Спроси у старшекурсника" />

      <h1 className="mt-[26px] font-heading text-[52px] leading-[0.98] tracking-[-0.045em]">
        Анонимно
        <br />и по делу
      </h1>

      <div className="mt-[22px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        ТЕМА ВОПРОСА
      </div>
      <div className="mt-3 flex flex-wrap gap-2">
        {(topics.data ?? []).map((item) => (
          <Button
            key={item.code}
            variant={item.code === topic ? 'dark' : 'outline'}
            aria-pressed={item.code === topic}
            onClick={() => {
              setTopic(item.code);
            }}
            className="px-5 py-[13px] text-[14px]"
          >
            {item.label}
          </Button>
        ))}
      </div>

      <div className="mt-5 flex items-center gap-3 rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-[15px]">
        <div className="min-w-0 flex-1">
          <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
            {universityId === null ? 'ВУЗ ИЗ ПРОФИЛЯ' : 'ВУЗ ВОПРОСА'}
          </div>
          <div className="mt-[3px] text-[15px]">{chosen?.short_name ?? 'Не выбран'}</div>
        </div>
        <Button
          variant="outline"
          className="flex-none px-4 py-[10px] text-[12px]"
          onClick={() => {
            setPicking(true);
          }}
        >
          Другой
        </Button>
      </div>

      <textarea
        rows={4}
        value={text}
        aria-label="Текст вопроса"
        placeholder="Например: реально ли совмещать первый курс и подработку?"
        onChange={(event) => {
          setText(event.target.value);
        }}
        className={`mt-3 w-full resize-none rounded-[26px] border-[1.5px] bg-transparent px-5 py-[18px] text-[15px] leading-[1.45] ${
          ask.isError ? 'border-accent' : 'border-neutral-400'
        }`}
      />

      <Button
        variant="dark"
        disabled={!valid || ask.isPending}
        onClick={() => {
          if (chosenId === null) return;
          ask.mutate(
            { universityId: chosenId, topic, text: text.trim() },
            {
              onSuccess: (result) => {
                setAsked(result);
                setText('');
              },
            },
          );
        }}
        className="mt-3 w-full px-[10px] py-[17px] text-[14px] disabled:opacity-60"
      >
        Опубликовать анонимно
      </Button>

      {chosenId === null && (
        <Hint>
          Выберите вуз кнопкой «Другой» — вопрос попадёт в его ленту. В профиле вуз не указан, и
          угадывать его за вас неправильно.
        </Hint>
      )}

      {ask.isError && <Hint>Не удалось отправить вопрос. Попробуйте ещё раз.</Hint>}

      {asked !== null && <AskedNotice asked={asked} />}

      <div className="mt-[22px] flex items-center justify-between gap-3">
        <span className="text-[11px] font-bold tracking-[0.2em] text-neutral-600">ЛЕНТА ВУЗА</span>
        <Button
          variant="outline"
          disabled={chosenId === null}
          className="px-4 py-[10px] text-[12px] disabled:opacity-60"
          onClick={() => {
            if (chosenId !== null) void navigate(`/mentor-qa/${String(chosenId)}`);
          }}
        >
          Смотреть все
        </Button>
      </div>

      <UniversityPicker
        open={picking}
        onClose={() => {
          setPicking(false);
        }}
        title="Лента какого вуза"
        selected={chosenId}
        onSelect={(university) => {
          setUniversityId(university.id);
          setPicking(false);
        }}
      />
    </>
  );
}

/**
 * Что стало с отправленным вопросом (уточнение У18).
 *
 * Три исхода показываются как есть: делать вид, что отклонённый вопрос попал в
 * ленту, — значит обмануть человека, который потом его там не найдёт.
 */
function AskedNotice({ asked }: { readonly asked: Asked }) {
  if (asked.published) {
    return (
      <div className="animate-card-in mt-4 rounded-[28px] bg-accent-200 px-5 py-[18px]">
        <div className="text-[10px] font-bold tracking-[0.18em] text-accent-700">
          ВАШ ВОПРОС ОПУБЛИКОВАН
        </div>
        <p className="mt-2 text-[12px] text-neutral-700">Пришлю уведомление, как только ответят</p>
      </div>
    );
  }

  if (asked.moderation_status === 'rejected') {
    return (
      <div className="animate-card-in mt-4 rounded-[28px] border-[1.5px] border-accent px-5 py-[18px]">
        <div className="text-[10px] font-bold tracking-[0.18em] text-accent-700">
          ВОПРОС НЕ ОПУБЛИКОВАН
        </div>
        <p className="mt-2 text-[13px] leading-[1.45] text-neutral-700">
          {asked.moderation_reason || 'Текст нарушает правила ленты.'} Переформулируйте и попробуйте
          ещё раз.
        </p>
      </div>
    );
  }

  return (
    <div className="animate-card-in mt-4 rounded-[28px] border-[1.5px] border-neutral-400 px-5 py-[18px]">
      <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
        ВОПРОС НА ПРОВЕРКЕ
      </div>
      <p className="mt-2 text-[13px] leading-[1.45] text-neutral-700">
        Его посмотрит живой модератор — обычно это недолго. Как только вопрос появится в ленте,
        пришлю уведомление.
      </p>
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}
