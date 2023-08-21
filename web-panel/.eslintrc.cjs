/* eslint-env node */
require('@rushstack/eslint-patch/modern-module-resolution');
const vuetifyTags = Object.keys(require('vuetify/dist/vuetify.js').components);

/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  parserOptions: {
    sourceType: 'module',
    ecmaVersion: 'latest',
    tsconfigRootDir: __dirname,
    project: 'tsconfig*.json',
    EXPERIMENTAL_useSourceOfProjectReferenceRedirect: true,
    extraFileExtensions: ['.vue'],
  },
  extends: ['eslint:recommended', 'plugin:unicorn/recommended'],
  rules: {
    // The core 'no-unused-vars' rules (in the eslint:recommeded ruleset)
    // does not work with type definitions
    'no-unused-vars': 'off',
    // TS already checks for that, and Typescript-Eslint recommends to disable it
    // https://typescript-eslint.io/linting/troubleshooting#i-get-errors-from-the-no-undef-rule-about-global-variables-not-being-defined-even-though-there-are-no-typescript-errors
    'no-undef': 'off',
    '@typescript-eslint/no-unused-vars': 'warn',
  },
  overrides: [
    {
      // Config and build scripts in root directory
      files: ['./*.{ts,mts,cts,cjs,js,mjs}'],
      env: { node: true, browser: false, es2023: true, jest: false },
      overrides: [
        {
          files: ['*.{ts,mts,cts}'],
          extends: [
            'eslint:recommended',
            'plugin:@typescript-eslint/strict-type-checked',
            'plugin:@typescript-eslint/stylistic-type-checked',
            'plugin:unicorn/recommended',
          ],
        },
      ],
    },
    {
      files: ['src/**/*.{vue,ts,tsx}'],
      env: { node: false, browser: true, es2023: true, jest: false },
      plugins: ['@typescript-eslint', 'vue', 'unicorn'],
      parser: 'vue-eslint-parser',
      parserOptions: {
        ecmaFeatures: { jsx: true },
        vueFeatures: { filter: false },
        parser: {
          js: 'espree',
          cjs: 'espree',
          mjs: 'espree',
          jsx: 'espree',
          ts: require.resolve('@typescript-eslint/parser'),
          tsx: require.resolve('@typescript-eslint/parser'),
        },
      },
      extends: [
        'plugin:vue/vue3-recommended',
        'eslint:recommended',
        'plugin:@typescript-eslint/strict-type-checked',
        'plugin:@typescript-eslint/stylistic-type-checked',
        'plugin:unicorn/recommended',
        // '@vue/eslint-config-prettier/skip-formatting',
      ],
      rules: {
        'vue/multi-word-component-names': 'off',
        'vue/component-name-in-template-casing': [
          'error',
          'PascalCase',
          {
            registeredComponentsOnly: true,
            globals: [...vuetifyTags, 'RouterLink', 'RouterView'],
            ignores: [],
          },
        ],
        'vue/block-lang': ['error', { script: { lang: 'ts' } }],
        'vue/component-api-style': ['error', ['script-setup', 'composition']],
        'vue/match-component-file-name': [
          'error',
          { extensions: ['vue', 'ts', 'tsx'], shouldMatchCase: false },
        ],
        'vue/match-component-import-name': 'error',
      },
    },
  ],
};
