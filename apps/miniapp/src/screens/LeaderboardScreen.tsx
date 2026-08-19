/**
 * Рейтинг активности (ТЗ 6.1–6.7).
 *
 * Рейтинг один на всю площадку, а не по вузам (уточнение У19): подпись «место
 * в вузе» из макета стала просто «местом», и вуза здесь нет ни в одном поле.
 *
 * Ранжирование — по баллам, набранным за неделю, а не по остатку на счету:
 * иначе обмен баллов выглядел бы наказанием за активность.
 */
import {
  useBuyReward,
  useCheckIn,
  useGamificationMe,
  useLeaderboard,
  type LeaderboardRow,
  type Reward,
} from '@/shared/api/gamification';
import { Button } from '@/shared/ui/Button';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

export function LeaderboardScreen() {
  const me = useGamificationMe();
  const board = useLeaderboard();
  const checkIn = useCheckIn();

  const checkedIn = me.data?.checked_in_today === true || checkIn.data?.granted === true;

  return (
    <>
      <ScreenHeader title="Рейтинг активности" />

      <div className="mt-6 flex items-baseline gap-[14px]">
        <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">
          {me.data?.balance ?? 0}
        </span>
        <span className="text-[11px] leading-[1.3] font-bold tracking-[0.18em] text-neutral-600">
          БАЛЛОВ
          {board.data?.me != null && (
            <>
              <br />
              {board.data.me.place} МЕСТО
            </>
          )}
        </span>
      </div>

      {me.isError && <Hint>Не удалось загрузить баллы. Проверьте связь.</Hint>}

      {me.data?.title?.mine === true && (
        <div className="mt-4 flex items-center gap-3 rounded-[26px] bg-accent px-[18px] py-4">
          <span className="text-[10px] font-bold tracking-[0.14em]">
            {me.data.title.name.toUpperCase()}
          </span>
          <span className="text-[12px]">
            статус месяца ваш — {me.data.title.points} баллов за прошлый месяц
          </span>
        </div>
      )}

      <Button
        variant={checkedIn ? 'outline' : 'accent'}
        disabled={checkedIn || checkIn.isPending}
        onClick={() => {
          checkIn.mutate();
        }}
        className="mt-[18px] w-full justify-start rounded-[26px] px-5 py-4 text-left text-[15px] disabled:opacity-100"
      >
        <span className="flex-1">
          {checkedIn ? 'Чек-ин засчитан сегодня · +10' : 'Ежедневный чек-ин · +10'}
        </span>
      </Button>

      <div className="mt-[22px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        ЗА НЕДЕЛЮ
      </div>

      {board.isPending && <Hint>Считаю рейтинг…</Hint>}
      {board.isSuccess && board.data.rows.length === 0 && (
        <Hint>
          За эту неделю баллов ещё никто не набрал. Отметьтесь чек-ином или ответьте на вопрос — и
          рейтинг появится.
        </Hint>
      )}

      {board.data !== undefined && board.data.rows.length > 0 && (
        <div className="mt-3 flex flex-col gap-[9px]">
          {board.data.rows.map((row) => (
            <Row key={row.place} row={row} toNextPlace={board.data.to_next_place} />
          ))}
          {/* Своя строка снизу, если в первую десятку не попал. */}
          {board.data.me != null &&
            !board.data.rows.some((row) => row.place === board.data.me?.place) && (
              <Row row={board.data.me} toNextPlace={board.data.to_next_place} />
            )}
        </div>
      )}

      <div className="mt-[22px] text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        ОБМЕНЯТЬ БАЛЛЫ
      </div>
      <div className="mt-3 flex flex-col gap-[10px]">
        {(me.data?.rewards ?? []).map((reward) => (
          <RewardRow key={reward.code} reward={reward} balance={me.data?.balance ?? 0} />
        ))}
      </div>
    </>
  );
}

function Row({
  row,
  toNextPlace,
}: {
  readonly row: LeaderboardRow;
  readonly toNextPlace: number | null;
}) {
  // Первое место — тёмная карточка, своя строка — акцентная обводка
  // (макет, экран 14).
  const dark = row.place === 1;

  return (
    <div
      className={`flex items-center gap-[14px] rounded-[26px] px-[18px] py-4 ${
        dark
          ? 'bg-text text-neutral-200'
          : row.mine
            ? 'border-[1.5px] border-accent'
            : 'border-[1.5px] border-neutral-400'
      }`}
    >
      <span className="font-heading text-[22px] tracking-[-0.03em]">{row.place}</span>
      <div className="min-w-0 flex-1">
        <div className="text-[14px]">{row.mine ? 'Вы' : row.display_name || 'Участник'}</div>
        <div className={`text-[11px] ${dark ? 'text-neutral-500' : 'text-neutral-600'}`}>
          {row.points.toLocaleString('ru-RU')} баллов
          {row.mine &&
            toNextPlace !== null &&
            ` · до ${String(row.place - 1)} места ${String(toNextPlace)}`}
        </div>
      </div>
      {row.has_title && (
        <span className="flex-none rounded-full bg-accent px-[11px] py-[6px] text-[10px] font-bold tracking-[0.12em] text-text">
          НАШ ЧЕЛОВЕК
        </span>
      )}
    </div>
  );
}

function RewardRow({ reward, balance }: { readonly reward: Reward; readonly balance: number }) {
  const buy = useBuyReward();
  const notEnough = buy.data?.not_enough === true || (!reward.owned && balance < reward.price);
  const owned = reward.owned || buy.data?.bought === true;

  return (
    <>
      <Button
        variant={owned ? 'accent' : 'outline'}
        disabled={owned || buy.isPending}
        onClick={() => {
          buy.mutate(reward.code);
        }}
        className="w-full justify-start rounded-[26px] px-[18px] py-4 text-left text-[15px] disabled:opacity-100"
      >
        <span className="flex-1">{owned ? `${reward.title} · активировано` : reward.title}</span>
        <span className="font-heading text-[18px]">{reward.price}</span>
      </Button>
      {!owned && notEnough && (
        <p className="text-[12px] text-accent-700">
          Не хватает баллов: нужно ещё {reward.price - balance}
        </p>
      )}
    </>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-4 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}
