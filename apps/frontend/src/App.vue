<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import type { AppServices } from './services/contracts'
import type { AppUser } from './types/app'
import AppHeader from './components/AppHeader.vue'
import AppNavigation from './components/AppNavigation.vue'
import AppIcon from './components/AppIcon.vue'
import AuthScreen from './screens/AuthScreen.vue'
import DeliveriesScreen from './screens/DeliveriesScreen.vue'
import DeliveryDetailScreen from './screens/DeliveryDetailScreen.vue'
import DevicesScreen from './screens/DevicesScreen.vue'
import MembersScreen from './screens/MembersScreen.vue'
import SettingsScreen from './screens/SettingsScreen.vue'
import NotificationSettings from './screens/NotificationSettings.vue'
import { createPushController } from './composables/usePush'
import {
  createSimulatedPushBridge,
  createDevicePushBridge,
} from './lib/push'
import { deliveryRoute, guardRoute, useNavigation } from './lib/navigation'
import { ui, errorMessage } from './lib/strings'
import { shellCopy as copy } from './lib/shell-copy'

const { services } = defineProps<{ services: AppServices }>()
const user = shallowRef<AppUser | null>(null)
const ready = shallowRef(false)
const refreshKey = shallowRef(0)
const signingOut = shallowRef(false)
const notice = shallowRef('')
const { requested, navigate } = useNavigation()
let pendingDirectLink = requested.value.startsWith('/deliveries/')
  ? requested.value
  : null
const route = computed(() => guardRoute(requested.value, user.value))
const deliveryId = computed(() =>
  route.value.startsWith('/deliveries/')
    ? decodeURIComponent(route.value.slice(12))
    : null,
)
const bridge =
  services.mode === 'mock' && import.meta.env.DEV
    ? createSimulatedPushBridge()
    : createDevicePushBridge()
const push = createPushController({
  bridge,
  service: services.push,
  user,
  navigationReady: ready,
  onNavigate(id) {
    if (!ready.value || !user.value) return false
    navigate(deliveryRoute(id))
    return true
  },
  onRefresh() {
    refreshKey.value++
  },
})
const pushState = push.state
let disposed = false
watch([user, requested, ready], () => {
  if (!ready.value) return
  if (!user.value && requested.value.startsWith('/deliveries/'))
    pendingDirectLink = requested.value
  const target = guardRoute(requested.value, user.value)
  if (target !== requested.value) navigate(target, true)
})
function authenticated(next: AppUser) {
  user.value = next
  notice.value = ''
  // The detail service reauthorizes this ID against the newly signed-in household.
  const target = pendingDirectLink
  pendingDirectLink = null
  if (!pushState.value.pendingNavigation)
    navigate(target || '/deliveries', true)
}
function expired() {
  pendingDirectLink = deliveryId.value ? deliveryRoute(deliveryId.value) : null
  // A 401 invalidates UI state; the push controller rejects stale account work.
  user.value = null
  notice.value = copy.sessionExpired
  navigate('/login', true)
}
async function logout() {
  if (signingOut.value) return
  signingOut.value = true
  notice.value = ''
  try {
    if (!(await push.beforeLogout())) {
      notice.value = copy.logoutFailed
      return
    }
    await services.auth.logout()
    pendingDirectLink = null
    user.value = null
    refreshKey.value++
    navigate('/login', true)
    notice.value = copy.signedOut
  } catch (cause) {
    notice.value = errorMessage(cause)
  } finally {
    signingOut.value = false
  }
}
function simulate(tap: boolean) {
  if (!import.meta.env.DEV || services.mode !== 'mock' || !user.value) return
  const payload = {
    type: 'delivery.created',
    eventId: `demo-event-${user.value.id}`,
    deliveryId: 'delivery-demo-complete',
    householdId: user.value.householdId,
  }
  if (tap) push.simulateTap(payload)
  else push.simulateReceived(payload)
}
function resume() {
  if (document.visibilityState === 'visible') refreshKey.value++
}
function focusMain() {
  document.getElementById('main-content')?.focus({ preventScroll: true })
}
watch(route, () => {
  queueMicrotask(() => {
    window.scrollTo(0, 0)
    focusMain()
  })
})
onMounted(async () => {
  document.addEventListener('visibilitychange', resume)
  try {
    const restored = await services.auth.restore()
    if (!disposed) user.value = restored
  } catch (cause) {
    if (!disposed) notice.value = errorMessage(cause)
  } finally {
    if (!disposed) {
      ready.value = true
      push.setNavigationReady(true)
    }
  }
})
onUnmounted(() => {
  disposed = true
  document.removeEventListener('visibilitychange', resume)
  push.dispose()
})
</script>

<template>
  <div class="app-shell" :class="{ 'app-shell--authenticated': user }">
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">{{
      copy.skip
    }}</a>
    <AppHeader :user="user" :route="route" @navigate="navigate" />
    <p class="app-status">
      <span class="mode-label">{{
        services.mode === 'mock' ? ui.mock : ui.live
      }}</span>
    </p>
    <p v-if="services.mode === 'mock'" class="mode-note">{{ ui.mockNote }}</p>
    <div v-if="notice" class="banner session-banner" role="status">
      {{ notice }}
    </div>
    <main id="main-content" class="main-content" tabindex="-1">
      <p v-if="!ready" role="status">{{ copy.restore }}</p>
      <template v-else>
        <aside
          v-if="pushState.banner && user"
          class="banner push-banner"
          role="status"
        >
          <p>{{ ui.deliveries }}</p>
          <button class="button button--primary" @click="push.tapBanner()">
            <AppIcon name="package" />
            {{ copy.navigateDelivery }}</button
          ><button class="text-button" @click="push.dismissBanner()">
            <AppIcon name="close" />
            {{ copy.dismiss }}
          </button>
        </aside>
        <div v-if="services.mode === 'live'" class="banner live-note">
          <strong>{{ copy.unavailable }}</strong>
          <p>{{ copy.liveHelp }}</p>
        </div>
        <AuthScreen
          v-if="!user"
          :key="route"
          :services="services"
          :signup="route === '/signup'"
          @authenticated="authenticated"
          @switch="navigate(route === '/signup' ? '/login' : '/signup')"
        />
        <template v-else>
          <DeliveryDetailScreen
            v-if="deliveryId"
            :key="`${user.id}:${deliveryId}`"
            :services="services"
            :user="user"
            :delivery-id="deliveryId"
            :refresh-key="refreshKey"
            @back="navigate('/deliveries')"
            @session-expired="expired"
          />
          <DeliveriesScreen
            v-else-if="route === '/deliveries'"
            :key="user.id"
            :services="services"
            :user="user"
            :refresh-key="refreshKey"
            @open="navigate(deliveryRoute($event))"
            @session-expired="expired"
          />
          <DevicesScreen
            v-else-if="route === '/devices' && user.role === 'admin'"
            :key="user.id"
            :services="services"
            :user="user"
            @session-expired="expired"
          />
          <MembersScreen
            v-else-if="route === '/members' && user.role === 'admin'"
            :key="user.id"
            :services="services"
            :user="user"
            @session-expired="expired"
          />
          <SettingsScreen
            v-else
            :user="user"
            :signing-out="signingOut"
            @logout="logout"
            ><NotificationSettings
              :state="pushState"
              @enable="push.enable()"
              @retry="push.retry()"
              @simulate-received="simulate(false)"
              @simulate-tap="simulate(true)"
              @tap-banner="push.tapBanner()"
              @dismiss-banner="push.dismissBanner()"
          /></SettingsScreen>
        </template>
      </template>
    </main>
    <footer>{{ copy.privacy }}</footer>
    <AppNavigation
      v-if="user"
      :role="user.role"
      :route="route"
      @navigate="navigate"
    />
  </div>
</template>
