// Plugins
import vue from '@vitejs/plugin-vue';
import vuetify, { transformAssetUrls } from 'vite-plugin-vuetify';
// import Unfonts from 'unplugin-fonts/vite';

// Utilities
import { defineConfig } from 'vite';
import { fileURLToPath, URL } from 'node:url';

// const persianUnicodeRanges =
//   'U+609, U+60C, U+61B, U+61F, U+621-624, U+626-63A, U+641-642, U+644-648, U+64B-64D, U+651, U+654, U+66A-66C, U+67E, U+686, U+698, U+6A9, U+6AF, U+6CC, U+6F0-6F9';
//   // 'U+A9, U+AB, U+BB, U+609, U+60C, U+61B, U+61F, U+621-624, U+626-63A, U+641-642, U+644-648, U+64B-64D, U+651, U+654, U+66A-66C, U+67E, U+686, U+698, U+6A9, U+6AF, U+6CC, U+6F0-6F9, U+2010-2011, U+2026, U+2030, U+2039-203A, U+20AC, U+2212';
// // ('U+0600-06FF, U+0750-077F, U+0870-088E, U+0890-0891, U+0898-08E1, U+08E3-08FF, U+200C-200E, U+2010-2011, U+204F, U+2E41, U+FB50-FDFF, U+FE70-FE74, U+FE76-FEFC');
// const text = persianUnicodeRanges
//   .split(/\s*,\s*/)
//   .map((range) =>
//     range.split('-').map((s) => Number.parseInt(s.replace('U+', ''), 16)),
//   )
//   // End inclusive ranges
//   .map(([start, end]) => ({ start, length: (end || start) + 1 - start }))
//   .flatMap(({ start, length }) =>
//     Array.from({ length }, (_, index) => String.fromCodePoint(start + index)),
//   )
//   .join('');

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [
    vue({ template: { transformAssetUrls } }),
    // https://github.com/vuetifyjs/vuetify-loader/tree/next/packages/vite-plugin
    vuetify({ autoImport: true }),
    // Unfonts({
    //   google: {
    //     families: [{ name: 'Roboto', styles: 'wght@100;300;400;500;700;900' }],
    //   },
    // }),
    // Unfonts({
    //   google: {
    //     text,
    //     families: [
    //       { name: 'Vazirmatn', styles: 'wght@100;300;400;500;700;900' },
    //     ],
    //   },
    // }),
  ],
  define: { 'process.env': {} },
  resolve: {
    alias: { '@': fileURLToPath(new URL('src', import.meta.url)) },
    extensions: ['.js', '.json', '.jsx', '.mjs', '.ts', '.tsx', '.vue'],
  },
  server: {
    port: 3000,
    proxy: {
      '^/api(/|$)': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
      '^/ws(/|$)': {
        target: 'ws://127.0.0.1:8000',
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
