<script setup lang="ts">
import { computed, shallowRef, useTemplateRef, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { usePullToRefresh } from '../composables/usePullToRefresh'
import { deliveryCopy as copy } from '../lib/delivery-copy'

const props = defineProps<{ busy: boolean; onRefresh: () => Promise<void> }>()
const container = useTemplateRef<HTMLElement>('container')
const { distance, armed, refreshing } = usePullToRefresh(container, {
  disabled: () => props.busy,
  onRefresh: () => props.onRefresh(),
})
const awaitingUpdates = shallowRef(false)
watch(
  [refreshing, () => props.busy],
  ([active, busy]) => {
    if (active) awaitingUpdates.value = true
    else if (!busy) awaitingUpdates.value = false
  },
  { flush: 'sync' },
)
const showingRefresh = computed(
  () => refreshing.value || (awaitingUpdates.value && props.busy),
)
const label = computed(() =>
  showingRefresh.value
    ? copy.pullRefreshing
    : armed.value
      ? copy.pullRelease
      : copy.pullHint,
)
</script>

<template>
  <div
    ref="container"
    class="pull-to-refresh"
    :class="{
      'pull-to-refresh--pulling': distance > 0 && !showingRefresh,
      'pull-to-refresh--refreshing': showingRefresh,
    }"
    :style="{ '--pull-distance': `${distance}px` }"
  >
    <div
      class="pull-to-refresh__indicator content-inset"
      :class="{
        'pull-to-refresh__indicator--visible': distance > 0 || showingRefresh,
      }"
      :aria-hidden="distance === 0 && !showingRefresh"
    >
      <span role="status">{{ label }}</span>
      <AppIcon :name="showingRefresh ? 'loading' : 'refresh'" />
    </div>
    <div class="pull-to-refresh__content" :aria-busy="refreshing || busy">
      <slot />
    </div>
  </div>
</template>

<style scoped>
.pull-to-refresh {
  position: relative;
  --content-offset: var(--pull-distance, 0px);
}
.pull-to-refresh--refreshing {
  --content-offset: max(var(--pull-distance), 3rem);
}
.pull-to-refresh__indicator {
  position: absolute;
  inset: 0 0 auto;
  display: flex;
  height: var(--content-offset);
  align-items: center;
  gap: 8px;
  overflow: hidden;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
  opacity: 0;
  pointer-events: none;
}
.pull-to-refresh__indicator--visible {
  opacity: 1;
}
.pull-to-refresh__content {
  transform: translateY(var(--content-offset));
}
@media (prefers-reduced-motion: no-preference) {
  .pull-to-refresh__content {
    transition: transform 180ms ease-out;
  }
  .pull-to-refresh--pulling .pull-to-refresh__content {
    transition: none;
  }
}
</style>
