/**
 * Кнопка ленты уведомлений в нижней панели со счётчиком-бейджем.
 *
 * Уточнение У25: уведомления копятся в базе и показываются внутри приложения.
 * Лента открывается шторкой — тем же сквозным элементом, что и остальные
 * списки макета, чтобы не заводить семнадцатый экран ради неё.
 */
import { useState } from 'react';

import { useMarkRead, useNotifications, type Notification } from '@/shared/api/notifications';
import { BellIcon } from '@/shared/ui/icons';
import { Sheet } from '@/shared/ui/Sheet';

export function NotificationsButton() {
  const notifications = useNotifications();
  const [open, setOpen] = useState(false);

  const unread = notifications.data?.unread ?? 0;
  const items = notifications.data?.items ?? [];

  return (
    <>
      <button
        type="button"
        aria-label={unread > 0 ? `Уведомления, непрочитанных ${String(unread)}` : 'Уведомления'}
        onClick={() => {
          setOpen(true);
        }}
        className="relative flex h-[54px] w-[54px] flex-none items-center justify-center rounded-full border-[1.5px] border-neutral-400 text-text transition-colors hover:bg-text/6"
      >
        <BellIcon size={20} />
        {unread > 0 && (
          <span className="absolute top-[6px] right-[6px] flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-accent px-[5px] text-[10px] font-bold">
            {unread > 9 ? '9+' : unread}
          </span>
        )}
      </button>

      <Sheet open={open} onOpenChange={setOpen} title="Уведомления">
        {notifications.isPending && <SheetHint>Загружаю…</SheetHint>}
        {notifications.isError && <SheetHint>Не удалось загрузить уведомления.</SheetHint>}
        {notifications.isSuccess && items.length === 0 && (
          <SheetHint>
            Пока тихо. Сюда придут напоминания о приёме документов, дедлайнах и ответах на ваши
            вопросы.
          </SheetHint>
        )}
        {items.map((item) => (
          <NotificationRow key={item.id} notification={item} />
        ))}
      </Sheet>
    </>
  );
}

function NotificationRow({ notification }: { readonly notification: Notification }) {
  const markRead = useMarkRead();
  const unread = notification.read_at === null;

  return (
    <button
      type="button"
      disabled={!unread || markRead.isPending}
      onClick={() => {
        markRead.mutate(notification.id);
      }}
      className={`flex-none rounded-3xl px-5 py-4 text-left transition-colors disabled:cursor-default ${
        unread ? 'border-[1.5px] border-accent' : 'border-[1.5px] border-neutral-400'
      }`}
    >
      <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">
        {notification.kind_label.toUpperCase()}
      </div>
      <div className="mt-1 text-[15px]">{notification.title}</div>
      <p className="mt-1 text-[13px] leading-[1.45] text-neutral-700">{notification.body}</p>
    </button>
  );
}

function SheetHint({ children }: { readonly children: React.ReactNode }) {
  return <p className="flex-none text-[13px] leading-[1.45] text-neutral-700">{children}</p>;
}
