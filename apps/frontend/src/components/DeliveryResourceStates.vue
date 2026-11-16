<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import { deliveryCopy } from '../lib/delivery-copy'
import { ui } from '../lib/strings'
import type { ResourceState } from '../types/app'

const props = defineProps<{
  photoState: ResourceState
  trackingState: ResourceState
}>()

const photoLabel = computed(() => {
  if (props.photoState === 'pending') return ui.photoPending
  if (props.photoState === 'unavailable') return ui.photoUnavailable
  return ui.photoReady
})
const trackingLabel = computed(() => {
  if (props.trackingState === 'pending') return ui.trackingPending
  if (props.trackingState === 'unavailable') return ui.trackingUnavailable
  return ui.trackingReady
})
</script>

<template>
  <ul
    class="delivery-resource-states"
    :aria-label="deliveryCopy.resourceAvailability"
  >
    <li
      class="delivery-resource-state"
      :class="`delivery-resource-state--${photoState}`"
    >
      <span class="delivery-resource-state__name"
        ><AppIcon name="camera" />{{ ui.photo }}</span
      >
      <span>{{ photoLabel }}</span>
    </li>
    <li
      class="delivery-resource-state"
      :class="`delivery-resource-state--${trackingState}`"
    >
      <span class="delivery-resource-state__name"
        ><AppIcon name="tracking" />{{ deliveryCopy.resourceTracking }}</span
      >
      <span>{{ trackingLabel }}</span>
    </li>
  </ul>
</template>

<style scoped>
.delivery-resource-states {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.delivery-resource-state {
  display: inline-flex;
  align-items: baseline;
  flex-wrap: wrap;
  gap: 4px 7px;
  padding: 6px 9px;
  border-radius: 5px;
  background: #f0f2e9;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.45;
}

.delivery-resource-state--pending {
  background: #f3f0e6;
  color: #6f6342;
}

.delivery-resource-state--unavailable {
  background: #f9e9df;
  color: #875334;
}

.delivery-resource-state__name {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-weight: 650;
}
</style>
