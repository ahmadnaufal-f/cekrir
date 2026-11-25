<script setup lang="ts">
import {
  computed,
  onMounted,
  onUnmounted,
  shallowRef,
  useTemplateRef,
} from 'vue'
import { RouterLink } from 'vue-router'
import { accountInitials } from '../lib/account-initials'
import { ui } from '../lib/strings'
import AppIcon from './AppIcon.vue'
import BackButton from './BackButton.vue'

const props = defineProps<{
  signedIn: boolean
  displayName?: string | null
  accountCurrent: boolean
  modeLabel: string
}>()
const emit = defineEmits<{
  back: []
  logout: []
}>()
const scrolled = shallowRef(false)
const menuOpen = shallowRef(false)
const account = useTemplateRef('account')
const avatar = useTemplateRef('avatar')
const name = computed(() => props.displayName?.trim())
const initials = computed(() => accountInitials(name.value))
function updateScroll() {
  scrolled.value = window.scrollY > 0
}
function closeOutside(event: PointerEvent | FocusEvent) {
  const target =
    event instanceof FocusEvent ? event.relatedTarget : event.target
  if (
    menuOpen.value &&
    !(target instanceof Node && account.value?.contains(target))
  )
    menuOpen.value = false
}
function closeOnEscape(event: KeyboardEvent) {
  if (!menuOpen.value) return
  event.preventDefault()
  event.stopPropagation()
  menuOpen.value = false
  avatar.value?.focus()
}
function openSettings() {
  menuOpen.value = false
  if (props.accountCurrent) avatar.value?.focus()
}
onMounted(() => {
  updateScroll()
  window.addEventListener('scroll', updateScroll, { passive: true })
  document.addEventListener('pointerdown', closeOutside, true)
})
onUnmounted(() => {
  window.removeEventListener('scroll', updateScroll)
  document.removeEventListener('pointerdown', closeOutside, true)
})
</script>

<template>
  <header
    class="site-header"
    :class="{
      'sticky-header': signedIn,
      'site-header--floating': signedIn && scrolled,
      'site-header--settings': accountCurrent,
    }"
  >
    <BackButton
      v-if="accountCurrent"
      class="site-header__back"
      @click="emit('back')"
    />
    <RouterLink
      v-else
      class="brand"
      :to="{ name: signedIn ? 'shipments' : 'login' }"
      aria-label="Cekrir"
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
        />
      </svg>
      <span>cekrir<span class="brand__dot">.</span></span>
    </RouterLink>
    <div
      v-if="signedIn"
      ref="account"
      class="account-dropdown"
      @focusout="closeOutside"
      @keydown.esc="closeOnEscape"
    >
      <button
        ref="avatar"
        type="button"
        class="account-avatar"
        :class="{ 'account-avatar--current': accountCurrent }"
        :aria-label="name ? `Menu akun: ${name}` : 'Menu akun'"
        :aria-expanded="menuOpen"
        aria-controls="account-dropdown-actions"
        @click="menuOpen = !menuOpen"
      >
        <span v-if="initials" aria-hidden="true">{{ initials }}</span>
        <AppIcon v-else name="user" />
      </button>
      <div
        id="account-dropdown-actions"
        class="account-dropdown__actions"
        :data-open="menuOpen"
        :inert="!menuOpen"
      >
        <RouterLink
          :to="{ name: 'settings', state: { settingsOpenedInApp: true } }"
          class="account-dropdown__action"
          @click="openSettings"
        >
          <AppIcon name="user" /> Pengaturan
        </RouterLink>
        <button
          type="button"
          class="account-dropdown__action"
          @click="emit('logout')"
        >
          <AppIcon name="logout" /> {{ ui.logout }}
        </button>
      </div>
    </div>
    <p v-else class="mode-label site-header__mode">{{ modeLabel }}</p>
  </header>
</template>

<style scoped>
.site-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: calc(48px + 2 * var(--app-header-padding));
  gap: 12px;
  padding-block: var(--app-header-padding);
  pointer-events: none;
}
.site-header--settings.site-header--floating {
  background: #f6f7f2;
}
.brand,
.account-avatar {
  border: 1px solid transparent;
  pointer-events: auto;
}
.brand {
  min-height: 48px;
  padding-inline: 12px;
  margin-inline-start: -12px;
  border-radius: 999px;
  line-height: 1.15;
}
.site-header__mode {
  max-width: 50%;
  text-align: end;
}
.account-dropdown {
  position: relative;
  pointer-events: auto;
}
.account-avatar {
  display: grid;
  width: 48px;
  height: 48px;
  flex: none;
  place-items: center;
  padding: 0;
  border-color: #d5decf;
  border-radius: 50%;
  background: #e9eedf;
  color: #234e41;
  font-size: 0.875rem;
  font-weight: 650;
  text-decoration: none;
}
.site-header__back {
  align-self: start;
  pointer-events: auto;
}
.site-header--floating .brand,
.site-header--floating .account-avatar {
  border-color: #dce2d8;
  background: #fffefa;
  box-shadow: 0 6px 20px #233d371f;
}
.site-header--floating .site-header__back {
  border-color: #dce2d8;
  box-shadow: 0 6px 20px #233d371f;
}
@media (hover: hover) and (pointer: fine) {
  .brand:hover,
  .account-avatar:hover {
    background: #e9eedf;
  }
}
.account-avatar--current,
.account-avatar[aria-expanded='true'] {
  border-color: #234e41;
  background: #234e41;
  color: #fffefa;
}
.account-dropdown__actions {
  position: absolute;
  inset-block-start: calc(100% + 8px);
  inset-inline-end: 0;
  display: grid;
  gap: 2px;
  inline-size: min(12rem, calc(100vw - 40px));
  padding: 6px;
  border: 1px solid #dce2d8;
  border-radius: 14px;
  background: #fffefa;
  box-shadow: 0 10px 28px #233d3726;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform-origin: calc(100% - 24px) top;
}
.account-dropdown__actions[data-open='true'] {
  opacity: 1;
  visibility: visible;
  pointer-events: auto;
}
.account-dropdown__action {
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ink);
  font-size: 0.9375rem;
  font-weight: 600;
  text-align: start;
  text-decoration: none;
  overflow-wrap: anywhere;
}
.account-dropdown__action[aria-current='page'] {
  background: #eef2e8;
}
@media (hover: hover) and (pointer: fine) {
  .account-dropdown__action:hover {
    background: #eef2e8;
  }
}
.account-dropdown__action:focus-visible {
  outline-offset: -2px;
}
@media (prefers-reduced-motion: no-preference) {
  .account-dropdown__actions {
    transform: translateY(-4px) scale(0.97);
    transition:
      opacity var(--motion-menu-exit) var(--ease-exit),
      transform var(--motion-menu-exit) var(--ease-exit),
      visibility 0s linear var(--motion-menu-exit);
  }

  .account-dropdown__actions[data-open='true'] {
    transform: none;
    transition:
      opacity var(--motion-menu-enter) var(--ease-enter),
      transform var(--motion-menu-enter) var(--ease-enter);
  }

  .brand {
    transition:
      background-color var(--motion-feedback) ease,
      border-color var(--motion-feedback) ease,
      box-shadow var(--motion-feedback) ease;
  }

  .account-avatar {
    transition: transform var(--motion-feedback) var(--ease-enter);
  }

  .account-avatar:active {
    transform: scale(0.96);
  }
}
</style>
