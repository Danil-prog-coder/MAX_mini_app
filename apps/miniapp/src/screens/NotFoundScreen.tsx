/**
 * Адрес не найден.
 *
 * Этого экрана нет в дизайн-хендоффе — он нужен архитектурно. Требование
 * «тупиковых экранов нет» (ТЗ 1.1) без него дырявое: по неизвестному адресу
 * (устаревшая ссылка, опечатка в диплинке) пользователь оказался бы на пустой
 * странице без выхода. Экран собран из тех же токенов, что и остальные, и
 * получает кнопку «Главное меню» от общего layout-роута.
 */
import { Link } from 'react-router-dom';

export function NotFoundScreen() {
  return (
    <>
      <div className="text-[11px] font-bold tracking-[0.2em] text-neutral-600 uppercase">
        Адрес не найден
      </div>
      <h1 className="mt-6 font-heading text-[56px] leading-[0.95] tracking-[-0.05em]">
        Такой страницы нет
      </h1>
      <p className="mt-4 text-[15px] leading-[1.5] text-neutral-700">
        Ссылка устарела или в ней опечатка. Ничего не потеряно: данные профиля и начатые сценарии на
        месте.
      </p>
      <Link
        to="/"
        className="mt-6 flex items-center justify-center rounded-[26px] bg-accent px-[18px] py-4 text-[15px] transition-colors hover:bg-accent-400 active:bg-accent-700"
      >
        Вернуться в главное меню
      </Link>
    </>
  );
}
