/**
 * Лента вопросов вуза (ТЗ 5.6–5.8).
 *
 * Открыта всем (уточнение У15). Отвечать может только привязанный к этому вузу
 * и прошедший верификацию — право приходит из профиля полем
 * `access.answer_questions`, считает его сервер (решение Р19). У остальных
 * поля ответа нет, но лента читается целиком.
 *
 * Подпись автора ответа — только имя (уточнение У16): ни курса, ни отметки
 * «верифицирован», хотя в макете они нарисованы.
 */
import { useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import {
  useAnswer,
  useFeed,
  useToggleLike,
  type FeedAnswer,
  type FeedQuestion,
} from '@/shared/api/mentorQa';
import { useProfile } from '@/shared/api/profile';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

const MIN_TEXT_LENGTH = 10;

export function MentorQaFeedScreen() {
  const { universityId } = useParams();
  const parsed = Number(universityId);
  const id = Number.isInteger(parsed) && parsed > 0 ? parsed : null;

  const profile = useProfile();
  const feed = useFeed(id);

  // Отвечать вправе только студент этого вуза с верификацией (У15, У17).
  const canAnswer =
    profile.data?.access.answer_questions === true && profile.data.university?.id === id;

  return (
    <>
      <ScreenHeader title="Лента вуза" />

      {feed.isPending && <Hint>Загружаю ленту…</Hint>}
      {feed.isError && <Hint>Не удалось загрузить ленту. Проверьте связь.</Hint>}

      {feed.isSuccess && feed.data.items.length === 0 && (
        <>
          <Hint>В этой ленте пока нет вопросов. Задайте первый — он опубликуется анонимно.</Hint>
          <Link
            to="/mentor-qa"
            className={buttonClass('accent', 'mt-4 w-full px-[10px] py-[17px] text-[14px]')}
          >
            Задать вопрос
          </Link>
        </>
      )}

      {feed.data !== undefined && feed.data.items.length > 0 && (
        <div className="mt-5 flex flex-col gap-3">
          {feed.data.items.map((question, position) => (
            <QuestionCard
              key={question.id}
              question={question}
              position={position}
              canAnswer={canAnswer}
            />
          ))}
        </div>
      )}
    </>
  );
}

function QuestionCard({
  question,
  position,
  canAnswer,
}: {
  readonly question: FeedQuestion;
  readonly position: number;
  readonly canAnswer: boolean;
}) {
  const published = question.moderation_status === 'published';

  return (
    <div
      style={{ animationDelay: `${String(position * 50)}ms` }}
      className={`animate-card-in rounded-[30px] px-[22px] py-5 ${
        question.mine && !published
          ? 'border-[1.5px] border-dashed border-neutral-400'
          : 'border-[1.5px] border-neutral-400'
      }`}
    >
      <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
        {question.topic_label.toUpperCase()} · {pluralAnswers(question.answers.length)}
        {question.mine && !published && ' · НА ПРОВЕРКЕ'}
      </div>
      <div className="mt-[6px] font-heading text-[19px] leading-[1.2] tracking-[-0.02em] text-pretty">
        {question.text}
      </div>

      {question.answers.map((answer) => (
        <AnswerRow key={answer.id} answer={answer} />
      ))}

      {published && canAnswer && <AnswerForm questionId={question.id} />}
    </div>
  );
}

function AnswerRow({ answer }: { readonly answer: FeedAnswer }) {
  const like = useToggleLike();

  return (
    <div className="mt-[14px] border-t-[1.5px] border-neutral-300 pt-[14px]">
      <p className="text-[14px] leading-[1.5] text-neutral-700">{answer.text}</p>
      <div className="mt-3 flex items-center justify-between gap-3">
        <span className="flex items-center gap-2 text-[12px] text-neutral-600">
          <span className="flex h-[26px] w-[26px] items-center justify-center rounded-full bg-text font-heading text-[11px] text-neutral-200">
            {answer.author_name.slice(0, 1) || '·'}
          </span>
          {answer.author_name || 'Студент'}
        </span>
        <Button
          variant={answer.liked_by_me ? 'accent' : 'outline'}
          disabled={like.isPending}
          aria-pressed={answer.liked_by_me}
          aria-label={`Лайк ответа, сейчас ${String(answer.likes_count)}`}
          onClick={() => {
            like.mutate(answer.id);
          }}
          className="px-[15px] py-[9px] text-[12px] disabled:opacity-60"
        >
          ♥ {answer.likes_count}
        </Button>
      </div>
    </div>
  );
}

function AnswerForm({ questionId }: { readonly questionId: number }) {
  const answer = useAnswer();
  const [text, setText] = useState('');
  const valid = text.trim().length >= MIN_TEXT_LENGTH;

  return (
    <div className="mt-[14px] border-t-[1.5px] border-neutral-300 pt-[14px]">
      <textarea
        rows={2}
        value={text}
        aria-label="Ваш ответ"
        placeholder="Ответьте по делу — вам за это +25 баллов"
        onChange={(event) => {
          setText(event.target.value);
        }}
        className="w-full resize-none rounded-[22px] border-[1.5px] border-neutral-400 bg-transparent px-4 py-3 text-[14px] leading-[1.45]"
      />
      <Button
        variant="dark"
        disabled={!valid || answer.isPending}
        onClick={() => {
          answer.mutate(
            { questionId, text: text.trim() },
            {
              onSuccess: () => {
                setText('');
              },
            },
          );
        }}
        className="mt-2 w-full px-[10px] py-3 text-[13px] disabled:opacity-60"
      >
        Ответить
      </Button>
      {answer.isError && (
        <p className="mt-2 text-[12px] text-accent-700">Не удалось отправить ответ.</p>
      )}
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

function pluralAnswers(count: number): string {
  const tail = count % 100;
  if (tail >= 11 && tail <= 14) return `${String(count)} ОТВЕТОВ`;
  const last = count % 10;
  if (last === 1) return `${String(count)} ОТВЕТ`;
  if (last >= 2 && last <= 4) return `${String(count)} ОТВЕТА`;
  return `${String(count)} ОТВЕТОВ`;
}
