<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from './AppIcon.vue'
import type { IconName } from './AppIcon.vue'
import { deliveryCopy } from '../lib/delivery-copy'
import { ui } from '../lib/strings'
import type { ResourceState } from '../types/app'

const props = defineProps<{
  photoState: ResourceState
  trackingState: ResourceState
}>()

const stateIcons: Record<ResourceState, IconName> = {
  ready: 'check',
  pending: 'loading',
  unavailable: 'stop',
}

const photoLabels: Record<ResourceState, string> = {
  ready: ui.photoReady,
  pending: ui.photoPending,
  unavailable: ui.photoUnavailable,
}

const trackingLabels: Record<ResourceState, string> = {
  ready: ui.trackingReady,
  pending: ui.trackingPending,
  unavailable: ui.trackingUnavailable,
}

const photoStatus = computed(() => ({
  label: photoLabels[props.photoState],
  icon: stateIcons[props.photoState],
}))

const trackingStatus = computed(() => ({
  label: trackingLabels[props.trackingState],
  icon: stateIcons[props.trackingState],
}))
</script>

<template>
  <ul
    class="delivery-resource-states"
    role="list"
    :aria-label="deliveryCopy.resourceAvailability"
  >
    <li
      class="delivery-resource-state"
      :class="`delivery-resource-state--${photoState}`"
      :aria-label="photoStatus.label"
      :title="photoStatus.label"
    >
      <AppIcon class="delivery-resource-state__icon" :name="photoStatus.icon" />
      <span class="delivery-resource-state__label">{{
        deliveryCopy.resourcePhoto
      }}</span>
    </li>
    <li
      class="delivery-resource-state"
      :class="`delivery-resource-state--${trackingState}`"
      :aria-label="trackingStatus.label"
      :title="trackingStatus.label"
    >
      <AppIcon
        class="delivery-resource-state__icon"
        :name="trackingStatus.icon"
      />
      <span class="delivery-resource-state__label">{{
        deliveryCopy.resourceTracking
      }}</span>
    </li>
  </ul>
</template>

<style scoped>
.delivery-resource-states {
  display: flex;
  flex-wrap: wrap;
  max-width: 100%;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.delivery-resource-state {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  padding: 4px 8px;
  border-radius: 999px;
  background: #f0f2e9;
  color: #53675a;
  font-size: 0.8125rem;
  font-weight: 650;
  line-height: 1.25;
}

.delivery-resource-state--pending {
  background: #f3f0e6;
  color: #6f6342;
}

.delivery-resource-state--unavailable {
  background: #f9e9df;
  color: #875334;
}

.delivery-resource-state__icon {
  width: 1rem;
  height: 1rem;
}

.delivery-resource-state__label {
  min-width: 0;
  overflow-wrap: anywhere;
}
</style>
