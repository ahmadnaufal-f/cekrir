<script setup lang="ts">
import { ui } from '../lib/strings'
import AppIcon from './AppIcon.vue'

withDefaults(defineProps<{ label?: string }>(), { label: ui.back })
</script>

<template>
  <button type="button" class="back-button" :aria-label="label">
    <AppIcon name="back" />
  </button>
</template>

<style scoped>
.back-button {
  display: grid;
  width: 48px;
  height: 48px;
  flex: none;
  place-items: center;
  padding: 0;
  border: 1px solid #d5decf;
  border-radius: 50%;
  background: #fffefa;
  color: #234e41;
}

.back-button:active {
  background: #e9eedf;
}

@media (hover: hover) and (pointer: fine) {
  .back-button:hover {
    background: #e9eedf;
  }
}

.back-button .app-icon {
  width: 1.25rem;
  height: 1.25rem;
}

@media (prefers-reduced-motion: no-preference) {
  .back-button {
    transition:
      background-color var(--motion-feedback) ease,
      transform var(--motion-feedback) var(--ease-enter);
  }

  .back-button:active {
    transform: scale(0.96);
  }
}
</style>
