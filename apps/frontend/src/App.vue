<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, shallowRef, watch } from 'vue'
import type {
  ApiServices,
  PackageNotification,
  User,
} from './features/api/contracts'
import { parseApiRoute, shipmentRoute, type Route } from './features/api/routes'
import ApiAuth from './features/ApiAuth.vue'
import ShipmentView from './features/ShipmentView.vue'
import NotificationFeed from './features/NotificationFeed.vue'
import UserRoles from './features/UserRoles.vue'
import AppIcon from './components/AppIcon.vue'
const { services } = defineProps<{ services: ApiServices }>()
const user = shallowRef<User | null>(services.user())
const route = ref<Route>(parseApiRoute(location.hash))
const revision = ref(0)
const liveStatus = ref('unavailable')
const alert = shallowRef<PackageNotification | null>(null)
const notice = ref('')
let pendingLink: Route | null = route.value.startsWith('/shipments/')
  ? route.value
  : null
let disconnect: (() => void) | null = null
const id = computed(() =>
  route.value.startsWith('/shipments/')
    ? decodeURIComponent(route.value.slice(11))
    : null,
)
const nav = computed(() => [
  { path: '/shipments' as Route, label: 'Paket', icon: 'package' as const },
  {
    path: '/notifications' as Route,
    label: 'Notifikasi',
    icon: 'bell' as const,
  },
  ...(user.value?.role === 'admin'
    ? [{ path: '/members' as Route, label: 'Pengguna', icon: 'users' as const }]
    : []),
  { path: '/settings' as Route, label: 'Akun', icon: 'user' as const },
])
function navigate(value: Route, replace = false) {
  route.value = value
  if (replace) history.replaceState(null, '', `#${value}`)
  else location.hash = value
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
    pendingLink = id.value ? shipmentRoute(id.value) : null
    alert.value = null
    navigate('/login', true)
  }
  if (next && !previous) {
    notice.value = ''
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
    if (value)
      disconnect = services.notifications.connect({
        event(notification) {
          alert.value = notification
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
      if (id.value) pendingLink = route.value
      navigate('/login', true)
    } else if (
      user.value &&
      (route.value === '/login' ||
        (route.value === '/members' && user.value.role !== 'admin'))
    )
      navigate('/shipments', true)
  },
  { immediate: true },
)
watch(route, () =>
  queueMicrotask(() => {
    window.scrollTo(0, 0)
    document.getElementById('main-content')?.focus({ preventScroll: true })
  }),
)
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
  <div class="app-shell api-shell">
    <a class="skip-link" href="#main-content" @click.prevent="focusMain"
      >Lewati ke konten</a
    >
    <header class="api-topbar">
      <a
        class="brand"
        href="#/shipments"
        @click.prevent="navigate(user ? '/shipments' : '/login')"
        >cekrir<span class="brand__dot">.</span></a
      ><a
        v-if="user"
        href="#/settings"
        @click.prevent="navigate('/settings')"
        >{{ user.full_name }}</a
      >
    </header>
    <p class="mode-label">
      {{ services.mode === 'mock' ? 'Demo · data simulasi' : 'Mode live' }}
    </p>
    <p v-if="services.mode === 'mock'" class="banner">
      Data simulasi, tanpa email, perangkat, atau notifikasi nyata.
    </p>
    <p v-if="notice" class="banner" role="status">{{ notice }}</p>
    <aside v-if="alert && user" class="banner api-actions" role="status">
      <span>{{ alert.title }} · {{ alert.message }}</span
      ><button
        class="text-button"
        @click="
          openShipment(alert.shipment_id);
          alert = null
        "
      >
        Lihat paket</button
      ><button class="text-button" @click="alert = null">Tutup</button>
    </aside>
    <main id="main-content" tabindex="-1">
      <ApiAuth v-if="!user" :services="services" />
      <template v-else>
        <ShipmentView
          v-if="route.startsWith('/shipments')"
          :key="`${user.id}:${user.role}`"
          :services="services"
          :user="user"
          :id="id"
          :revision="revision"
          @open="openShipment"
          @back="navigate('/shipments')"
        />
        <NotificationFeed
          v-else-if="route === '/notifications'"
          :key="user.id"
          :services="services"
          :revision="revision"
          :live-status="liveStatus"
          @open="openShipment"
        />
        <UserRoles
          v-else-if="route === '/members' && user.role === 'admin'"
          :key="user.id"
          :services="services"
        />
        <section v-else>
          <h1>Akun</h1>
          <article class="panel">
            <h2>{{ user.full_name }}</h2>
            <p>{{ user.email }}</p>
            <p>{{ user.role === 'admin' ? 'Admin' : 'Anggota' }}</p>
            <p class="supporting">
              Sesi disimpan sementara. Muat ulang halaman atau tutup aplikasi
              untuk mengakhiri sesi lokal. Keluar tidak mencabut token di
              server.
            </p>
            <button class="button button--quiet" @click="logout">Keluar</button>
          </article>
          <article class="panel">
            <h2>Ketersediaan layanan</h2>
            <p>
              Catatan paket digunakan bersama; pemisahan lokasi penerimaan belum
              tersedia.
            </p>
            <p>
              Pengelolaan perangkat, foto pengiriman, pembayaran, dan notifikasi
              latar belakang belum tersedia di aplikasi ini.
            </p>
            <p>
              Pembaruan langsung:
              {{
                liveStatus === 'connected'
                  ? 'terhubung'
                  : services.mode === 'mock'
                    ? 'simulasi'
                    : 'sementara tidak tersedia'
              }}. Daftar notifikasi dapat dimuat ulang.
            </p>
          </article>
        </section>
      </template>
    </main>
    <nav v-if="user" class="api-nav" aria-label="Navigasi utama">
      <a
        v-for="link in nav"
        :key="link.path"
        :href="`#${link.path}`"
        :aria-current="
          route === link.path || (link.path === '/shipments' && id)
            ? 'page'
            : undefined
        "
        @click.prevent="navigate(link.path)"
        ><AppIcon :name="link.icon" /><span>{{ link.label }}</span></a
      >
    </nav>
    <footer>cekrir · Catatan paket dan pelacakan</footer>
  </div>
</template>
