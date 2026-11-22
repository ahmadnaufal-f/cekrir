<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import type { ApiServices } from '../features/api/contracts'
import {
  canSendDeviceNotification,
  requestNotificationPermission,
  scheduleTestNotification,
} from '../lib/notifications'

const props = defineProps<{
  enabled: boolean
  accountId: string
  checkingPermission: boolean
  preferenceMessage: string
  shipments: ApiServices['shipments']
}>()
const emit = defineEmits<{
  'update:enabled': [value: boolean]
}>()

const canTest = canSendDeviceNotification()
const testRequest = shallowRef<AbortController | null>(null)
const testMessage = shallowRef('')

function resetTest() {
  testRequest.value?.abort()
  testRequest.value = null
  testMessage.value = ''
}

async function testNotification() {
  if (
    !props.enabled ||
    !canTest ||
    props.checkingPermission ||
    testRequest.value
  )
    return
  const request = new AbortController()
  testRequest.value = request
  testMessage.value = ''
  const accountId = props.accountId
  try {
    const permitted = await requestNotificationPermission()
    if (request.signal.aborted) return
    if (!permitted) {
      testMessage.value =
        'Izinkan notifikasi Cekrir di pengaturan perangkat untuk menjalankan tes.'
      return
    }

    const signal = AbortSignal.any([request.signal, AbortSignal.timeout(2500)])
    const page = await props.shipments.list(0, signal).catch(() => null)
    if (request.signal.aborted) return
    await scheduleTestNotification(
      accountId,
      page?.items[0]?.id,
      () => !request.signal.aborted,
    )
    if (!request.signal.aborted)
      testMessage.value =
        'Notifikasi tes dikirim. Periksa panel notifikasi perangkat.'
  } catch {
    if (!request.signal.aborted)
      testMessage.value = 'Notifikasi tes belum dapat dikirim. Coba lagi.'
  } finally {
    if (testRequest.value === request) testRequest.value = null
  }
}

watch(
  () => props.enabled,
  (enabled) => {
    if (!enabled) resetTest()
  },
)
onUnmounted(resetTest)
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
          {{
            canTest
              ? 'Tampilkan notifikasi paket di aplikasi dan di panel notifikasi perangkat.'
              : 'Tampilkan notifikasi paket saat aplikasi terbuka.'
          }}
        </p>
      </div>
      <button
        type="button"
        class="shipment-notification-settings__switch"
        role="switch"
        :aria-checked="enabled"
        :disabled="checkingPermission"
        aria-labelledby="shipment-notifications-title"
        aria-describedby="shipment-notifications-description"
        @click="emit('update:enabled', !enabled)"
      >
        <span aria-hidden="true" />
      </button>
    </div>

    <p v-if="preferenceMessage" class="supporting" role="status">
      {{ preferenceMessage }}
    </p>

    <div class="shipment-notification-settings__test">
      <button
        type="button"
        class="button button--quiet"
        :disabled="!enabled || !canTest || checkingPermission || !!testRequest"
        @click="testNotification"
      >
        {{ testRequest ? 'Mengirim…' : 'Tes notifikasi' }}
      </button>
      <p v-if="!canTest" class="supporting">
        Tes notifikasi perangkat tersedia di aplikasi Android dan iOS.
      </p>
      <p v-else-if="!enabled" class="supporting">
        Aktifkan notifikasi paket untuk menjalankan tes.
      </p>
      <p v-else class="supporting" role="status">{{ testMessage }}</p>
    </div>
  </section>
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

@media (prefers-reduced-motion: no-preference) {
  .shipment-notification-settings__switch span {
    transition: background-color 160ms ease-out;
  }

  .shipment-notification-settings__switch span::before {
    transition: transform 160ms ease-out;
  }
}
</style>
