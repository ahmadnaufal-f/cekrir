<script setup lang="ts">
import type { ShipmentStatus } from '../types/api'

defineProps<{ status: ShipmentStatus }>()

const labels: Record<ShipmentStatus, string> = {
  pending: 'Pending',
  in_transit: 'In transit',
  delivered: 'Delivered',
  exception: 'Needs attention',
}
</script>

<template>
  <span class="status" :class="`status--${status}`">{{ labels[status] }}</span>
</template>
