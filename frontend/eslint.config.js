import globals from 'globals'
import tseslint from 'typescript-eslint'
import eslintJs from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier'

export default tseslint.config(eslintJs.configs.recommended, ...tseslint.configs.recommended, eslintConfigPrettier, {
    languageOptions: {
        globals: {
            ...globals.browser,
            ...globals.es2021
        },
        parserOptions: {
            project: true // Looks for nearest tsconfig.json to determine project root
        }
    },
    rules: {
        '@typescript-eslint/no-explicit-any': 'off'
    },
    files: ['src/**/*.ts'],
    ignores: ['node_modules', 'dist', '*.config.js', 'static/**/*']
})
