import globals from 'globals'
import tseslint from 'typescript-eslint'
import eslintJs from '@eslint/js'
import eslintConfigPrettier from 'eslint-config-prettier'

export default tseslint.config(
    {
        ignores: ['node_modules', 'dist', '*.config.js', 'static/**/*']
    },
    eslintJs.configs.recommended,
    ...tseslint.configs.recommended,
    eslintConfigPrettier,
    { 
        files: ['src/**/*.ts'],
        languageOptions: {
            globals: {
                ...globals.browser,
                ...globals.es2021
            },
            parserOptions: {
                project: true
            }
        },
        rules: {
            '@typescript-eslint/no-explicit-any': 'off'
        }
    }
)