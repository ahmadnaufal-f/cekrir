<script setup lang="ts">
import { useId } from 'vue'
import AppIcon from './AppIcon.vue'
import { adminCopy } from '../lib/admin-copy'

defineProps<{
  id: string
  name: string
  description: string
  editLabel: string
  busy?: boolean
}>()
const emit = defineEmits<{ edit: []; remove: [] }>()
const copy = adminCopy.devices
const headingId = `device-card-${useId()}`
</script>

<template>
  <article class="device-card">
    <header class="device-card__heading">
      <h3 :id="headingId">{{ name }}</h3>
      <slot name="badge" />
    </header>
    <p>{{ description }}</p>
    <small>{{ copy.identity }} · {{ id }}</small>
    <div class="device-card__actions">
      <slot name="actions" />
      <button
        class="button button--quiet device-card__icon-button device-card__edit"
        type="button"
        :aria-label="editLabel"
        :aria-describedby="headingId"
        :title="editLabel"
        :disabled="busy"
        @click="emit('edit')"
      >
        <AppIcon name="edit" />
      </button>
      <button
        class="button button--quiet device-card__icon-button device-card__remove"
        type="button"
        :aria-label="copy.removeDevice"
        :aria-describedby="headingId"
        :title="copy.removeDevice"
        :disabled="busy"
        @click="emit('remove')"
      >
        <AppIcon name="trash" />
      </button>
    </div>
  </article>
</template>

<style scoped>
.device-card {
  display: grid;
  min-width: 0;
  gap: 7px;
  padding: 24px var(--card-inset);
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
  overflow-wrap: anywhere;
}
.device-card__heading,
.device-card__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.device-card__heading h3 {
  min-width: 0;
  flex: 1 1 8rem;
  font-size: 1rem;
  line-height: 1.4;
}
.device-card p,
.device-card small {
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.6;
}
.device-card__actions {
  margin-top: 9px;
}
.device-card__actions .button {
  max-width: 100%;
}
.device-card__icon-button {
  width: 44px;
  flex: none;
  padding: 0;
}
.device-card__icon-button .app-icon {
  width: 1.125rem;
  height: 1.125rem;
}
.device-card__remove {
  background: #f5e9e2;
  color: #8d3729;
}
.device-card__remove:hover:not(:disabled) {
  background: #eedcd3;
}
</style>
