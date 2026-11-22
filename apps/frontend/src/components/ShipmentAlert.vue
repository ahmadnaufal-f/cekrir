<script setup lang="ts">
import { useRouter } from 'vue-router'
import type { PackageNotification } from '../features/api/contracts'

export type ShipmentAlertContent = Pick<
  PackageNotification,
  'title' | 'message'
> & {
  shipment_id?: string
}

const props = defineProps<{ notification: ShipmentAlertContent }>()
const emit = defineEmits<{ open: [shipmentId: string]; dismiss: [] }>()
const router = useRouter()

function openShipment() {
  const id = props.notification.shipment_id
  if (id) emit('open', id)
}
</script>

<template>
  <aside class="banner shipment-alert">
    <div class="shipment-alert__summary" role="status">
      <strong>{{ notification.title }}</strong>
      <p>{{ notification.message }}</p>
    </div>
    <div class="shipment-alert__actions">
      <a
        v-if="notification.shipment_id"
        class="text-button shipment-alert__link"
        :href="
          router.resolve({
            name: 'shipment-detail',
            params: { id: notification.shipment_id },
          }).href
        "
        @click.prevent="openShipment"
      >
        Lihat paket
      </a>
      <button
        type="button"
        class="text-button shipment-alert__dismiss"
        aria-label="Tutup notifikasi paket"
        @click="emit('dismiss')"
      >
        Tutup
      </button>
    </div>
  </aside>
</template>

<style scoped>
.shipment-alert {
  position: relative;
  margin-top: 20px;
  padding: 12px var(--card-inset) 4px;
}

.shipment-alert__summary {
  color: var(--ink);
  overflow-wrap: anywhere;
}

.shipment-alert__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: end;
  gap: 0 16px;
}

.shipment-alert__actions .text-button {
  padding-inline: 0;
}

.shipment-alert__link {
  color: var(--accent);
  font-weight: 650;
}

.shipment-alert__link::after {
  position: absolute;
  inset: 0;
  content: '';
}

.shipment-alert__dismiss {
  position: relative;
}
</style>
