<script setup lang="ts">
import { computed } from 'vue'
import type { AppRoute, Role } from '../types/app'
import { shellCopy as copy } from '../lib/shell-copy'
import { ui } from '../lib/strings'
import AppIcon, { type IconName } from './AppIcon.vue'

const props = defineProps<{ role: Role; route: AppRoute }>()
const emit = defineEmits<{ navigate: [path: AppRoute] }>()
interface NavigationLink {
  path: AppRoute
  label: string
  icon: IconName
}
const links = computed<NavigationLink[]>(() => {
  const deliveries: NavigationLink = {
    path: '/deliveries',
    label: ui.packages,
    icon: 'package',
  }
  return props.role === 'admin'
    ? [
        deliveries,
        { path: '/devices', label: ui.devices, icon: 'device' },
        { path: '/members', label: ui.members, icon: 'users' },
      ]
    : [deliveries]
})
function isCurrent(path: AppRoute) {
  return (
    props.route === path ||
    (path === '/devices' && props.route.startsWith('/devices/')) ||
    (path === '/deliveries' && props.route.startsWith('/deliveries/'))
  )
}
</script>

<template>
  <nav
    id="main-navigation"
    class="app-nav"
    :class="{ 'app-nav--member': role === 'member' }"
    :aria-label="copy.navigation"
  >
    <a
      v-for="link in links"
      :key="link.path"
      class="app-nav__link"
      :href="`#${link.path}`"
      :aria-current="isCurrent(link.path) ? 'page' : undefined"
      @click.prevent="emit('navigate', link.path)"
    >
      <AppIcon :name="link.icon" /><span>{{ link.label }}</span>
    </a>
  </nav>
</template>

<style scoped>
.app-nav {
  container: bottom-navigation / inline-size;
  font-size: 1rem;
  position: fixed;
  z-index: 30;
  bottom: calc(16px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  display: flex;
  align-items: stretch;
  gap: 4px;
  width: min(calc(100% - 32px), 480px);
  padding: 8px;
  border: 1px solid #dce2d8;
  border-radius: 48px;
  background: #fffefa;
  box-shadow: 0 8px 28px #233d3726;
  transform: translateX(-50%);
}
.app-nav--member {
  container-name: member-navigation;
  max-width: 220px;
}
.app-nav__link {
  display: flex;
  min-width: 0;
  min-height: 64px;
  flex: 1;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 10px 8px;
  border-radius: 36px;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.25;
  text-align: center;
  text-decoration: none;
}
.app-nav__link .app-icon {
  width: 22px;
  height: 22px;
}
.app-nav__link span {
  max-width: 100%;
  overflow-wrap: anywhere;
}
.app-nav__link:hover {
  background: #e9eedf;
  color: #233d37;
}
.app-nav__link[aria-current='page'] {
  background: #234e41;
  color: #fffefa;
}
.app-nav__link[aria-current='page']:hover {
  background: #173e32;
}
.app-nav__link:focus-visible {
  outline-offset: -3px;
}
@container bottom-navigation (max-width: 19em) {
  .app-nav__link {
    min-height: 56px;
    gap: 0;
  }
  .app-nav__link span {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    white-space: nowrap;
    clip-path: inset(50%);
  }
}
@media (prefers-reduced-motion: no-preference) {
  .app-nav__link {
    transition: background-color 160ms ease-out;
  }
}
</style>
