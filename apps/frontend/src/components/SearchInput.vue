<script setup lang="ts">
import { useId, useTemplateRef } from 'vue'
import AppIcon from './AppIcon.vue'

const model = defineModel<string>({ required: true })
const props = defineProps<{
  label: string
  placeholder: string
  clearLabel: string
  controls?: string
}>()

const inputId = useId()
const input = useTemplateRef<HTMLInputElement>('input')

function clearSearch() {
  model.value = ''
  input.value?.focus()
}
</script>

<template>
  <div class="search-input">
    <label class="search-input__label content-inset" :for="inputId">{{
      props.label
    }}</label>
    <div class="search-input__control">
      <input
        :id="inputId"
        ref="input"
        v-model="model"
        class="search-input__field"
        type="search"
        :placeholder="props.placeholder"
        maxlength="200"
        autocomplete="off"
        :aria-controls="props.controls"
      />
      <button
        v-if="model.length > 0"
        class="search-input__clear"
        type="button"
        :aria-label="props.clearLabel"
        @click="clearSearch"
      >
        <AppIcon name="close" />
      </button>
      <AppIcon v-else class="search-input__icon" name="search" />
    </div>
  </div>
</template>

<style scoped>
.search-input {
  display: grid;
  gap: 8px;
  width: 100%;
  min-width: 0;
}

.search-input__label {
  max-width: 100%;
  margin: 0;
  color: #233d37;
  font-size: 0.875rem;
  font-weight: 600;
  line-height: 1.45;
  overflow-wrap: anywhere;
}

.search-input__control {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  min-height: 48px;
  padding-block: 2px;
  padding-inline: var(--card-inset);
  border: 1px solid #d6ded0;
  border-radius: 8px;
  background: #fffefa;
  color: #53675a;
}

.search-input__control:focus-within {
  border-color: #8da88e;
  outline: 2px solid #8da88e;
  outline-offset: 2px;
}

.search-input__icon {
  flex: none;
  width: 1.25rem;
  height: 1.25rem;
  color: #53675a;
}

.search-input__field {
  flex: 1 1 auto;
  width: 100%;
  min-width: 0;
  min-height: 44px;
  margin: 0;
  padding: 8px 0;
  border: 0;
  border-radius: 0;
  outline: 0;
  background: transparent;
  color: #233d37;
  font-size: 1rem;
  line-height: 1.4;
}

.search-input__field::placeholder {
  color: #53675a;
  opacity: 1;
}

.search-input__field::-webkit-search-cancel-button {
  -webkit-appearance: none;
  appearance: none;
}

.search-input__clear {
  display: grid;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: #53675a;
}

.search-input__clear:hover {
  background: #eef2e8;
  color: #233d37;
}

.search-input__clear:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 1px;
}
</style>
