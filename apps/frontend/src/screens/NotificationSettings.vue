<script setup lang="ts">
import { computed } from 'vue'
import type { PushState } from '../composables/usePush'
import { pushCopy } from '../lib/push-copy'

const props = defineProps<{ state: PushState }>()
const isDevBuild = import.meta.env.DEV

const emit = defineEmits<{
  enable: []
  retry: []
  simulateReceived: []
  simulateTap: []
  tapBanner: []
  dismissBanner: []
}>()

const statusCopy = computed(() => {
  if (props.state.mode === 'unavailable') return pushCopy.unavailable
  if (props.state.association === 'blocked') return pushCopy.associationBlocked

  switch (props.state.permission) {
    case 'unsupported':
      return pushCopy.unavailable
    case 'denied':
      return pushCopy.permissionDenied
    case 'granted':
      switch (props.state.association) {
        case 'pending':
          return pushCopy.associationPending
        case 'registered':
          return props.state.mode === 'simulated'
            ? pushCopy.simulatedRegistered
            : pushCopy.associationRegistered
        case 'failed':
          return pushCopy.associationFailed
        default:
          return pushCopy.permissionGranted
      }
    default:
      return pushCopy.permissionNotRequested
  }
})

const showError = computed(() =>
  Boolean(
    props.state.error &&
    props.state.error !== statusCopy.value &&
    !props.state.pendingNavigation,
  ),
)

const showEnable = computed(
  () =>
    props.state.mode !== 'unavailable' &&
    props.state.association !== 'blocked' &&
    props.state.permission === 'not-requested',
)
const showRetry = computed(
  () =>
    props.state.mode !== 'unavailable' &&
    (props.state.association === 'blocked' ||
      (props.state.permission === 'granted' &&
        props.state.association !== 'registered')),
)
</script>

<template>
  <section class="notification-settings" aria-labelledby="notification-heading">
    <header class="notification-settings__header">
      <span class="notification-settings__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none">
          <path
            d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4"
            stroke="currentColor"
            stroke-width="1.7"
            stroke-linecap="round"
            stroke-linejoin="round"
          />
        </svg>
      </span>
      <div>
        <h2 id="notification-heading">{{ pushCopy.heading }}</h2>
        <p>{{ pushCopy.description }}</p>
      </div>
    </header>

    <div class="notification-settings__status" aria-live="polite">
      <span
        class="notification-settings__dot"
        :class="{
          'notification-settings__dot--ready':
            state.association === 'registered',
          'notification-settings__dot--warning':
            state.association === 'failed' || state.association === 'blocked',
        }"
        aria-hidden="true"
      />
      <p>{{ statusCopy }}</p>
    </div>

    <p v-if="showError" class="notification-settings__error" role="alert">
      {{ state.error }}
    </p>

    <div class="notification-settings__actions">
      <button
        v-if="showEnable"
        class="notification-settings__button notification-settings__button--primary"
        type="button"
        :disabled="state.busy"
        @click="emit('enable')"
      >
        {{ state.busy ? pushCopy.processing : pushCopy.enable }}
      </button>
      <button
        v-else-if="showRetry"
        class="notification-settings__button"
        type="button"
        :disabled="state.busy"
        @click="emit('retry')"
      >
        {{ state.busy ? pushCopy.processing : pushCopy.retry }}
      </button>
    </div>

    <aside
      v-if="state.banner"
      class="notification-settings__banner"
      role="status"
      aria-live="polite"
    >
      <div>
        <strong>{{ pushCopy.bannerTitle }}</strong>
        <p>{{ pushCopy.description }}</p>
      </div>
      <div class="notification-settings__banner-actions">
        <button
          class="notification-settings__text-button"
          type="button"
          :disabled="state.pendingNavigation && !state.error"
          @click="emit('tapBanner')"
        >
          {{
            state.error
              ? pushCopy.retry
              : state.pendingNavigation
                ? pushCopy.opening
                : pushCopy.bannerAction
          }}
        </button>
        <button
          class="notification-settings__dismiss"
          type="button"
          :aria-label="pushCopy.dismissBanner"
          @click="emit('dismissBanner')"
        >
          {{ pushCopy.close }}
        </button>
      </div>
    </aside>

    <aside
      v-if="state.pendingNavigation && !state.banner"
      class="notification-settings__banner"
      role="status"
      aria-live="polite"
    >
      <p>{{ state.error ?? pushCopy.pendingNavigation }}</p>
      <button
        v-if="state.error"
        class="notification-settings__text-button"
        type="button"
        @click="emit('tapBanner')"
      >
        {{ pushCopy.retry }}
      </button>
    </aside>

    <div
      v-if="state.mode === 'simulated' && isDevBuild"
      class="notification-settings__demo"
    >
      <p>{{ pushCopy.simulated }}</p>
      <p>{{ pushCopy.demoDescription }}</p>
      <div class="notification-settings__demo-actions">
        <button
          class="notification-settings__button"
          type="button"
          @click="emit('simulateReceived')"
        >
          {{ pushCopy.simulateReceived }}
        </button>
        <button
          class="notification-settings__text-button"
          type="button"
          @click="emit('simulateTap')"
        >
          {{ pushCopy.simulateTap }}
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.notification-settings {
  display: grid;
  gap: 18px;
  padding: 22px;
  border: 1px solid #e0e4d9;
  border-radius: 10px;
  background: #fffefa;
  color: #233d37;
}

.notification-settings__header {
  display: grid;
  grid-template-columns: 42px minmax(0, 1fr);
  align-items: start;
  gap: 13px;
}

.notification-settings__icon {
  display: grid;
  width: 42px;
  height: 42px;
  place-items: center;
  border-radius: 8px;
  background: #eef2e8;
  color: #234e41;
}

.notification-settings__icon svg {
  width: 22px;
  height: 22px;
}

.notification-settings__header h2 {
  margin: 0 0 5px;
  font-size: 1.0625rem;
  letter-spacing: -0.4px;
}

.notification-settings__header p,
.notification-settings__status p,
.notification-settings__demo p,
.notification-settings__banner p {
  color: #65736a;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.notification-settings__status {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 13px 14px;
  border-radius: 7px;
  background: #f4f5ef;
}

.notification-settings__dot {
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  margin-top: 5px;
  border-radius: 50%;
  background: #788577;
}

.notification-settings__dot--ready {
  background: #477657;
}

.notification-settings__dot--warning {
  background: #a66a37;
}

.notification-settings__error {
  color: #925b3a;
  font-size: 0.8125rem;
  line-height: 1.55;
}

.notification-settings__actions,
.notification-settings__demo-actions,
.notification-settings__banner-actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}

.notification-settings__button,
.notification-settings__text-button,
.notification-settings__dismiss {
  min-height: 44px;
  border: 1px solid #d6ded0;
  border-radius: 6px;
  padding: 9px 13px;
  background: #f1f3ec;
  color: #415b4d;
  font: inherit;
  font-size: 0.8125rem;
  line-height: 1.35;
  text-align: left;
  transition:
    background-color 160ms ease-out,
    border-color 160ms ease-out,
    color 160ms ease-out;
}

.notification-settings__button:hover:not(:disabled),
.notification-settings__text-button:hover:not(:disabled),
.notification-settings__dismiss:hover:not(:disabled) {
  border-color: #9eae9e;
  background: #e8ede3;
}

.notification-settings__button:focus-visible,
.notification-settings__text-button:focus-visible,
.notification-settings__dismiss:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 3px;
}

.notification-settings__button:disabled,
.notification-settings__text-button:disabled,
.notification-settings__dismiss:disabled {
  cursor: wait;
  opacity: 0.65;
}

.notification-settings__button--primary {
  border-color: #234e41;
  background: #234e41;
  color: #fffefa;
}

.notification-settings__button--primary:hover:not(:disabled) {
  border-color: #173e32;
  background: #173e32;
}

.notification-settings__banner {
  display: grid;
  gap: 13px;
  padding: 15px;
  border: 1px solid #d3ddc7;
  border-radius: 7px;
  background: #e9eedf;
}

.notification-settings__banner strong {
  display: block;
  margin-bottom: 4px;
  font-size: 0.875rem;
}

.notification-settings__banner-actions {
  justify-content: space-between;
}

.notification-settings__text-button {
  border-color: transparent;
  background: transparent;
  color: #234e41;
  font-weight: 600;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.notification-settings__dismiss {
  border-color: transparent;
  background: transparent;
  color: #65736a;
}

.notification-settings__demo {
  display: grid;
  gap: 10px;
  padding-top: 15px;
  border-top: 1px solid #e6e9df;
}

@media (max-width: 520px) {
  .notification-settings {
    padding: 17px;
  }

  .notification-settings__actions,
  .notification-settings__demo-actions {
    align-items: stretch;
    flex-direction: column;
  }

  .notification-settings__actions > *,
  .notification-settings__demo-actions > * {
    width: 100%;
    text-align: center;
  }
}
</style>
