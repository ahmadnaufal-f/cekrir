<script setup lang="ts">
import { useId } from 'vue'
import AppIcon from './AppIcon.vue'
import type { IconName } from './AppIcon.vue'

withDefaults(
  defineProps<{
    title: string
    description: string
    icon?: IconName
  }>(),
  { icon: 'package' },
)

const headingId = useId()
</script>

<template>
  <section class="empty-state-card" :aria-labelledby="headingId">
    <AppIcon class="empty-state-card__icon" :name="icon" />
    <h3 :id="headingId" class="empty-state-card__title">{{ title }}</h3>
    <p class="empty-state-card__description">{{ description }}</p>
    <div v-if="$slots.actions" class="empty-state-card__actions">
      <slot name="actions" />
    </div>
  </section>
</template>

<style scoped>
.empty-state-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 28px 32px;
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
  color: #233d37;
  text-align: center;
}

.empty-state-card__icon {
  width: 1.5rem;
  height: 1.5rem;
  margin-bottom: 12px;
  color: #53675a;
}

.empty-state-card__title {
  max-width: 100%;
  margin-bottom: 8px;
  color: #233d37;
  font-size: 1.0625rem;
  font-weight: 650;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.empty-state-card__description {
  max-width: 50ch;
  color: #53675a;
  font-size: 0.9375rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.empty-state-card__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px;
  max-width: 100%;
  margin-top: 20px;
}
</style>
