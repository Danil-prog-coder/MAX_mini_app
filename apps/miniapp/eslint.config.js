import js from '@eslint/js';
import reactHooks from 'eslint-plugin-react-hooks';
import reactRefresh from 'eslint-plugin-react-refresh';
import tseslint from 'typescript-eslint';

export default tseslint.config(
  { ignores: ['dist', 'playwright-report', 'test-results', 'src/shared/api/schema.d.ts'] },
  js.configs.recommended,
  tseslint.configs.recommendedTypeChecked,
  {
    languageOptions: {
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    files: ['**/*.{ts,tsx}'],
    plugins: {
      'react-hooks': reactHooks,
      'react-refresh': reactRefresh,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      'react-refresh/only-export-components': ['warn', { allowConstantExport: true }],
      // Пользовательский контент рендерится текстом (тех. ТЗ 8.11): запрет на
      // dangerouslySetInnerHTML держим правилом, а не памятью.
      'no-restricted-syntax': [
        'error',
        {
          selector: 'JSXAttribute[name.name="dangerouslySetInnerHTML"]',
          message:
            'dangerouslySetInnerHTML запрещён: пользовательский контент рендерится текстом (тех. ТЗ 8.11)',
        },
      ],
    },
  },
  {
    files: ['**/*.config.ts', 'tests/**'],
    rules: { '@typescript-eslint/no-unsafe-assignment': 'off' },
  },
  {
    // Сам конфиг eslint — обычный JS и вне проекта TypeScript, правила с
    // проверкой типов к нему не применимы.
    files: ['**/*.js'],
    ...tseslint.configs.disableTypeChecked,
  },
);
