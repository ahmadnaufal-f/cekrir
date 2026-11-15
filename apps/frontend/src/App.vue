<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef, watch } from 'vue'
import type { AppServices } from './services/contracts'
import type { AppUser } from './types/app'
import AuthScreen from './screens/AuthScreen.vue'
import DeliveriesScreen from './screens/DeliveriesScreen.vue'
import DeliveryDetailScreen from './screens/DeliveryDetailScreen.vue'
import DevicesScreen from './screens/DevicesScreen.vue'
import MembersScreen from './screens/MembersScreen.vue'
import SetupScreen from './screens/SetupScreen.vue'
import SettingsScreen from './screens/SettingsScreen.vue'
import NotificationSettings from './screens/NotificationSettings.vue'
import { createPushController } from './composables/usePush'
import {
  createSimulatedPushBridge,
  createUnavailablePushBridge,
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
const links = computed(() => {
  const common = [{ path: '/deliveries' as const, label: ui.deliveries }]
  return user.value?.role === 'admin'
    ? [
        ...common,
        { path: '/devices' as const, label: ui.devices },
        { path: '/members' as const, label: ui.members },
        { path: '/setup' as const, label: ui.setup },
        { path: '/settings' as const, label: ui.settings },
      ]
    : [...common, { path: '/settings' as const, label: ui.settings }]
})
const bridge =
  services.mode === 'mock' && import.meta.env.DEV
    ? createSimulatedPushBridge()
    : createUnavailablePushBridge()
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
  queueMicrotask(focusMain)
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
  <div class="app-shell">
    <a href="#main-content" class="skip-link" @click.prevent="focusMain">{{
      copy.skip
    }}</a>
    <header class="topbar">
      <a
        class="brand"
        href="#/deliveries"
        aria-label="Cekrir"
        @click.prevent="navigate(user ? '/deliveries' : '/login')"
        ><svg viewBox="0 0 28 28" fill="none" aria-hidden="true">
          <path
            d="m3 9 11-6 11 6v12l-11 5-11-5V9Z"
            stroke="currentColor"
            stroke-width="1.6"
            stroke-linejoin="round"
          />
          <path
            d="m3 9 11 6 11-6M14 15v11M8 6l11 6"
            stroke="currentColor"
            stroke-width="1.6"
          /></svg
        >cekrir<span class="brand__dot">.</span></a
      >
      <span class="mode-label">{{
        services.mode === 'mock' ? ui.mock : ui.live
      }}</span>
    </header>
    <nav v-if="user" class="app-nav" :aria-label="copy.navigation">
      <a
        v-for="link in links"
        :key="link.path"
        :href="`#${link.path}`"
        :aria-current="
          route === link.path || (link.path === '/deliveries' && deliveryId)
            ? 'page'
            : undefined
        "
        @click.prevent="navigate(link.path)"
        >{{ link.label }}</a
      >
    </nav>
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
            {{ copy.navigateDelivery }}</button
          ><button class="text-button" @click="push.dismissBanner()">
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
          <SetupScreen
            v-else-if="route === '/setup' && user.role === 'admin'"
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
  </div>
</template>
