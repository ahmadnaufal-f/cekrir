<script setup lang="ts">
import { computed } from 'vue'
import DeliveryResourceStates from './DeliveryResourceStates.vue'
import { deliveryCopy, formatDeliveryTimestamp } from '../lib/delivery-copy'
import { deliveryRoute } from '../lib/navigation'
import { ui } from '../lib/strings'
import type { DeliverySummary } from '../types/app'

const props = defineProps<{
  delivery: Pick<
    DeliverySummary,
    | 'id'
    | 'trackingNumber'
    | 'courier'
    | 'scannedAt'
    | 'photoState'
    | 'trackingState'
  >
  href?: string
  isNew?: boolean
  timestampLabel?: string
}>()
const emit = defineEmits<{ open: [id: string] }>()
const timestamp = computed(() =>
  formatDeliveryTimestamp(props.delivery.scannedAt),
)
function openDelivery(event: MouseEvent) {
  if (
    event.button !== 0 ||
    event.ctrlKey ||
    event.metaKey ||
    event.shiftKey ||
    event.altKey
  )
    return
  event.preventDefault()
  emit('open', props.delivery.id)
}
</script>

<template>
  <a
    class="delivery-card"
    :href="href ?? `#${deliveryRoute(delivery.id)}`"
    @click="openDelivery"
  >
    <div class="delivery-card__information">
      <div class="delivery-card__heading">
        <strong class="delivery-card__number">{{
          delivery.trackingNumber
        }}</strong>
        <span v-if="isNew" class="delivery-card__badge">{{
          deliveryCopy.newBadge
        }}</span>
      </div>
      <span class="delivery-card__courier">{{
        delivery.courier?.name || deliveryCopy.unknownCourier
      }}</span>
      <time
        class="delivery-card__time"
        :datetime="delivery.scannedAt"
        :aria-label="`${timestampLabel ?? ui.scannedAt}: ${timestamp}`"
        >{{ timestamp }}</time
      >
      <slot />
    </div>
    <DeliveryResourceStates
      :photo-state="delivery.photoState"
      :tracking-state="delivery.trackingState"
    />
  </a>
</template>

<style scoped>
.delivery-card {
  display: flex;
  min-width: 0;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding-block: 22px;
  padding-inline: var(--card-inset);
  border: 1px solid #dfe4d9;
  border-radius: 12px;
  background: #fffefa;
  color: #233d37;
  text-decoration: none;
}
.delivery-card:hover {
  border-color: #a8b9a5;
  background: #fafbf6;
}
.delivery-card:focus-visible {
  outline-offset: 3px;
}
.delivery-card__information {
  display: grid;
  min-width: 0;
  gap: 5px;
}
.delivery-card__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px 8px;
}
.delivery-card__number {
  overflow-wrap: anywhere;
  font-size: 1rem;
  font-weight: 650;
  line-height: 1.4;
}
.delivery-card__badge {
  padding: 2px 8px;
  border-radius: 999px;
  background: #e2eee4;
  color: var(--accent);
  font-size: 0.75rem;
  font-weight: 650;
  line-height: 1.45;
}
.delivery-card__courier {
  overflow-wrap: anywhere;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.5;
}
.delivery-card__time {
  margin-top: 3px;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}
@media (max-width: 640px) {
  .delivery-card {
    flex-direction: column;
    align-items: flex-start;
    gap: 14px;
    padding-block: 20px;
  }
}
@media (prefers-reduced-motion: no-preference) {
  .delivery-card {
    transition:
      background-color 160ms ease-out,
      border-color 160ms ease-out;
  }
}
</style>
