<script setup lang="ts">
import { computed } from 'vue'
import type { Route } from '../features/api/routes'
import { shellCopy as copy } from '../lib/shell-copy'
import { ui } from '../lib/strings'
import AppIcon, { type IconName } from './AppIcon.vue'

const props = defineProps<{ isAdmin: boolean; route: Route }>()
const emit = defineEmits<{ navigate: [path: Route] }>()
interface NavigationLink {
  path: Route
  label: string
  icon: IconName
}
const links = computed<NavigationLink[]>(() => {
  const shipments: NavigationLink = {
    path: '/shipments',
    label: ui.packages,
    icon: 'package',
  }
  return props.isAdmin
    ? [
        shipments,
        { path: '/devices', label: ui.devices, icon: 'device' },
        { path: '/members', label: 'Pengguna', icon: 'users' },
      ]
    : [shipments]
})
const activeIndex = computed(() =>
  links.value.findIndex((link) => link.path === props.route),
)
</script>

<template>
  <nav
    id="main-navigation"
    class="api-nav"
    :class="{ 'api-nav--member': !isAdmin }"
    :aria-label="copy.navigation"
  >
    <span
      v-if="activeIndex >= 0"
      class="api-nav__indicator"
      :style="{ '--active-index': activeIndex, '--tab-count': links.length }"
      aria-hidden="true"
    />
    <a
      v-for="link in links"
      :key="link.path"
      :href="`#${link.path}`"
      :aria-current="route === link.path ? 'page' : undefined"
      @click.prevent="emit('navigate', link.path)"
    >
      <AppIcon :name="link.icon" /><span>{{ link.label }}</span>
    </a>
  </nav>
</template>

<style scoped>
.api-nav {
  --nav-padding: 8px;
  --nav-gap: 4px;
  --tab-radius: 24px;
  position: fixed;
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

.api-nav--member {
  max-width: 220px;
}

.api-nav__indicator {
  position: absolute;
  inset-block: var(--nav-padding);
  left: var(--nav-padding);
  width: calc(
    (100% - 2 * var(--nav-padding) - (var(--tab-count) - 1) * var(--nav-gap)) /
      var(--tab-count)
  );
  transform: translateX(calc(var(--active-index) * (100% + var(--nav-gap))));
  border-radius: var(--tab-radius);
  background: #234e41;
  pointer-events: none;
}

.api-nav a {
  position: relative;
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
  color: #fffefa;
}

.api-nav a:hover {
  outline: 1px solid #71866c;
}

.api-nav svg {
  width: 22px;
  height: 22px;
}

@media (prefers-reduced-motion: no-preference) {
  .api-nav__indicator {
    transition: transform 240ms cubic-bezier(0.2, 0.8, 0.2, 1);
  }

  .api-nav a {
    transition: color 160ms ease-out;
  }
}
</style>
