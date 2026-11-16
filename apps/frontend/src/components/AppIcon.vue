<script setup lang="ts">
// Authored outline icons share one viewbox, stroke weight, and decorative role.
const paths = {
  package: 'm3 7 9-4 9 4v10l-9 4-9-4V7Zm0 0 9 4 9-4M12 11v10M7.5 5l9 4',
  camera: 'M8 5 6.5 8H3v12h18V8h-3.5L16 5H8Zm8 9a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  refresh: 'M20 8a8 8 0 0 0-14-2L3 9m0-6v6h6M4 16a8 8 0 0 0 14 2l3-3m0 6v-6h-6',
  device: 'M7 7h10v10H7V7ZM9 3v4m6-4v4M9 17v4m6-4v4M3 9h4m-4 6h4m10-6h4m-4 6h4',
  users:
    'M16 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2m16 0v-2a4 4 0 0 0-3-3.87M14 3.13a4 4 0 0 1 0 7.75M14 7a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  book: 'M12 5c-3-2-6-2-10-1v15c4-1 7-1 10 1 3-2 6-2 10-1V4c-4-1-7-1-10 1Zm0 0v15',
  user: 'M20 21v-2a5 5 0 0 0-5-5H9a5 5 0 0 0-5 5v2M16 6a4 4 0 1 1-8 0 4 4 0 0 1 8 0Z',
  menu: 'M3 6h18M3 12h18M3 18h18',
  close: 'm6 6 12 12M6 18 18 6',
  back: 'm12 5-7 7 7 7M5 12h15',
  tracking:
    'M3 4h11v13H3V4Zm11 5h4l3 4v4h-7M7 17a2 2 0 1 1-4 0 2 2 0 0 1 4 0Zm13 0a2 2 0 1 1-4 0 2 2 0 0 1 4 0Z',
  plus: 'M12 5v14M5 12h14',
  copy: 'M9 9h12v12H9V9Zm-4 6H3V3h12v2',
  check: 'm5 12 4 4L19 6',
  external: 'M14 3h7v7m0-7L10 14M10 3H3v18h18v-7',
  logout: 'M9 3H3v18h6m6-16 7 7-7 7M8 12h14',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4',
  eye: 'M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7Zm13 0a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  eyeOff:
    'm3 3 18 18M10.6 5.1 12 5c6 0 10 7 10 7a18 18 0 0 1-3 3.7M6.2 6.2A22 22 0 0 0 2 12s4 7 10 7c1.8 0 3.4-.6 4.8-1.5M9.9 9.9a3 3 0 0 0 4.2 4.2',
} as const

export type IconName = keyof typeof paths
defineProps<{ name: IconName }>()
</script>

<template>
  <svg
    class="app-icon"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    stroke-width="1.7"
    stroke-linecap="round"
    stroke-linejoin="round"
    aria-hidden="true"
    focusable="false"
  >
    <path :d="paths[name]" />
  </svg>
</template>

<style scoped>
.app-icon {
  display: inline-block;
  width: 1.125rem;
  height: 1.125rem;
  flex: none;
  vertical-align: -0.2em;
}
</style>
