<script setup lang="ts">
defineProps<{ title?: string; titleId?: string }>()
</script>

<template>
  <header class="page-header">
    <div class="page-header__row">
      <div class="page-header__title">
        <slot name="title">
          <h1 :id="titleId" class="page-title">{{ title }}</h1>
        </slot>
      </div>
      <slot name="actions" />
    </div>
    <div v-if="$slots.default" class="page-header__details">
      <slot />
    </div>
  </header>
</template>

<style scoped>
.page-header {
  margin-block: var(--page-header-offset, 1rem) var(--page-header-gap, 1.25rem);
  padding-inline: var(--page-header-inset, var(--card-text-inset, 0px));
}

.page-header__row {
  display: flex;
  min-height: var(--page-header-row-height, 48px);
  align-items: center;
  gap: 12px;
}

.page-header__title {
  min-width: 0;
  flex: 1;
}

.page-header__details {
  display: grid;
  gap: 6px;
  max-width: 68ch;
  margin-top: 24px;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.6;
}

.page-header__details:empty {
  display: none;
}
</style>
