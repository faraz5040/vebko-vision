<template>
  <VContainer class="fill-height">
    <VResponsive class="align-center text-center fill-height">
      <div class="text-body-2 font-weight-light mb-n1">دستاوردی از وبکو</div>

      <h1 class="text-h2 font-weight-bold">سامانه جانما</h1>

      <div class="py-14" />

      <VVirtualScroll :height="300" :items="dwmLogs">
        <template #default="{ item }">
          <VListItem
            :title="item.text"
            :subtitle="new Date(item.timestamp).toISOString()"
          />
        </template>
      </VVirtualScroll>

      <VRow class="d-flex align-center justify-center">
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
      </VRow>
    </VResponsive>
  </VContainer>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { io } from 'socket.io-client';

interface DwmLog {
  timestamp: number;
  text: string;
}

const started = ref(false);
const loading = ref(false);
const dwmLogs = ref([] as DwmLog[]);
const eventName = 'dwm-message' as const;

function onMessage(data: unknown) {
  console.log(data);

  dwmLogs.value.push({ timestamp: Date.now(), text: String(data) });
}

const socket = io('/api', { autoConnect: false });

async function handleClick() {
  const endpoint = started.value ? 'end' : 'start';

  loading.value = true;
  const response = await fetch(`/api/${endpoint}`, { method: 'POST' }).finally(
    () => (loading.value = false),
  );

  if (response.ok) {
    started.value = !started.value;
  }

  if (started.value) {
    socket.connect();
    socket.on(eventName, onMessage);
  } else {
    socket.off(eventName, onMessage);
    socket.disconnect();
  }

  // Download file
  if (endpoint == 'end') {
    const fileNameRegex =
      /filename[^;=\n]*=((?<quote>['"])(?<f1>.*?)\k<quote>|(?<f2>[^;\n]*))/;
    const contentDisposition =
      response.headers.get('Content-Disposition') ?? '';
    const groups = fileNameRegex.exec(contentDisposition)?.groups;
    const fileName = groups?.f1 || groups?.f2 || '';
    const blob = await response.blob();
    const file = fileName ? new File([blob], fileName) : blob;
    window.location.assign(URL.createObjectURL(file));
  }
}
</script>
