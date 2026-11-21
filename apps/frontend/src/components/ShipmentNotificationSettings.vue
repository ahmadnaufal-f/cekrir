<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import type { ApiServices } from '../features/api/contracts'
import ShipmentAlert, { type ShipmentAlertContent } from './ShipmentAlert.vue'

const props = defineProps<{
  enabled: boolean
  shipments: ApiServices['shipments']
}>()
const emit = defineEmits<{
  'update:enabled': [value: boolean]
  open: [id: string]
}>()

const testAlert = shallowRef<ShipmentAlertContent | null>(null)
let testRequest: AbortController | undefined

function dismissTest() {
  testRequest?.abort()
  testAlert.value = null
}

async function testNotification() {
  testRequest?.abort()
  const request = new AbortController()
  testRequest = request
  const title = 'Tes notifikasi paket'
  testAlert.value = { title, message: 'Ini adalah contoh notifikasi paket.' }

  const page = await props.shipments.list(0, request.signal).catch(() => null)
  const shipment = page?.items[0]
  if (shipment && !request.signal.aborted) {
    testAlert.value = {
      title,
      message: `Ini adalah contoh notifikasi untuk paket ${shipment.resi_number}.`,
      shipment_id: shipment.id,
    }
  }
}

watch(
  () => props.enabled,
  (enabled) => {
    if (!enabled) dismissTest()
  },
)
onUnmounted(dismissTest)
</script>

<template>
  <section
    class="panel shipment-notification-settings"
    aria-labelledby="shipment-notifications-title"
  >
    <div class="shipment-notification-settings__row">
      <div>
        <h2 id="shipment-notifications-title">Notifikasi paket</h2>
        <p id="shipment-notifications-description" class="supporting">
          Tampilkan notifikasi paket saat aplikasi terbuka.
        </p>
      </div>
      <button
        type="button"
        class="shipment-notification-settings__switch"
        role="switch"
        :aria-checked="enabled"
        aria-labelledby="shipment-notifications-title"
        aria-describedby="shipment-notifications-description"
        @click="emit('update:enabled', !enabled)"
      >
        <span aria-hidden="true" />
      </button>
    </div>

    <div class="shipment-notification-settings__test">
      <button
        type="button"
        class="button button--quiet"
        :disabled="!enabled"
        @click="testNotification"
      >
        Tes notifikasi
      </button>
      <p v-if="!enabled" class="supporting">
        Aktifkan notifikasi paket untuk menjalankan tes.
      </p>
    </div>
  </section>
  <ShipmentAlert
    v-if="testAlert"
    class="shipment-notification-settings__preview"
    :notification="testAlert"
    @open="emit('open', $event)"
    @dismiss="dismissTest"
  />
</template>

<style scoped>
.shipment-notification-settings {
  display: grid;
  gap: 16px;
}

.shipment-notification-settings__row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.shipment-notification-settings__switch {
  display: grid;
  width: 48px;
  flex: none;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
}

.shipment-notification-settings__switch span {
  display: flex;
  width: 46px;
  height: 26px;
  align-items: center;
  padding: 3px;
  border-radius: 999px;
  background: #627366;
}

.shipment-notification-settings__switch span::before {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #fffefa;
  content: '';
}

.shipment-notification-settings__switch[aria-checked='true'] span {
  background: var(--accent);
}

.shipment-notification-settings__switch[aria-checked='true'] span::before {
  transform: translateX(20px);
}

.shipment-notification-settings__test {
  display: grid;
  justify-items: start;
  gap: 6px;
}

.shipment-notification-settings__preview {
  margin-block: 0;
}

@media (prefers-reduced-motion: no-preference) {
  .shipment-notification-settings__switch span {
    transition: background-color 160ms ease-out;
  }

  .shipment-notification-settings__switch span::before {
    transition: transform 160ms ease-out;
  }
}
</style>
