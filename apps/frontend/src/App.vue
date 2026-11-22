<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import { RouterView, useRoute, useRouter } from 'vue-router'
import type {
  ApiServices,
  PackageNotification,
  User,
} from './features/api/contracts'
import AppHeader from './components/AppHeader.vue'
import AppNavigation from './components/AppNavigation.vue'
import ShipmentAlert from './components/ShipmentAlert.vue'
import { deviceGuideServices } from './lib/setup-reference'
import { loginRoute, signedInRoute } from './router'
import type { DeviceCategory } from './types/device-ui'
const { services } = defineProps<{ services: ApiServices }>()
const router = useRouter()
const route = useRoute()
const user = shallowRef<User | null>(services.user())
const accountName = computed(() => user.value?.full_name?.trim())
const isAdmin = computed(() => user.value?.role === 'admin')
const modeLabel = computed(() =>
  services.mode === 'mock' ? 'Demo · data simulasi' : 'Mode live',
)
const onShipmentList = computed(() => route.name === 'shipments')
const inSettings = computed(() => route.name === 'settings')
const revision = ref(0)
const liveStatus = ref('unavailable')
const alert = shallowRef<PackageNotification | null>(null)
const shipmentNotificationsEnabled = ref(true)
const notice = ref('')
const deviceCategory = shallowRef<DeviceCategory>('esp32')
const registrationRequest = shallowRef<DeviceCategory | null>(null)
const guideKind = computed(() => route.meta.guide)
const inFocusedPage = computed(
  () =>
    !!user.value &&
    (route.name === 'shipment-detail' || (isAdmin.value && !!guideKind.value)),
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
let disconnect: (() => void) | null = null
let signingOut = false
function openDeviceGuide(kind: DeviceCategory) {
  void router.push({ name: kind === 'esp32' ? 'esp32-setup' : 'bardi-setup' })
}
function leaveDeviceGuide(register = false) {
  registrationRequest.value = register ? (guideKind.value ?? null) : null
  void router.push({ name: 'devices' })
}
function backFromSettings() {
  if (router.options.history.state.settingsOpenedInApp) router.back()
  else void router.replace({ name: 'shipments' })
}
function focusMain() {
  document.getElementById('main-content')?.focus()
}
function openShipment(value: string) {
  void router.push({ name: 'shipment-detail', params: { id: value } })
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
  signingOut = true
  services.auth.logout()
  signingOut = false
}
const unsubscribe = services.subscribe((next) => {
  const previous = user.value
  user.value = next
  if (!next && previous) {
    notice.value = signingOut
      ? 'Anda telah keluar.'
      : 'Sesi berakhir. Silakan masuk lagi.'
    alert.value = null
    void router.replace(signingOut ? { name: 'login' } : loginRoute(route))
  }
  if (next && !previous) {
    notice.value = ''
    deviceCategory.value = 'esp32'
    registrationRequest.value = null
    void router.replace(signedInRoute(router, route.query.redirect))
  }
  if (next && previous && route.meta.requiresAdmin && next.role !== 'admin')
    void router.replace({ name: 'shipments' })
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
  guideKind,
  (kind) => {
    if (kind) deviceCategory.value = kind
  },
  { immediate: true },
)
watch(
  () => route.fullPath,
  () => {
    if (route.name !== 'devices') registrationRequest.value = null
    document.getElementById('main-content')?.focus({ preventScroll: true })
  },
  { flush: 'post' },
)

const screenKey = computed(() => {
  const account = user.value
  return onShipmentList.value || route.name === 'shipment-detail'
    ? `shipments:${account?.id}:${account?.role}`
    : `${String(route.name)}:${account?.id}`
})

const screenBindings = computed(() => {
  const account = user.value
  if (route.name === 'login') return { services }
  if (!account || (route.meta.requiresAdmin && account.role !== 'admin'))
    return null

  switch (route.name) {
    case 'shipments':
    case 'shipment-detail':
      return {
        services,
        user: account,
        id: typeof route.params.id === 'string' ? route.params.id : null,
        revision: revision.value,
        notifiedShipmentId: alert.value?.shipment_id,
        onOpen: openShipment,
        onBack: () => router.push({ name: 'shipments' }),
      }
    case 'devices':
      return {
        category: deviceCategory.value,
        'onUpdate:category': (kind: DeviceCategory) =>
          (deviceCategory.value = kind),
        services: deviceServices.value,
        user: account,
        registrationRequest: registrationRequest.value,
        onGuide: openDeviceGuide,
        onRegistrationHandled: () => (registrationRequest.value = null),
        onSessionExpired: () => services.auth.logout(),
      }
    case 'esp32-setup':
    case 'bardi-setup':
      return {
        services: deviceGuideServices,
        user: account,
        kind: guideKind.value,
        canRegister: !!deviceServices.value,
        onBack: () => leaveDeviceGuide(),
        onRegister: () => leaveDeviceGuide(true),
        onSessionExpired: () => services.auth.logout(),
      }
    case 'members':
      return { services, currentUserId: account.id }
    case 'settings':
      return {
        services,
        user: account,
        liveStatus: liveStatus.value,
        notifications: shipmentNotificationsEnabled.value,
        'onUpdate:notifications': setShipmentNotifications,
        onOpen: openShipment,
        onLogout: logout,
      }
    default:
      return null
  }
})
function resume() {
  if (document.visibilityState === 'visible') revision.value++
}
onMounted(() => {
  document.addEventListener('visibilitychange', resume)
})
onUnmounted(() => {
  unsubscribe()
  disconnect?.()
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
      @back="backFromSettings"
      @logout="logout"
    />
    <p v-if="notice" class="banner" role="status">{{ notice }}</p>
    <ShipmentAlert
      v-if="alert && user && !onShipmentList"
      :notification="alert"
      @open="openShipmentAlert"
      @dismiss="alert = null"
    />
    <main id="main-content" tabindex="-1">
      <RouterView v-slot="{ Component }">
        <component
          :is="Component"
          v-if="Component && screenBindings"
          :key="screenKey"
          v-bind="screenBindings"
        >
          <template v-if="onShipmentList" #after-summary>
            <ShipmentAlert
              v-if="alert"
              :notification="alert"
              @open="openShipmentAlert"
              @dismiss="alert = null"
            />
          </template>
        </component>
      </RouterView>
    </main>
    <AppNavigation v-if="showNavigation" :is-admin="isAdmin" />
  </div>
</template>
