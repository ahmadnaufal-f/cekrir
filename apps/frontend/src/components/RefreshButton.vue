<script setup lang="ts">
import { ui } from '../lib/strings'
import AppIcon from './AppIcon.vue'

defineProps<{ loading?: boolean }>()
</script>

<template>
  <button
    type="button"
    class="button button--quiet refresh-button"
    :aria-label="ui.refresh"
    :title="ui.refresh"
  >
    <AppIcon :name="loading ? 'loading' : 'refresh'" />
  </button>
</template>

<style scoped>
.refresh-button {
  width: 48px;
  height: 48px;
  flex: none;
  padding: 0;
  border: 1px solid #dce2d8;
  border-radius: 10px;
  color: var(--accent);
}

.refresh-button:hover:not(:disabled) {
  background-color: #e2eadd;
}
</style>
