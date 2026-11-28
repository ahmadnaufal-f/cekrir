<script setup lang="ts">
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { shellCopy as copy } from '../lib/shell-copy'
import { ui } from '../lib/strings'
import AppIcon, { type IconName } from './AppIcon.vue'

interface NavigationLink {
  name: 'shipments' | 'devices' | 'members'
  label: string
  icon: IconName
}
const links: NavigationLink[] = [
  { name: 'shipments', label: ui.packages, icon: 'package' },
  { name: 'devices', label: ui.devices, icon: 'device' },
  { name: 'members', label: 'Pengguna', icon: 'users' },
]
const route = useRoute()
const activeIndex = computed(() =>
  links.findIndex((link) => link.name === route.name),
)
</script>

<template>
  <nav
    id="main-navigation"
    class="api-nav"
    :aria-label="copy.navigation"
    :style="{ '--link-count': links.length, '--active-index': activeIndex }"
  >
    <span
      v-if="activeIndex >= 0"
      class="api-nav__indicator"
      aria-hidden="true"
    />
    <RouterLink
      v-for="link in links"
      :key="link.name"
      :to="{ name: link.name }"
    >
      <AppIcon :name="link.icon" /><span>{{ link.label }}</span>
    </RouterLink>
  </nav>
</template>

<style scoped>
.api-nav {
  --nav-padding: 8px;
  --nav-gap: 4px;
  --tab-radius: 24px;
  position: fixed;
  isolation: isolate;
  bottom: calc(12px + env(safe-area-inset-bottom, 0px));
  left: 50%;
  transform: translateX(-50%);
  z-index: 30;
  display: flex;
  width: min(480px, calc(100% - 24px));
  padding: var(--nav-padding);
  border: 1px solid #dce2d8;
  border-radius: 32px;
  background: #fffefa;
  box-shadow: 0 8px 28px #233d3726;
  gap: var(--nav-gap);
}

.api-nav__indicator {
  position: absolute;
  z-index: -1;
  inset: var(--nav-padding) auto var(--nav-padding) var(--nav-padding);
  width: calc(
    (100% - 2 * var(--nav-padding) - (var(--link-count) - 1) * var(--nav-gap)) /
      var(--link-count)
  );
  border: 1px solid #a9c5b0;
  border-radius: var(--tab-radius);
  background: #cfe3d6;
  transform: translateX(calc(var(--active-index) * (100% + var(--nav-gap))));
  pointer-events: none;
}

.api-nav a {
  flex: 1;
  min-width: 0;
  min-height: 60px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 5px;
  padding-inline: 0;
  border-radius: var(--tab-radius);
  text-align: center;
  text-decoration: none;
  font-size: 0.8125rem;
}

.api-nav a span {
  max-width: 100%;
  overflow-wrap: anywhere;
}

.api-nav a[aria-current='page'] {
  color: #173e32;
}

.api-nav a:active:not([aria-current='page']) {
  background: #eef2e8;
}

@media (hover: hover) and (pointer: fine) {
  .api-nav a:hover:not(:active, [aria-current='page']) {
    background: #eef2e8;
  }
}

.api-nav svg {
  width: 22px;
  height: 22px;
}

@media (prefers-reduced-motion: no-preference) {
  .api-nav__indicator {
    transition: transform var(--motion-selection) var(--ease-move);
  }

  .api-nav svg {
    transition: transform var(--motion-feedback) var(--ease-enter);
  }

  .api-nav a:active svg {
    transform: scale(0.9);
  }
}
</style>
