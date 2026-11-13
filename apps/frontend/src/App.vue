<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import ShipmentCard from './components/ShipmentCard.vue'
import { api } from './lib/api'
import {
  requestNotificationPermission,
  showPackageNotification,
} from './lib/notifications'
import type { PackageNotification, Shipment } from './types/api'

const shipments = ref<Shipment[]>([])
const notifications = ref<PackageNotification[]>([])
const resiNumber = ref('')
const courier = ref('jne')
const loading = ref(true)
const saving = ref(false)
const refreshing = ref<string | null>(null)
const error = ref('')
const notice = ref('')
const notificationsEnabled = ref(false)
const permissionPending = ref(false)
const seenNotifications = new Set<string>()
let initialized = false
let loadingData = false
let pollTimer: ReturnType<typeof setInterval> | undefined

const stats = computed(() => [
  { label: 'Tracked packages', value: shipments.value.length },
  {
    label: 'On the way',
    value: shipments.value.filter((item) => item.status === 'in_transit')
      .length,
  },
  {
    label: 'Delivered',
    value: shipments.value.filter((item) => item.status === 'delivered').length,
  },
])
const hasDemo = computed(() =>
  shipments.value.some((shipment) => shipment.provider === 'demo'),
)

function message(cause: unknown): string {
  return cause instanceof Error
    ? cause.message
    : 'Something went wrong. Please try again.'
}

async function loadData(): Promise<void> {
  if (loadingData) return
  loadingData = true
  try {
    const [packages, updates] = await Promise.all([
      api.shipments(),
      api.notifications(),
    ])
    shipments.value = packages
    notifications.value = updates
    for (const update of [...updates].reverse()) {
      if (
        initialized &&
        notificationsEnabled.value &&
        !seenNotifications.has(update.id)
      ) {
        try {
          await showPackageNotification(update)
        } catch {
          notice.value =
            'Device notification could not be shown. Your updates are saved below.'
        }
      }
      seenNotifications.add(update.id)
    }
    // Bound the set to the current page of notifications in a long-running app.
    const currentIds = new Set(updates.map((update) => update.id))
    for (const id of seenNotifications)
      if (!currentIds.has(id)) seenNotifications.delete(id)
    initialized = true
    error.value = ''
  } catch (cause) {
    error.value = `Could not load package updates. ${message(cause)}`
  } finally {
    loading.value = false
    loadingData = false
  }
}

async function addShipment(): Promise<void> {
  saving.value = true
  error.value = ''
  notice.value = ''
  try {
    await api.addShipment({
      resi_number: resiNumber.value,
      courier: courier.value,
    })
    resiNumber.value = ''
    notice.value =
      'Package saved. Tracking the same resi again keeps a single entry.'
    await loadData()
  } catch (cause) {
    error.value = `Could not add package. ${message(cause)}`
  } finally {
    saving.value = false
  }
}

async function refreshShipment(id: string): Promise<void> {
  if (refreshing.value) return
  refreshing.value = id
  error.value = ''
  try {
    await api.refreshShipment(id)
    await loadData()
  } catch (cause) {
    error.value = `Could not refresh package. ${message(cause)}`
  } finally {
    refreshing.value = null
  }
}

async function enableNotifications(): Promise<void> {
  permissionPending.value = true
  try {
    notificationsEnabled.value = await requestNotificationPermission()
    notice.value = notificationsEnabled.value
      ? 'Device notifications enabled while this app is open.'
      : 'Notifications are unavailable or permission was declined. Updates remain visible here.'
  } catch (cause) {
    notice.value = `Could not enable device notifications. ${message(cause)}`
  } finally {
    permissionPending.value = false
  }
}

onMounted(() => {
  void loadData()
  pollTimer = setInterval(() => void loadData(), 10_000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <div class="app-shell">
    <header class="topbar">
      <a class="brand" href="/" aria-label="Cekrir home"
        ><span class="brand__mark" aria-hidden="true">▥</span>cekrir<span
          class="brand__dot"
          >.</span
        ></a
      >
      <span class="topbar__label">PACKAGE MONITOR</span>
      <span class="chip">Local workspace</span>
    </header>

    <main>
      <section class="intro">
        <div>
          <p class="eyebrow">FROM YOUR DOORSTEP TO YOUR DASHBOARD</p>
          <h1>A little more clarity.<br />For every delivery.</h1>
          <p class="intro__copy">
            Follow your resi numbers, collect camera detections, and keep
            package updates in one place.
          </p>
        </div>
        <div class="intro__illustration" aria-hidden="true">
          <div class="parcel">
            <span>CEKRIR</span>
            <div class="barcode"></div>
            <small>HANDLE WITH CARE</small>
          </div>
          <span class="scan-line"></span>
        </div>
      </section>

      <div v-if="error" class="banner banner--error" role="alert">
        {{ error }} <button class="text-button" @click="loadData">Retry</button>
      </div>
      <div v-if="notice" class="banner" role="status">{{ notice }}</div>

      <section
        class="stats"
        aria-label="Package overview, latest 100 shipments"
      >
        <article v-for="stat in stats" :key="stat.label">
          <span>{{ stat.label }}</span><strong>{{
            stat.value.toString().padStart(2, '0')
          }}</strong>
        </article>
      </section>

      <div class="dashboard-grid">
        <div class="packages">
          <div class="section-heading">
            <div>
              <p class="eyebrow">YOUR DELIVERIES</p>
              <h2>Package activity</h2>
            </div>
            <span class="muted">Latest 100 · updates every 10s</span>
          </div>
          <p v-if="hasDemo" class="demo-note">
            Demo tracking is active. These statuses are sample data.
          </p>
          <div v-if="loading" class="empty-state" role="status">
            Loading your packages…
          </div>
          <div v-else-if="!shipments.length" class="empty-state">
            <span class="empty-state__icon" aria-hidden="true">▥</span>
            <h3>Your next delivery starts here</h3>
            <p>
              Add a resi number to try tracking. Camera detections will appear
              here too.
            </p>
          </div>
          <div v-else class="shipment-list">
            <ShipmentCard
              v-for="shipment in shipments"
              :key="shipment.id"
              :shipment="shipment"
              :refreshing="refreshing === shipment.id"
              @refresh="refreshShipment"
            />
          </div>
        </div>

        <aside class="sidebar" aria-label="Tracking tools and notifications">
          <section class="panel add-package">
            <p class="eyebrow">A NEW ARRIVAL?</p>
            <h2>Track a package</h2>
            <form @submit.prevent="addShipment">
              <label for="resi">Resi number</label>
              <input
                id="resi"
                v-model.trim="resiNumber"
                placeholder="e.g. CEKRIR123456"
                required
                minlength="3"
                maxlength="64"
                pattern="[A-Za-z0-9-]+"
                autocomplete="off"
              />
              <label for="courier">Courier code</label>
              <input
                id="courier"
                v-model.trim="courier"
                list="couriers"
                placeholder="e.g. jne"
                required
                minlength="2"
                maxlength="32"
                pattern="[A-Za-z0-9_-]+"
              />
              <datalist id="couriers">
                <option value="jne" />
                <option value="jnt" />
                <option value="sicepat" />
                <option value="pos" />
                <option value="anteraja" />
              </datalist>
              <p class="field-help">
                Use the courier code supported by your tracking provider.
              </p>
              <button
                class="button button--primary"
                type="submit"
                :disabled="saving"
              >
                {{ saving ? 'Adding package…' : 'Track package' }}
                <span aria-hidden="true">→</span>
              </button>
            </form>
          </section>

          <section class="panel updates">
            <div class="section-heading">
              <h2>Latest updates</h2>
              <span class="count">{{ notifications.length }}</span>
            </div>
            <p v-if="!notifications.length" class="muted">
              When a package is detected or its status changes, you’ll see an
              update here.
            </p>
            <ol v-else class="notification-list">
              <li v-for="update in notifications.slice(0, 5)" :key="update.id">
                <span class="notification-dot" aria-hidden="true"></span>
                <div>
                  <strong>{{ update.title }}</strong>
                  <p>{{ update.message }}</p>
                  <time :datetime="update.created_at">{{
                    new Date(update.created_at).toLocaleString()
                  }}</time>
                </div>
              </li>
            </ol>
            <button
              class="button button--quiet"
              :disabled="permissionPending || notificationsEnabled"
              @click="enableNotifications"
            >
              {{
                notificationsEnabled
                  ? 'Notifications enabled'
                  : 'Enable device notifications'
              }}
            </button>
            <p class="field-help">Device alerts work while the app is open.</p>
          </section>
        </aside>
      </div>
      <footer>
        Cekrir <span aria-hidden="true">/</span> A watchful eye on every
        package.
      </footer>
    </main>
  </div>
</template>
