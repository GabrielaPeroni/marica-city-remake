const js = require('@eslint/js');
const prettier = require('eslint-config-prettier');

// Browser globals used across the plain-JS files in static/js/. There is no
// bundler/module system yet: every file below is loaded individually via a
// <script src="..."> tag in a Django template and files share globals by
// attaching to `window` or simply relying on script load order.
const browserGlobals = {
  window: 'readonly',
  document: 'readonly',
  console: 'readonly',
  navigator: 'readonly',
  location: 'readonly',
  localStorage: 'readonly',
  sessionStorage: 'readonly',
  fetch: 'readonly',
  FormData: 'readonly',
  URLSearchParams: 'readonly',
  FileReader: 'readonly',
  Promise: 'readonly',
  Set: 'readonly',
  Map: 'readonly',
  setTimeout: 'readonly',
  clearTimeout: 'readonly',
  setInterval: 'readonly',
  clearInterval: 'readonly',
  atob: 'readonly',
  btoa: 'readonly',
  alert: 'readonly',
  confirm: 'readonly',
  module: 'readonly',
};

// Third-party libraries loaded from CDN <script> tags in templates/base.html
// and templates/core/landing.html (Bootstrap, Swiper, Google Maps / Sign-In SDK).
const thirdPartyGlobals = {
  bootstrap: 'readonly',
  Swiper: 'readonly',
  google: 'readonly',
};

module.exports = [
  js.configs.recommended,
  {
    files: ['static/js/**/*.js'],
    languageOptions: {
      ecmaVersion: 2021,
      sourceType: 'script',
      globals: {
        ...browserGlobals,
        ...thirdPartyGlobals,
      },
    },
    rules: {
      'no-unused-vars': ['warn', { args: 'none', caughtErrors: 'none' }],
      'no-undef': 'error',
      'no-console': 'off',
    },
  },
  {
    // getCookie() is defined in utils.js and consumed by these files via
    // script load order (utils.js is loaded first in base.html).
    files: [
      'static/js/components/user_management.js',
      'static/js/favorites-ui.js',
      'static/js/google_auth.js',
      'static/js/login.js',
    ],
    languageOptions: {
      globals: { getCookie: 'readonly' },
    },
  },
  {
    // favoritesService is the singleton exported by favorites-service.js,
    // which base.html loads before favorites-ui.js.
    files: ['static/js/favorites-ui.js'],
    languageOptions: {
      globals: { favoritesService: 'readonly' },
    },
  },
  {
    ignores: ['static/js/dist/**', 'node_modules/**', 'staticfiles/**'],
  },
  prettier,
];
