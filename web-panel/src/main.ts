import { createApp } from 'vue';
import { RouterView } from 'vue-router';
import { createVuetify } from 'vuetify';
import '@mdi/font/css/materialdesignicons.css';
// import 'vuetify/styles';
import '@/assets/styles/main.scss';
import pinia from './store';
import router from './router';

const vuetify = createVuetify({
  theme: {
    themes: { light: { colors: { primary: '#1867C0', secondary: '#5CBBF6' } } },
  },
});

createApp(RouterView).use(vuetify).use(router).use(pinia).mount('#app');
