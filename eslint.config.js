import js from '@eslint/js'
import globals from 'globals'
import react from 'eslint-plugin-react'
import reactHooks from 'eslint-plugin-react-hooks'

/**
 * Lint config aimed at catching the class of bug that shipped to production:
 *
 *   <IconFace /> was used in Sidebar.jsx but never imported.
 *   Vite compiled it happily (it does not resolve JSX identifiers), the build
 *   passed, and the app threw a ReferenceError at runtime - blanking the page.
 *
 * `react/jsx-no-undef` catches exactly that. `react-hooks/rules-of-hooks` and
 * `no-undef` catch stale-closure and typo bugs.
 *
 * Rules deliberately switched OFF, with reasons:
 *
 *  - react/prop-types: this project is plain JavaScript with no TypeScript and
 *    no PropTypes anywhere. Enabling it produces ~30 errors that say nothing
 *    about correctness, and a linter nobody can get to zero is a linter nobody
 *    reads. The genuinely useful signal (undefined components, undefined
 *    variables, hook misuse) is preserved.
 *
 *  - react/no-unknown-property: react-three-fiber components take props that
 *    look like DOM attributes but are not (attach, args, vertexColors,
 *    wireframe). The rule cannot know about the r3f reconciler, so every
 *    <bufferGeometry>/<meshBasicMaterial> prop is a false positive.
 *
 * Run: npm run lint
 */
export default [
  {
    // `Notin/` is an unrelated project that happens to live inside this
    // working directory (it has its own .git). Linting it produces ~10k
    // problems from code this repository does not own, which drowns out the
    // real signal. `dist/` is generated output.
    ignores: ['dist/**', 'node_modules/**', 'Notin/**', 'fablab-face-attendance/**']
  },
  js.configs.recommended,
  {
    files: ['**/*.{js,jsx}'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: { ...globals.browser, ...globals.es2022 },
      parserOptions: {
        ecmaFeatures: { jsx: true }
      }
    },
    settings: { react: { version: 'detect' } },
    plugins: {
      react,
      'react-hooks': reactHooks
    },
    rules: {
      ...react.configs.flat.recommended.rules,
      ...react.configs.flat['jsx-runtime'].rules,
      ...reactHooks.configs.recommended.rules,

      // The one that matters most here: catch undefined JSX components.
      'react/jsx-no-undef': 'error',
      'react/jsx-uses-vars': 'error',
      'react/jsx-uses-react': 'off',

      // No PropTypes / TypeScript in this codebase - see header note.
      'react/prop-types': 'off',
      // r3f reconciler props are not DOM attributes.
      'react/no-unknown-property': 'off',

      // Surface unused code and shadowing rather than letting it rot.
      'no-unused-vars': ['warn', { argsIgnorePattern: '^_', varsIgnorePattern: '^_' }],
      'no-shadow': 'warn',
      'no-undef': 'error',
      'no-empty': ['error', { allowEmptyCatch: false }]
    }
  },
  {
    // Build tooling runs in Node, not the browser: `process` and friends.
    files: ['vite.config.js', 'eslint.config.js'],
    languageOptions: {
      globals: { ...globals.node }
    }
  }
]
