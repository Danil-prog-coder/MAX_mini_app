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

  it('не оставляет пустую строку из окружения', () => {
    const config = readConfig({ VITE_API_BASE_URL: '   ', VITE_MOCK_MAX_USER_ID: '' });

    expect(config.apiBaseUrl).toBe('http://localhost:8000');
    expect(config.mockMaxUserId).toBe('mock-user-1');
  });
});
