/**
 * Поддержка и предложения (ТЗ 8.1–8.7).
 *
 * Смысл блока — снять ощущение «сообщение ушло в пустоту»: отписка приходит
 * сразу (ТЗ 8.4), а история обращений с ответами поддержки видна тут же
 * (ТЗ 8.6).
 *
 * Отписку выбирает сервер из заготовленного пула, а не экран: иначе текст
 * менялся бы при каждом рендере, и обещание «ответ придёт сюда» выглядело бы
 * фальшивым.
 */
import { useState } from 'react';

import {
  useCategories,
  useSendTicket,
  useTickets,
  type CreatedTicket,
  type Ticket,
  type TicketCategory,
} from '@/shared/api/support';
import { Button } from '@/shared/ui/Button';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

/** Минимум из схемы сервера. */
const MIN_TEXT_LENGTH = 5;

export function SupportScreen() {
  const categories = useCategories();
  const tickets = useTickets();
  const send = useSendTicket();

  const [category, setCategory] = useState<TicketCategory>('bug');
  const [text, setText] = useState('');
  const [sent, setSent] = useState<CreatedTicket | null>(null);

  const valid = text.trim().length >= MIN_TEXT_LENGTH;
  // Свежая отписка показывается поверх истории: она и есть ответ на действие.
  const earlier = (tickets.data?.items ?? []).filter((item) => item.id !== sent?.ticket.id);

  return (
    <>
      <ScreenHeader title="Поддержка" />

      <h1 className="mt-[26px] font-heading text-[52px] leading-[0.98] tracking-[-0.045em]">
        Что случилось?
      </h1>

      <div className="mt-[22px] flex flex-wrap gap-2">
        {(categories.data ?? []).map((item) => (
          <Button
            key={item.code}
            variant={item.code === category ? 'dark' : 'outline'}
            aria-pressed={item.code === category}
            onClick={() => {
              setCategory(item.code);
            }}
            className="px-5 py-[13px] text-[14px]"
          >
            {item.label}
          </Button>
        ))}
      </div>

      <textarea
        rows={5}
        value={text}
        aria-label="Текст обращения"
        placeholder="Опишите свободной формой — чем подробнее, тем быстрее разберёмся"
        onChange={(event) => {
          setText(event.target.value);
        }}
        className={`mt-3 w-full resize-none rounded-[26px] border-[1.5px] bg-transparent px-5 py-[18px] text-[15px] leading-[1.45] ${
          send.isError ? 'border-accent' : 'border-neutral-400'
        }`}
      />

      <Button
        variant="dark"
        disabled={!valid || send.isPending}
        onClick={() => {
          send.mutate(
            { category, text: text.trim() },
            {
              onSuccess: (result) => {
                setSent(result);
                setText('');
              },
            },
          );
        }}
        className="mt-3 w-full px-[10px] py-[17px] text-[14px] disabled:opacity-60"
      >
        Отправить
      </Button>

      {send.isError && <Hint>Не удалось отправить обращение. Попробуйте ещё раз.</Hint>}

      {sent !== null && (
        <div className="animate-card-in mt-4 rounded-[30px] bg-text px-[22px] py-5 text-neutral-200">
          <div className="text-[10px] font-bold tracking-[0.18em] text-accent-300">
            {sent.sender.toUpperCase()}
          </div>
          <p className="mt-2 text-[15px] leading-[1.45]">{sent.reply}</p>
        </div>
      )}

      {earlier.length > 0 && (
        <>
          <div className="mt-[22px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
            ВАШИ ОБРАЩЕНИЯ
          </div>
          <div className="mt-3 flex flex-col gap-[10px]">
            {earlier.map((ticket) => (
              <TicketCard key={ticket.id} ticket={ticket} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function TicketCard({ ticket }: { readonly ticket: Ticket }) {
  return (
    <div className="rounded-[28px] border-[1.5px] border-neutral-400 px-5 py-4">
      <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
        {ticket.category_label.toUpperCase()}
      </div>
      <p className="mt-2 text-[14px] leading-[1.45]">{ticket.text}</p>

      <div className="mt-3 border-t-[1.5px] border-neutral-300 pt-3">
        <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
          {ticket.sender.toUpperCase()}
        </div>
        {/* Пока администратор не ответил, видна типовая отписка — она и была
            ответом на отправку (ТЗ 8.4). */}
        <p className="mt-1 text-[13px] leading-[1.45] text-neutral-700">
          {ticket.admin_reply ?? ticket.auto_reply}
        </p>
      </div>
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}
