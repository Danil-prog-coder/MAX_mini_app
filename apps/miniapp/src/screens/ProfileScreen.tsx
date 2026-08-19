/**
 * Мой профиль — единственный источник правды о пользователе (ТЗ 1.3, 3).
 *
 * Статус, вуз и группа меняются здесь и больше нигде не хранятся: остальные
 * блоки их только читают. Права доступа считает сервер и отдаёт в поле
 * `access` — экран его показывает, но не выводит сам (решение Р19).
 *
 * Верификация — осознанная заглушка (уточнение У7): кнопка переводит профиль в
 * подтверждённое состояние, но реальной проверки учебной почты за ней нет,
 * и текст этого не обещает.
 */
import { useState } from 'react';
import { Link } from 'react-router-dom';

import { useLatestResult } from '@/shared/api/careerTest';
import {
  useNotificationSettings,
  useUpdateNotificationSettings,
  type NotificationKind,
} from '@/shared/api/notifications';
import {
  STATUS_LABELS,
  useConfirmVerification,
  useProfile,
  useUniversities,
  useUpdateProfile,
  type Profile,
  type UserStatus,
} from '@/shared/api/profile';
import { useGroups, useBindGroup } from '@/shared/api/schedule';
import { useTracked } from '@/shared/api/tracker';
import { Button } from '@/shared/ui/Button';
import { buttonClass } from '@/shared/ui/buttonStyles';
import { ScreenHeader } from '@/shared/ui/ScreenHeader';
import { Sheet } from '@/shared/ui/Sheet';

const STATUSES: readonly UserStatus[] = ['school', 'applicant', 'student'];

type Picker = 'university' | 'group' | null;

export function ProfileScreen() {
  const profile = useProfile();
  const [picker, setPicker] = useState<Picker>(null);

  return (
    <>
      <ScreenHeader title="Мой профиль" />

      {profile.isPending && <Hint>Загружаю профиль…</Hint>}
      {profile.isError && <Hint>Не удалось загрузить профиль. Проверьте связь.</Hint>}

      {profile.data !== undefined && (
        <ProfileView
          profile={profile.data}
          onPick={setPicker}
          picker={picker}
          onClosePicker={() => {
            setPicker(null);
          }}
        />
      )}
    </>
  );
}

function ProfileView({
  profile,
  picker,
  onPick,
  onClosePicker,
}: {
  readonly profile: Profile;
  readonly picker: Picker;
  readonly onPick: (picker: Picker) => void;
  readonly onClosePicker: () => void;
}) {
  const update = useUpdateProfile();
  const verify = useConfirmVerification();
  const result = useLatestResult();
  const tracked = useTracked();

  const isStudent = profile.status === 'student';

  return (
    <>
      <NameRow profile={profile} />

      <div className="mt-3 text-[11px] font-bold tracking-[0.2em] text-neutral-600">СТАТУС</div>
      <div className="mt-[10px] flex gap-2">
        {STATUSES.map((status) => (
          <Button
            key={status}
            variant={profile.status === status ? 'dark' : 'outline'}
            disabled={update.isPending}
            onClick={() => {
              update.mutate({ status });
            }}
            className="flex-1 px-[6px] py-[14px] text-[13px] disabled:opacity-100"
          >
            {STATUS_LABELS[status]}
          </Button>
        ))}
      </div>

      {/* Смена статуса открывает и закрывает разделы 4 и 7 немедленно — об
          этом стоит сказать словами, а не оставлять человека гадать. */}
      {isStudent && profile.university === null && (
        <p className="mt-3 rounded-[22px] bg-accent-200 px-[18px] py-[14px] text-[13px]">
          Осталось выбрать вуз — тогда откроются расписание и точки питания.
        </p>
      )}

      <div className="mt-5 flex flex-col gap-[10px]">
        <Row
          label="ВУЗ"
          value={profile.university?.short_name ?? 'Не указан'}
          action={
            <Button
              variant="dark"
              aria-label="Изменить вуз"
              className="flex-none px-4 py-[10px] text-[12px]"
              onClick={() => {
                onPick('university');
              }}
            >
              Изменить
            </Button>
          }
        />

        {/* Группа нужна только студенту: у абитуриента расписания нет. */}
        {isStudent && (
          <Row
            label="ГРУППА"
            value={profile.group_name ?? 'Не указана'}
            action={
              <Button
                variant="dark"
                aria-label="Изменить группу"
                disabled={profile.university === null}
                className="flex-none px-4 py-[10px] text-[12px] disabled:opacity-60"
                onClick={() => {
                  onPick('group');
                }}
              >
                Изменить
              </Button>
            }
          />
        )}

        <Row
          label="РЕЗУЛЬТАТ ТЕСТА"
          value={
            result.data == null ? 'Не пройден' : (result.data.top_directions[0]?.name ?? 'Посчитан')
          }
          action={
            <Link
              to="/career-test"
              className={buttonClass('outline', 'flex-none px-4 py-[10px] text-[12px]')}
            >
              {result.data == null ? 'Пройти' : 'Открыть'}
            </Link>
          }
        />

        <Row
          label="ОТСЛЕЖИВАЕТСЯ ВУЗОВ"
          value={String(tracked.data?.total ?? 0)}
          action={
            <Link
              to="/tracker"
              className={buttonClass('outline', 'flex-none px-4 py-[10px] text-[12px]')}
            >
              Открыть
            </Link>
          }
        />
      </div>

      <div className="mt-3 rounded-[34px] bg-text px-6 py-[22px] text-neutral-200">
        <div className="text-[10px] font-bold tracking-[0.18em] text-accent-300">
          БАЛЛЫ АКТИВНОСТИ
        </div>
        <div className="flex items-baseline justify-between gap-3">
          <span className="font-heading text-[76px] leading-[1.05] tracking-[-0.05em]">
            {profile.points_balance}
          </span>
          <Link
            to="/leaderboard"
            className="text-[11px] font-bold tracking-[0.16em] text-neutral-500 underline-offset-4 hover:underline"
          >
            РЕЙТИНГ
          </Link>
        </div>
      </div>

      <VerificationRow profile={profile} onConfirm={verify} />

      <NotificationSettingsSection />

      {update.isError && <Hint>Не удалось сохранить профиль. Попробуйте ещё раз.</Hint>}

      <UniversitySheet
        open={picker === 'university'}
        onClose={onClosePicker}
        selected={profile.university?.id ?? null}
        onSelect={(id) => {
          update.mutate({ university_id: id });
          onClosePicker();
        }}
      />

      <GroupSheet open={picker === 'group'} onClose={onClosePicker} selected={profile.group_name} />
    </>
  );
}

function NameRow({ profile }: { readonly profile: Profile }) {
  const update = useUpdateProfile();
  const [name, setName] = useState('');

  // Платформа не отдала имя и человек его ещё не вводил (уточнение У6).
  if (profile.needs_display_name) {
    return (
      <div className="mt-6">
        <h1 className="font-heading text-[40px] leading-[1.02] tracking-[-0.04em]">
          Как вас зовут?
        </h1>
        <input
          value={name}
          aria-label="Ваше имя"
          placeholder="Имя"
          onChange={(event) => {
            setName(event.target.value);
          }}
          className="mt-4 w-full rounded-full border-[1.5px] border-neutral-400 bg-transparent px-6 py-4 text-[16px]"
        />
        <Button
          variant="dark"
          disabled={name.trim() === '' || update.isPending}
          onClick={() => {
            update.mutate({ display_name: name.trim() });
          }}
          className="mt-3 w-full px-[10px] py-[17px] text-[14px] disabled:opacity-60"
        >
          Сохранить
        </Button>
      </div>
    );
  }

  return (
    <h1 className="mt-6 font-heading text-[66px] leading-[0.95] tracking-[-0.05em]">
      {profile.display_name}
    </h1>
  );
}

function VerificationRow({
  profile,
  onConfirm,
}: {
  readonly profile: Profile;
  readonly onConfirm: ReturnType<typeof useConfirmVerification>;
}) {
  if (profile.is_verified_student) {
    return (
      <div className="mt-3 flex items-center gap-3 rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-[15px]">
        <span className="flex-1 text-[13px] text-neutral-700">
          Статус подтверждён — вы можете отвечать на вопросы абитуриентов.
        </span>
        <span className="flex-none rounded-full bg-accent px-[13px] py-[7px] text-[10px] font-bold tracking-[0.14em]">
          ГОТОВО
        </span>
      </div>
    );
  }

  return (
    <div className="mt-3 flex items-center gap-3 rounded-[26px] border-[1.5px] border-dashed border-neutral-400 px-[18px] py-[15px]">
      {/* Уточнение У7: текст не обещает отправку письма — реальной проверки
          почты за кнопкой нет. */}
      <span className="flex-1 text-[13px] text-neutral-700">
        Подтвердите учебную почту, чтобы отвечать на вопросы абитуриентов
      </span>
      <Button
        variant="accent"
        disabled={!profile.access.schedule || onConfirm.isPending}
        onClick={() => {
          onConfirm.mutate();
        }}
        className="flex-none px-4 py-[10px] text-[12px] disabled:opacity-60"
      >
        Подтвердить
      </Button>
    </div>
  );
}

function UniversitySheet({
  open,
  onClose,
  selected,
  onSelect,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly selected: number | null;
  readonly onSelect: (id: number) => void;
}) {
  const universities = useUniversities();

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title="Выберите вуз"
    >
      {universities.isPending && <SheetHint>Загружаю справочник…</SheetHint>}
      {universities.isError && <SheetHint>Не удалось загрузить список вузов.</SheetHint>}
      {universities.data?.map((university) => (
        <Button
          key={university.id}
          variant={university.id === selected ? 'dark' : 'outline'}
          className="flex-none justify-start px-5 py-4 text-left text-[15px]"
          onClick={() => {
            onSelect(university.id);
          }}
        >
          <span className="min-w-0 flex-1">
            {university.short_name}
            <span className="block text-[12px] text-neutral-600">{university.city}</span>
          </span>
        </Button>
      ))}
    </Sheet>
  );
}

function GroupSheet({
  open,
  onClose,
  selected,
}: {
  readonly open: boolean;
  readonly onClose: () => void;
  readonly selected: string | null;
}) {
  // Список групп — из блока 4: только он знает, какие группы есть у вуза
  // (ТЗ 4.3, уточнение У13). Запрос уходит, только когда шторку открыли.
  const groups = useGroups(open);
  const bind = useBindGroup();

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title="Выберите группу"
    >
      {groups.isPending && <SheetHint>Загружаю группы…</SheetHint>}
      {groups.isError && <SheetHint>Не удалось загрузить список групп.</SheetHint>}
      {groups.data?.length === 0 && (
        <SheetHint>У этого вуза в справочнике пока нет групп.</SheetHint>
      )}
      {groups.data?.map((group) => (
        <Button
          key={group.name}
          variant={group.name === selected ? 'dark' : 'outline'}
          disabled={bind.isPending}
          className="flex-none justify-start px-5 py-4 text-left text-[15px] disabled:opacity-60"
          onClick={() => {
            bind.mutate(group.name, { onSuccess: onClose });
          }}
        >
          {group.name}
        </Button>
      ))}
      {bind.isError && <SheetHint>Не удалось сохранить группу.</SheetHint>}
    </Sheet>
  );
}

function Row({
  label,
  value,
  action,
}: {
  readonly label: string;
  readonly value: string;
  readonly action: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 rounded-[26px] border-[1.5px] border-neutral-400 px-[18px] py-[15px]">
      <div className="min-w-0 flex-1">
        <div className="text-[10px] font-bold tracking-[0.18em] text-neutral-600">{label}</div>
        <div className="mt-[3px] text-[15px]">{value}</div>
      </div>
      {action}
    </div>
  );
}

function Hint({ children }: { readonly children: React.ReactNode }) {
  return <p className="mt-6 text-[14px] leading-[1.5] text-neutral-700">{children}</p>;
}

function SheetHint({ children }: { readonly children: React.ReactNode }) {
  return <p className="flex-none text-[13px] leading-[1.45] text-neutral-700">{children}</p>;
}

/**
 * Настройки уведомлений (уточнение У9).
 *
 * Час ежедневной сводки выбирается чипами — тем же приёмом, что и срок
 * дедлайна: экрана под это в макете нет, а компонент уже есть.
 */
function NotificationSettingsSection() {
  const settings = useNotificationSettings();
  const update = useUpdateNotificationSettings();

  const data = settings.data;
  if (data === undefined) return null;

  const muted = new Set(data.kinds.filter((kind) => kind.muted).map((kind) => kind.code));

  const toggle = (code: NotificationKind) => {
    const next = new Set(muted);
    if (next.has(code)) next.delete(code);
    else next.add(code);
    update.mutate({ muted_kinds: [...next] });
  };

  return (
    <>
      <div className="mt-5 text-[11px] font-bold tracking-[0.2em] text-neutral-600">
        УВЕДОМЛЕНИЯ
      </div>

      <p className="mt-3 text-[12px] text-neutral-600">Сводка расписания приходит в</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {DIGEST_HOURS.map((hour) => (
          <Button
            key={hour}
            variant={hour === data.digest_hour ? 'dark' : 'outline'}
            aria-pressed={hour === data.digest_hour}
            disabled={update.isPending}
            onClick={() => {
              update.mutate({ digest_hour: hour });
            }}
            className="px-4 py-[10px] text-[13px] disabled:opacity-60"
          >
            {String(hour).padStart(2, '0')}:00
          </Button>
        ))}
      </div>

      <div className="mt-3 flex flex-col gap-2">
        {data.kinds.map((kind) => (
          <label
            key={kind.code}
            className="flex items-center gap-3 rounded-[22px] border-[1.5px] border-neutral-400 px-[18px] py-3"
          >
            <input
              type="checkbox"
              checked={!kind.muted}
              disabled={update.isPending}
              onChange={() => {
                toggle(kind.code);
              }}
              className="h-[18px] w-[18px] flex-none accent-[var(--color-accent)]"
            />
            <span className="flex-1 text-[14px]">{kind.label}</span>
          </label>
        ))}
      </div>

      {update.isError && <Hint>Не удалось сохранить настройки уведомлений.</Hint>}
    </>
  );
}

/** Часы для чипов сводки: утро, день и вечер — больше выбора не нужно. */
const DIGEST_HOURS = [7, 8, 9, 12, 18, 20] as const;
