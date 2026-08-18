/**
 * Где покушать (ТЗ 7.1–7.7).
 *
 * Раздел закрыт статусом: сервер отвечает 403, пока в профиле нет статуса
 * «Студент» и вуза, и экран уводит на гейт — маршрут, а не отказ (ТЗ 7.2).
 *
 * У магазина и общепита разные карточки (ТЗ 7.5): у первого выпечка и
 * ассортимент, у второго — что готовят и оценка.
 */
import { Navigate } from 'react-router-dom';

import { CLOSED, useNearby, type Nearby, type Spot } from '@/shared/api/food';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';

/** Точек в шкале близости — пять, как в макете. */
const DISTANCE_DOTS = 5;

export function FoodScreen() {
  const nearby = useNearby();
  const data = nearby.data;

  if (data === CLOSED) {
    return <Navigate to="/gate/food" replace />;
  }

  const found: Nearby | undefined = data;

  return (
    <>
      <ScreenHeader title="Где покушать" />

      {nearby.isPending && <Hint>Ищу точки рядом…</Hint>}
      {nearby.isError && <Hint>Не удалось загрузить точки питания. Проверьте связь.</Hint>}

      {found !== undefined && (
        <>
          <div className="mt-6 flex items-baseline gap-[14px]">
            <span className="font-heading text-[118px] leading-[0.9] tracking-[-0.055em]">
              {found.total}
            </span>
            <span className="text-[11px] leading-[1.3] font-bold tracking-[0.18em] text-neutral-600">
              ТОЧЕК
              <br />В ПЕШЕЙ ДОСТУПНОСТИ
            </span>
          </div>
          <p className="mt-1 text-[12px] text-neutral-600">
            от корпуса: {found.university_address}
          </p>

          {found.demo && (
            <p className="mt-2 text-[12px] text-neutral-600">
              Названия и оценки точек демонстрационные: ключа к картам пока нет. Адрес и координаты
              корпуса — настоящие.
            </p>
          )}

          <div className="mt-5 flex flex-col gap-[10px]">
            {found.items.map((spot, position) => (
              <SpotCard key={spot.id} spot={spot} dark={position === 0} position={position} />
            ))}
          </div>
        </>
      )}
    </>
  );
}

function SpotCard({
  spot,
  dark,
  position,
}: {
  readonly spot: Spot;
  readonly dark: boolean;
  readonly position: number;
}) {
  return (
    <div
      style={{ animationDelay: `${String(position * 55)}ms` }}
      className={`animate-card-in rounded-[30px] px-[22px] py-5 ${
        dark ? 'bg-text text-neutral-200' : 'border-[1.5px] border-neutral-400'
      }`}
    >
      <div className="flex items-center justify-between gap-3">
        <span
          className={`text-[10px] font-bold tracking-[0.18em] ${
            dark ? 'text-accent-300' : 'text-neutral-600'
          }`}
        >
          {spot.place_type.toUpperCase()}
          {spot.rating !== null && ` · ${spot.rating.toFixed(1)}`}
        </span>
        <span className={`text-[11px] ${dark ? 'text-neutral-500' : 'text-neutral-600'}`}>
          {spot.walk_minutes} мин пешком
        </span>
      </div>

      <div className="mt-[6px] font-heading text-[24px] leading-[1.1] tracking-[-0.03em]">
        {spot.name}
      </div>

      {spot.kind === 'catering' && spot.menu !== null && (
        <p className={`mt-2 text-[13px] ${dark ? 'text-neutral-400' : 'text-neutral-700'}`}>
          {spot.menu}
        </p>
      )}

      {spot.kind === 'shop' && (
        <div className="mt-3 flex flex-wrap gap-2">
          <span
            className={`rounded-full px-[13px] py-[7px] text-[11px] ${
              spot.has_bakery === true
                ? 'bg-accent-200 text-text'
                : 'border-[1.5px] border-neutral-400'
            }`}
          >
            {spot.has_bakery === true ? 'Выпечка есть' : 'Выпечки нет'}
          </span>
          {spot.assortment !== null && (
            <span className="rounded-full border-[1.5px] border-neutral-400 px-[13px] py-[7px] text-[11px]">
              Ассортимент {spot.assortment}
            </span>
          )}
        </div>
      )}

      <div
        className="mt-3 flex items-center gap-[5px]"
        aria-label={`Близость ${String(spot.distance_score)} из 5`}
      >
        {Array.from({ length: DISTANCE_DOTS }, (_, index) => (
          <span
            key={index}
            aria-hidden="true"
            className={`block h-[9px] w-[9px] rounded-full ${
              index < spot.distance_score
                ? 'bg-accent'
                : dark
                  ? 'bg-neutral-200/25'
                  : 'bg-neutral-400'
            }`}
          />
        ))}
      </div>

      <p className={`mt-3 text-[12px] ${dark ? 'text-neutral-500' : 'text-neutral-600'}`}>
        {spot.address}
      </p>

      {/* ТЗ 7.6: ссылка ведёт на карточку места, а не на общий поиск. */}
      <a
        href={spot.map_deeplink}
        target="_blank"
        rel="noreferrer"
        className={`mt-3 inline-flex items-center rounded-full px-4 py-[10px] text-[12px] transition-colors ${
          dark
            ? 'border-[1.5px] border-neutral-200/30 hover:bg-neutral-200/12'
            : 'border-[1.5px] border-neutral-400 hover:bg-text/6'
        }`}
      >
        Открыть на карте
      </a>
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}
