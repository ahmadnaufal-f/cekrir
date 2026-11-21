<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import type {
  ApiServices,
  PackageNotification,
  User,
} from './features/api/contracts'
import {
  deviceGuideRoutes,
  parseApiRoute,
  shipmentRoute,
  type Route,
} from './features/api/routes'
import ApiAuth from './features/ApiAuth.vue'
import ShipmentView from './features/ShipmentView.vue'
import UserRoles from './features/UserRoles.vue'
import AppHeader from './components/AppHeader.vue'
import AppNavigation from './components/AppNavigation.vue'
import PageHeader from './components/PageHeader.vue'
import ShipmentAlert from './components/ShipmentAlert.vue'
import ShipmentNotificationSettings from './components/ShipmentNotificationSettings.vue'
import DevicesScreen from './screens/DevicesScreen.vue'
import DeviceSetupScreen from './screens/DeviceSetupScreen.vue'
import { deviceGuideServices } from './lib/setup-reference'
import { ui } from './lib/strings'
import type { DeviceCategory } from './types/device-ui'
const { services } = defineProps<{ services: ApiServices }>()
const user = shallowRef<User | null>(services.user())
const accountName = computed(() => user.value?.full_name?.trim())
const isAdmin = computed(() => user.value?.role === 'admin')
const modeLabel = computed(() =>
  services.mode === 'mock' ? 'Demo · data simulasi' : 'Mode live',
)
const route = ref<Route>(parseApiRoute(location.hash))
const id = computed(() =>
  route.value.startsWith('/shipments/')
    ? decodeURIComponent(route.value.slice(11))
    : null,
)
const inSettings = computed(() => route.value === '/settings')
const revision = ref(0)
const liveStatus = ref('unavailable')
const alert = shallowRef<PackageNotification | null>(null)
const shipmentNotificationsEnabled = ref(true)
const notice = ref('')
const deviceCategory = shallowRef<DeviceCategory>('esp32')
const registrationRequest = shallowRef<DeviceCategory | null>(null)
const guideKind = computed(() => {
  if (route.value === deviceGuideRoutes.esp32) return 'esp32'
  if (route.value === deviceGuideRoutes.bardi) return 'bardi'
  return null
})
const inDeviceGuide = computed(() => isAdmin.value && guideKind.value !== null)
const inFocusedPage = computed(
  () => !!user.value && (inDeviceGuide.value || id.value !== null),
)
const showNavigation = computed(
  () => !!user.value && !inSettings.value && !inFocusedPage.value,
)
const deviceServices = computed(
  () =>
    services.devices && {
      mode: services.mode,
      devices: services.devices,
    },
)
let pendingLink = resumableLink(route.value)
let disconnect: (() => void) | null = null
function navigate(value: Route, replace = false) {
  route.value = value
  if (replace) history.replaceState(null, '', `#${value}`)
  else if (value === '/settings' && location.hash !== '#/settings')
    history.pushState({ settingsOpenedInApp: true }, '', '#/settings')
  else location.hash = value
}
function resumableLink(path: Route): Route | null {
  return path.startsWith('/shipments/') || path.startsWith('/devices/')
    ? path
    : null
}
function openDeviceGuide(kind: DeviceCategory) {
  navigate(deviceGuideRoutes[kind])
}
function leaveDeviceGuide(register = false) {
  registrationRequest.value = register ? guideKind.value : null
  navigate('/devices')
}
function backFromSettings() {
  if (history.state?.settingsOpenedInApp) history.back()
  else navigate('/shipments', true)
}
function focusMain() {
  document.getElementById('main-content')?.focus()
}
function changedHash() {
  route.value = parseApiRoute(location.hash)
}
function openShipment(value: string) {
  navigate(shipmentRoute(value))
}
function openShipmentAlert(shipmentId: string) {
  openShipment(shipmentId)
  alert.value = null
}
function shipmentNotificationKey(userId: string) {
  return `cekrir:${services.mode}:shipment-notifications:${userId}`
}
function readShipmentNotificationSetting(userId: string) {
  try {
    return localStorage.getItem(shipmentNotificationKey(userId)) !== 'off'
  } catch {
    return true
  }
}
function setShipmentNotifications(enabled: boolean) {
  if (!user.value) return
  shipmentNotificationsEnabled.value = enabled
  if (!enabled) alert.value = null
  try {
    localStorage.setItem(
      shipmentNotificationKey(user.value.id),
      enabled ? 'on' : 'off',
    )
  } catch {
    // Keep the preference for the current session if storage is unavailable.
  }
}
function logout() {
  pendingLink = null
  alert.value = null
  services.auth.logout()
  notice.value = 'Anda telah keluar.'
  navigate('/login', true)
}
const unsubscribe = services.subscribe((next) => {
  const previous = user.value
  user.value = next
  if (!next && previous) {
    notice.value = 'Sesi berakhir. Silakan masuk lagi.'
    pendingLink = resumableLink(route.value)
    alert.value = null
    navigate('/login', true)
  }
  if (next && !previous) {
    notice.value = ''
    deviceCategory.value = 'esp32'
    registrationRequest.value = null
    const target = pendingLink
    pendingLink = null
    navigate(target || '/shipments', true)
  }
})
watch(
  () => user.value?.id,
  (value) => {
    disconnect?.()
    disconnect = null
    alert.value = null
    shipmentNotificationsEnabled.value = value
      ? readShipmentNotificationSetting(value)
      : true
    if (value)
      disconnect = services.notifications.connect({
        event(notification) {
          if (shipmentNotificationsEnabled.value) alert.value = notification
          revision.value++
        },
        ready() {
          revision.value++
        },
        status(status) {
          liveStatus.value = status
        },
      })
  },
  { immediate: true },
)
watch(
  [route, () => user.value?.role],
  () => {
    if (!user.value && route.value !== '/login') {
      pendingLink = resumableLink(route.value)
      navigate('/login', true)
    } else if (
      user.value &&
      (route.value === '/login' ||
        ((route.value === '/members' || route.value.startsWith('/devices')) &&
          !isAdmin.value))
    )
      navigate('/shipments', true)
  },
  { immediate: true },
)
watch(guideKind, (kind) => {
  if (kind) deviceCategory.value = kind
})
watch(route, (value) => {
  if (value !== '/devices') registrationRequest.value = null
  queueMicrotask(() => {
    window.scrollTo(0, 0)
    document.getElementById('main-content')?.focus({ preventScroll: true })
  })
})
function resume() {
  if (document.visibilityState === 'visible') revision.value++
}
onMounted(() => {
  window.addEventListener('hashchange', changedHash)
  document.addEventListener('visibilitychange', resume)
})
onUnmounted(() => {
  unsubscribe()
  disconnect?.()
  window.removeEventListener('hashchange', changedHash)
  document.removeEventListener('visibilitychange', resume)
})
</script>
<template>
  <div
    class="app-shell api-shell"
    :class="{ 'api-shell--auth': !user, 'api-shell--with-nav': showNavigation }"
  >
    <a class="skip-link" href="#main-content" @click.prevent="focusMain"
      >Lewati ke konten</a
    >
    <AppHeader
      v-if="!inFocusedPage"
      :key="user?.id ?? 'signed-out'"
      :signed-in="!!user"
      :display-name="accountName"
      :account-current="inSettings"
      :mode-label="modeLabel"
      @navigate="navigate"
      @back="backFromSettings"
      @logout="logout"
    />
    <p v-if="notice" class="banner" role="status">{{ notice }}</p>
    <ShipmentAlert
      v-if="alert && user && route !== '/shipments'"
      :notification="alert"
      @open="openShipmentAlert"
      @dismiss="alert = null"
    />
    <main id="main-content" tabindex="-1">
      <ApiAuth v-if="!user" :services="services" />
      <template v-else>
        <ShipmentView
          v-if="route.startsWith('/shipments')"
          :key="`shipments:${user.id}:${user.role}`"
          :services="services"
          :user="user"
          :id="id"
          :revision="revision"
          :notified-shipment-id="alert?.shipment_id"
          @open="openShipment"
          @back="navigate('/shipments')"
        >
          <template #after-summary>
            <ShipmentAlert
              v-if="alert"
              :notification="alert"
              @open="openShipmentAlert"
              @dismiss="alert = null"
            />
          </template>
        </ShipmentView>
        <DevicesScreen
          v-else-if="route === '/devices' && isAdmin"
          :key="`devices:${user.id}`"
          v-model:category="deviceCategory"
          :services="deviceServices"
          :user="user"
          :registration-request="registrationRequest"
          @guide="openDeviceGuide"
          @registration-handled="registrationRequest = null"
          @session-expired="services.auth.logout()"
        />
        <DeviceSetupScreen
          v-else-if="guideKind && isAdmin"
          :key="`device-guide:${guideKind}`"
          :services="deviceGuideServices"
          :user="user"
          :kind="guideKind"
          :can-register="!!deviceServices"
          @back="leaveDeviceGuide()"
          @register="leaveDeviceGuide(true)"
          @session-expired="services.auth.logout()"
        />
        <UserRoles
          v-else-if="route === '/members' && isAdmin"
          :key="`members:${user.id}`"
          :services="services"
          :current-user-id="user.id"
        />
        <section
          v-else-if="inSettings"
          class="api-settings"
          aria-labelledby="settings-title"
        >
          <PageHeader
            class="api-settings__heading"
            :title="ui.settings"
            title-id="settings-title"
          />
          <article class="panel">
            <h2>{{ accountName || user.email }}</h2>
            <p v-if="accountName">{{ user.email }}</p>
            <p>{{ isAdmin ? 'Admin' : 'Anggota' }}</p>
            <p class="supporting">
              Sesi disimpan sementara. Muat ulang halaman atau tutup aplikasi
              untuk mengakhiri sesi lokal. Keluar tidak mencabut token di
              server.
            </p>
            <button class="button button--quiet" @click="logout">Keluar</button>
          </article>
          <ShipmentNotificationSettings
            :key="user.id"
            :enabled="shipmentNotificationsEnabled"
            :shipments="services.shipments"
            @update:enabled="setShipmentNotifications"
            @open="openShipment"
          />
          <article class="panel">
            <h2>Ketersediaan layanan</h2>
            <p>
              Catatan paket digunakan bersama; pemisahan lokasi penerimaan belum
              tersedia.
            </p>
            <p>
              Foto pengiriman, pembayaran, dan notifikasi latar belakang belum
              tersedia di aplikasi ini.
            </p>
            <p>
              Pembaruan langsung:
              {{
                liveStatus === 'connected'
                  ? 'terhubung'
                  : services.mode === 'mock'
                    ? 'simulasi'
                    : 'sementara tidak tersedia'
              }}.
            </p>
          </article>
        </section>
      </template>
    </main>
    <AppNavigation
      v-if="showNavigation"
      :is-admin="isAdmin"
      :route="route"
      @navigate="navigate"
    />
  </div>
</template>
