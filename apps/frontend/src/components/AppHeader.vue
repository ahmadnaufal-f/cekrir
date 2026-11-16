<script setup lang="ts">
import { computed, onMounted, onUnmounted, shallowRef } from 'vue'
import type { AppRoute, AppUser } from '../types/app'
import { shellCopy as copy } from '../lib/shell-copy'
import AppIcon from './AppIcon.vue'

const props = defineProps<{
  user: Pick<AppUser, 'role' | 'displayName'> | null
  route: AppRoute
}>()
const emit = defineEmits<{ navigate: [path: AppRoute] }>()
const scrolled = shallowRef(false)
const initials = computed(() =>
  props.user?.displayName
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part.charAt(0))
    .join('')
    .toUpperCase(),
)
function updateScroll() {
  scrolled.value = window.scrollY > 0
}
onMounted(() => {
  updateScroll()
  window.addEventListener('scroll', updateScroll, { passive: true })
})
onUnmounted(() => window.removeEventListener('scroll', updateScroll))
</script>

<template>
  <header class="site-header" :class="{ 'site-header--floating': scrolled }">
    <a
      class="brand"
      href="#/deliveries"
      aria-label="Cekrir"
      @click.prevent="emit('navigate', user ? '/deliveries' : '/login')"
    >
      <svg viewBox="0 0 28 28" fill="none" aria-hidden="true">
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
      >cekrir<span class="brand__dot">.</span>
    </a>
    <a
      v-if="user"
      class="account-avatar"
      href="#/settings"
      :aria-label="`${copy.openAccount}: ${user.displayName}`"
      :aria-current="route === '/settings' ? 'page' : undefined"
      @click.prevent="emit('navigate', '/settings')"
    >
      <span v-if="initials" aria-hidden="true">{{ initials }}</span>
      <AppIcon v-else name="user" />
    </a>
  </header>
</template>

<style scoped>
.site-header {
  position: sticky;
  top: env(safe-area-inset-top, 0px);
  z-index: 20;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  padding: 14px 0;
  pointer-events: none;
}
.brand,
.account-avatar {
  border: 1px solid transparent;
  pointer-events: auto;
}
.brand {
  padding: 10px 12px;
  margin-left: -12px;
  border-radius: 999px;
}
.account-avatar {
  display: grid;
  width: 48px;
  height: 48px;
  flex: none;
  place-items: center;
  border-color: #d5decf;
  border-radius: 50%;
  background: #e9eedf;
  color: #234e41;
  font-size: 0.875rem;
  font-weight: 650;
  text-decoration: none;
}
.site-header--floating .brand,
.site-header--floating .account-avatar {
  border-color: #dce2d8;
  background: #fffefa;
  box-shadow: 0 6px 20px #233d371f;
}
.brand:hover,
.account-avatar:hover {
  background: #e9eedf;
}
.account-avatar[aria-current='page'] {
  border-color: #234e41;
  background: #234e41;
  color: #fffefa;
}
@media (prefers-reduced-motion: no-preference) {
  .brand,
  .account-avatar {
    transition:
      background-color 160ms ease-out,
      border-color 160ms ease-out,
      box-shadow 160ms ease-out;
  }
}
</style>
