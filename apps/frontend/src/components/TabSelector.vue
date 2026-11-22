<script setup lang="ts">
import { computed, useTemplateRef } from 'vue'
import AppIcon, { type IconName } from './AppIcon.vue'
import type { SetupStatus, TabOption } from '../types/device-ui'

const props = defineProps<{
  id: string
  label: string
  tabs: readonly TabOption[]
}>()

const model = defineModel<string>({ required: true })
const tabList = useTemplateRef<HTMLDivElement>('tabList')
const selectedTabIndex = computed(() =>
  props.tabs.findIndex((tab) => tab.value === model.value),
)

const statusPresentation: Record<
  SetupStatus,
  { icon: IconName; label: string }
> = {
  complete: { icon: 'check', label: 'Penyiapan tersimpan' },
  incomplete: { icon: 'warning', label: 'Belum selesai disiapkan' },
  loading: { icon: 'loading', label: 'Memuat status' },
  error: { icon: 'warning', label: 'Status belum tersedia' },
}

function handleKeydown(event: KeyboardEvent, currentIndex: number) {
  if (props.tabs.length === 0) return

  let nextIndex: number
  const currentTab = event.currentTarget as HTMLButtonElement
  const direction =
    currentTab.ownerDocument.defaultView?.getComputedStyle(currentTab)
      .direction ?? 'ltr'
  const forwardKey = direction === 'rtl' ? 'ArrowLeft' : 'ArrowRight'
  const backwardKey = direction === 'rtl' ? 'ArrowRight' : 'ArrowLeft'

  if (event.key === forwardKey) {
    nextIndex = (currentIndex + 1) % props.tabs.length
  } else if (event.key === backwardKey) {
    nextIndex = (currentIndex - 1 + props.tabs.length) % props.tabs.length
  } else if (event.key === 'Home') {
    nextIndex = 0
  } else if (event.key === 'End') {
    nextIndex = props.tabs.length - 1
  } else {
    return
  }

  event.preventDefault()
  const nextTab = props.tabs[nextIndex]
  if (!nextTab) return

  model.value = nextTab.value
  tabList.value
    ?.querySelectorAll<HTMLButtonElement>('[role="tab"]')
    .item(nextIndex)
    .focus()
}
</script>

<template>
  <div class="tab-selector">
    <div
      ref="tabList"
      class="tab-selector__list"
      role="tablist"
      :aria-label="props.label"
    >
      <button
        v-for="(tab, index) in props.tabs"
        :id="`${props.id}-${tab.value}`"
        :key="tab.value"
        class="tab-selector__tab"
        :class="{ 'tab-selector__tab--selected': model === tab.value }"
        type="button"
        role="tab"
        :aria-controls="tab.panelId"
        :aria-selected="model === tab.value"
        :tabindex="
          model === tab.value || (index === 0 && selectedTabIndex === -1)
            ? 0
            : -1
        "
        @click="model = tab.value"
        @keydown="handleKeydown($event, index)"
      >
        <span class="tab-selector__label">{{ tab.label }}</span>
        <span
          v-if="tab.status"
          class="tab-selector__status"
          :class="`tab-selector__status--${tab.status}`"
        >
          <AppIcon :name="statusPresentation[tab.status].icon" />
          <span class="tab-selector__visually-hidden">
            {{ statusPresentation[tab.status].label }}
          </span>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.tab-selector {
  --tab-padding-inline: 14px;
  width: 100%;
  min-width: 0;
  color: #233d37;
}

.tab-selector__list {
  display: flex;
  gap: 4px;
  max-width: 100%;
  overflow-x: auto;
  overscroll-behavior-x: contain;
  padding: 3px calc(var(--card-inset) - var(--tab-padding-inline)) 6px;
  border-bottom: 1px solid #d6ded0;
  scrollbar-color: #b7c5b0 #eef2e8;
  scrollbar-width: thin;
}

.tab-selector__tab {
  position: relative;
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  justify-content: center;
  gap: 8px;
  max-width: 100%;
  min-width: 44px;
  min-height: 44px;
  padding: 8px var(--tab-padding-inline);
  border: 1px solid transparent;
  border-bottom: 2px solid #d6ded0;
  border-radius: 8px 8px 0 0;
  background: transparent;
  color: #53675a;
  font: inherit;
  font-size: 1rem;
  font-weight: 600;
  line-height: 1.35;
  text-align: center;
  overflow-wrap: anywhere;
  cursor: pointer;
}

.tab-selector__tab:hover {
  background: #f2f4ed;
  color: #233d37;
}

.tab-selector__tab--selected {
  border-bottom-color: #42654a;
  background: #eef2e8;
  color: #233d37;
}

.tab-selector__tab:focus-visible {
  z-index: 1;
  outline: 3px solid #b88736;
  outline-offset: 1px;
}

.tab-selector__label {
  min-width: 0;
}

.tab-selector__status {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
}

.tab-selector__status--complete {
  color: #42654a;
}

.tab-selector__status--incomplete,
.tab-selector__status--error {
  color: #875334;
}

.tab-selector__status--loading {
  color: #53675a;
}

.tab-selector__visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  clip-path: inset(50%);
}
</style>
