/**
 * Шторка выбора вуза с поиском (уточнение У31).
 *
 * Один компонент на всё приложение: вуз выбирается и в профиле, и в вопросе
 * старшекурснику, и оба раза это должно работать одинаково. До этого в каждом
 * экране лежал свой список без поиска.
 *
 * Поведение задано заказчиком: список видно сразу при открытии, а после
 * каждого символа он пересобирается по близости названия. Поиск идёт по
 * загруженному справочнику в памяти — он маленький и меняется релизами, так
 * что запрос на сервер за каждым символом был бы платой ни за что.
 */
import { useState } from 'react';

import { useUniversities, type University } from '@/shared/api/profile';
import { Button } from '@/shared/ui/Button';
import { Sheet } from '@/shared/ui/Sheet';
import { searchUniversities } from '@/shared/ui/universitySearch';

interface UniversityPickerProps {
  readonly open: boolean;
  readonly onClose: () => void;
  /** Заголовок шторки: в профиле и в вопросе он разный. */
  readonly title: string;
  /** Уже выбранный вуз — он подсвечен в списке. */
  readonly selected: number | null;
  readonly onSelect: (university: University) => void;
}

export function UniversityPicker({
  open,
  onClose,
  title,
  selected,
  onSelect,
}: UniversityPickerProps) {
  const universities = useUniversities();
  const [query, setQuery] = useState('');

  // Запрос живёт, пока открыта шторка: закрыли и открыли — снова весь список.
  // Иначе человек возвращается к чужому фильтру и думает, что вузы пропали.
  // Сброс в рендере, а не эффектом: это подстройка состояния под изменившийся
  // пропс, и лишний проход рендера здесь не нужен.
  const [openedWith, setOpenedWith] = useState(open);
  if (openedWith !== open) {
    setOpenedWith(open);
    setQuery('');
  }

  const found = searchUniversities(universities.data ?? [], query);

  return (
    <Sheet
      open={open}
      onOpenChange={(next) => {
        if (!next) onClose();
      }}
      title={title}
    >
      <div className="flex-none">
        <input
          type="search"
          value={query}
          onChange={(event) => {
            setQuery(event.target.value);
          }}
          placeholder="Название, аббревиатура или город"
          aria-label="Поиск вуза"
          // Автофокуса нет намеренно: на телефоне он поднимает клавиатуру и
          // закрывает ей половину списка, который человек пришёл посмотреть.
          className="w-full rounded-full border-[1.5px] border-neutral-400 bg-transparent px-5 py-[13px] text-[15px] outline-none focus:border-text"
        />
      </div>

      {universities.isPending && <SheetHint>Загружаю справочник…</SheetHint>}
      {universities.isError && <SheetHint>Не удалось загрузить список вузов.</SheetHint>}

      {universities.isSuccess && found.length === 0 && (
        <SheetHint>
          По запросу «{query}» ничего не нашлось. Попробуйте короче — например, только город или
          первые буквы названия.
        </SheetHint>
      )}

      {found.map((university) => (
        <Button
          key={university.id}
          variant={university.id === selected ? 'dark' : 'outline'}
          className="flex-none justify-start px-5 py-4 text-left text-[15px]"
          onClick={() => {
            onSelect(university);
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

function SheetHint({ children }: { readonly children: React.ReactNode }) {
  return <p className="flex-none px-2 py-1 text-[13px] text-neutral-600">{children}</p>;
}
