<template>
  <VContainer class="fill-height">
    <VResponsive class="align-center text-center fill-height">
      <!-- <div class="text-body-2 font-weight-light mb-n1">دستاوردی از گروه تریسرز</div> -->

      <!-- <h1 class="text-h2 font-weight-bold">سامانه جانما</h1> -->

      <div class="py-14" />

      <v-card width="800">
        <img
          width="800"
          height="600"
          transition="none"
          :src="frameDataUrl"
          alt="Camera video output"
        />
        <v-card-item>
          <v-card-title>جانما</v-card-title>
          <v-card-subtitle>کاری از گروه تریسرز </v-card-subtitle>
        </v-card-item>
        <v-card-text>
          <p class="pt-3" dir="rtl">جایگاه خوانده شده از DWM1001:</p>
          <p class="pb-3">{{ dwmPosition }}</p>
          <p class="pt-3" dir="rtl">بازه‌های خوانده شده از DWM1001:</p>
          <p class="pb-3">{{ dwmDistances }}</p>
          <p class="pt-3" dir="rtl">جایگاه خوانده شده از دوربین:</p>
          <p class="pb-3">{{ cameraPosition }}</p>
        </v-card-text>
        <!-- <VVirtualScroll ref="logListEl" :height="300" :items="dwmLogs">
        <template #default="{ item }">
          <VListItem
            :title="item.text"
            :subtitle="new Date(item.timestamp).toLocaleTimeString('fa-IR')"
          />
        </template>
      </VVirtualScroll> -->

        <VCardActions class="d-flex align-center justify-center">
          <VCol cols="auto">
            <VBtn
              color="primary"
              href=""
              min-width="228"
              rel="noopener noreferrer"
              size="x-large"
              target="_blank"
              variant="flat"
              :loading="loading"
              @click="handleClick"
            >
              <VIcon icon="mdi-speedometer" size="large" start />

              {{ started ? 'پایان' : 'آغاز' }}
            </VBtn>
          </VCol>
        </VCardActions>
      </v-card>
    </VResponsive>
  </VContainer>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { io } from 'socket.io-client';
import { onMounted } from 'vue';
// import type { VVirtualScroll } from 'vuetify/lib/components/index.mjs';
// import { waitForStateChange } from '@/utils.ts/socket';

// interface DwmLog {
//   timestamp: number;
//   text: string;
// }

interface Location {
  x: number;
  y: number;
  z: number;
}

interface CameraFramePayload {
  frame: ArrayBuffer;
  location?: null | Location;
}

const started = ref(false);
const loading = ref(false);
const frameDataUrl = ref('');
const dwmPosition = ref('');
const dwmDistances = ref('');
const cameraPosition = ref('');
const socketEvents = Object.freeze({
  dwmMessage: 'dwm-message',
  cameraLocation: 'vision-location',
  cameraFrame: 'vision-frame',
});
// const logListEl = ref<typeof VVirtualScroll>();

const socket = io({
  autoConnect: true,
  closeOnBeforeunload: true,
  path: '/ws/socket.io/',
  transports: ['websocket'],
});

onMounted(async () => {
  const status: unknown = await socket
    .timeout(1000)
    .emitWithAck('status')
    .catch(() => false);
  if (typeof status != 'boolean') return;

  console.log(status);

  started.value = status;
});

async function handleClick() {
  loading.value = true;
  await toggleCamera().finally(() => (loading.value = false));
}

async function toggleCamera() {
  if (started.value) {
    socket.off();
    dwmPosition.value = '';
    dwmDistances.value = '';
    cameraPosition.value = '';
  } else {
    socket.on(socketEvents.dwmMessage, (data) => {
      if (!data) return;
      if ('x' in data) {
        const { x, y, z } = data as Location;
        dwmPosition.value = `X: ${x.toFixed(2)}, Y: ${y.toFixed(
          2,
        )}, Z: ${z.toFixed(2)}`;
      } else {
        dwmDistances.value = JSON.stringify(data);
      }
      // dwmLogs.value.push({ timestamp: Date.now(), text });
      // logListEl.value?.scrollToIndex(dwmLogs.value.length - 1);
      // if (dwmLogs.value.length > 1000) {
      //   dwmLogs.value.splice(0, 500);
      // }
    });
    socket.on(
      socketEvents.cameraFrame,
      ({ frame, location }: CameraFramePayload) => {
        const blob = new Blob([frame], { type: 'image/jpeg' });
        frameDataUrl.value = URL.createObjectURL(blob);
        cameraPosition.value = location ? JSON.stringify(location) : 'ناخوانا';
      },
    );
  }

  const endpoint = started.value ? 'end' : 'start';
  started.value = !started.value;

  const response = await fetch(`/api/${endpoint}`, { method: 'POST' });

  // Download file
  if (endpoint == 'end') {
    const fileNameRegex =
      /filename[^\n;=]*=((?<quote>["'])(?<f1>.*?)\k<quote>|(?<f2>[^\n;]*))/;
    const contentDisposition = response.headers.get('Content-Disposition');
    if (!contentDisposition) return;
    const groups = fileNameRegex.exec(contentDisposition)?.groups;
    const fileName = groups?.f1 ?? groups?.f2 ?? '';
    const blob = await response.blob();
    const file = fileName ? new File([blob], fileName) : blob;
    window.location.assign(URL.createObjectURL(file));
  }
}
</script>
