<template>
  <VContainer class="fill-height">
    <VResponsive class="align-center text-center fill-height">
      <VImg height="300" src="" />

      <div class="text-body-2 font-weight-light mb-n1">دستاوردی از وبکو</div>

      <h1 class="text-h2 font-weight-bold">سامانه جانما</h1>

      <div class="py-14" />

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

const started = ref(false);
</script>
