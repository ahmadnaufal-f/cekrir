<script setup lang="ts">
import type { Shipment } from '../types/api'
import StatusBadge from './StatusBadge.vue'

defineProps<{ shipment: Shipment; refreshing: boolean }>()
defineEmits<{ refresh: [id: string] }>()

function formatDate(value: string): string {
  return new Date(value).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}
</script>

<template>
  <article class="shipment-card">
    <div class="shipment-card__heading">
      <div>
        <span class="eyebrow"
          >{{ shipment.courier }}
          <span v-if="shipment.provider === 'demo'">· Demo</span></span
        >
        <h3>{{ shipment.resi_number }}</h3>
      </div>
      <StatusBadge :status="shipment.status" />
    </div>
    <p>{{ shipment.summary }}</p>
    <div class="shipment-card__meta">
      <span>{{
        shipment.source === 'camera'
          ? `Camera · ${shipment.camera_id}`
          : 'Added manually'
      }}</span>
      <span>Checked {{ formatDate(shipment.checked_at) }}</span>
    </div>
    <details v-if="shipment.history.length">
      <summary>Tracking history</summary>
      <ol class="history">
        <li
          v-for="(event, index) in shipment.history"
          :key="`${event.occurred_at}-${index}`"
        >
          <strong>{{ event.description }}</strong>
          <span
            >{{ event.location ? `${event.location} · ` : ''
            }}{{ formatDate(event.occurred_at) }}</span
          >
        </li>
      </ol>
    </details>
    <button
      class="button button--quiet"
      :disabled="refreshing"
      @click="$emit('refresh', shipment.id)"
    >
      {{ refreshing ? 'Checking…' : 'Check for updates' }}
      <span aria-hidden="true">↗</span>
    </button>
  </article>
</template>
