/**
 * Шапка экрана: кнопка «назад» и caps-заголовок.
 *
 * Повторяется на всех экранах, кроме главного меню (у него своя шапка с
 * логотипом и пилюлей статуса).
 */
import { useLocation, useNavigate } from 'react-router-dom';

import { ChevronLeftIcon } from './icons';

interface ScreenHeaderProps {
  readonly title: string;
}

export function ScreenHeader({ title }: ScreenHeaderProps) {
  const navigate = useNavigate();
  const location = useLocation();

  // `key === 'default'` означает, что этот адрес открыт первым в сессии: шага
  // назад внутри приложения нет, и `navigate(-1)` увёл бы пользователя из
  // мини-приложения. По диплинку в блок такое случается штатно.
  const goBack = () => {
    if (location.key === 'default') {
      void navigate('/');
    } else {
      void navigate(-1);
    }
  };

  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        onClick={goBack}
        aria-label="Назад"
        className="flex h-[38px] w-[38px] flex-none items-center justify-center rounded-full border-[1.5px] border-neutral-400 transition-colors hover:bg-text/7"
      >
        <ChevronLeftIcon />
      </button>
      <span className="text-[11px] font-bold tracking-[0.2em] uppercase">{title}</span>
    </div>
  );
}
