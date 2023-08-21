import { createApp } from 'vue';

import { registerPlugins } from '@/plugins';
import { RouterView } from 'vue-router';

const app = createApp(RouterView);

registerPlugins(app);

app.mount('#app');
