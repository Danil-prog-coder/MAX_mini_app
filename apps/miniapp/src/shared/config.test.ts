import { describe, expect, it } from 'vitest';

import { normaliseBaseUrl, readConfig } from './config';

describe('normaliseBaseUrl', () => {
  it('снимает завершающие слэши', () => {
    expect(normaliseBaseUrl('http://localhost:8000/')).toBe('http://localhost:8000');
    expect(normaliseBaseUrl('http://localhost:8000///')).toBe('http://localhost:8000');
  });

  it('снимает окружающие пробелы', () => {
    expect(normaliseBaseUrl('  http://localhost:8000  ')).toBe('http://localhost:8000');
  });

  it('оставляет корректный URL как есть', () => {
    expect(normaliseBaseUrl('https://api.example.com')).toBe('https://api.example.com');
  });
});

describe('readConfig', () => {
  it('берёт значения из окружения сборки', () => {
    const config = readConfig({
      VITE_API_BASE_URL: 'https://api.example.com/',
      VITE_MOCK_MAX_USER_ID: 'user-42',
    });

    expect(config.apiBaseUrl).toBe('https://api.example.com');
    expect(config.mockMaxUserId).toBe('user-42');
  });

  it('подставляет значения по умолчанию, если переменных нет', () => {
    const config = readConfig({});

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
    expect(config.mockMaxUserId).toBe('mock-user-1');
  });

  it('пустое значение — это осознанный выбор same-origin, а не забытая настройка', () => {
    // Так задано в docker-compose: фронт ходит на /api/v1/... того же origin,
    // а dev-сервер проксирует запрос в core-api по docker-сети. Подставлять
    // сюда localhost:8000 нельзя — именно это и ломалось, когда порт занят.
    const config = readConfig({ VITE_API_BASE_URL: '   ', VITE_MOCK_MAX_USER_ID: '' });

    expect(config.apiBaseUrl).toBe('');
    expect(config.mockMaxUserId).toBe('mock-user-1');
  });

  it('незаданная переменная даёт локальный адрес по умолчанию', () => {
    // Разработка без docker: фронт на 5173, uvicorn на 8000, прокси не нужен.
    // Пустой объект, а не поля со значением undefined: при
    // exactOptionalPropertyTypes это разные вещи, и «переменной нет» —
    // именно первое.
    const config = readConfig({});

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
  });
});
