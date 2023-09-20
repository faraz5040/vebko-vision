import { createApp } from 'vue';
import { RouterView } from 'vue-router';
import { createVuetify } from 'vuetify';
import { aliases, mdi } from 'vuetify/iconsets/mdi-svg';
import { mdiSpeedometer } from '@mdi/js';
// import 'vuetify/styles';
import '@/assets/styles/main.scss';
import pinia from './store';
import router from './router';

const vuetify = createVuetify({
  theme: {
    themes: { light: { colors: { primary: '#1867C0', secondary: '#5CBBF6' } } },
  },
  icons: {
    defaultSet: 'mdi',
    aliases: {
      ...aliases,
      speedometer: mdiSpeedometer,
    },
    sets: {
      mdi,
    },
  },
});

createApp(RouterView).use(vuetify).use(router).use(pinia).mount('#app');
