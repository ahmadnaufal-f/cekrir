<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import { configuredReference } from '../lib/setup-reference'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, SetupContent } from '../types/app'
import type { DeviceCategory } from '../types/device-ui'

const props = defineProps<{
  services: AppServices
  user: AppUser
  kind: DeviceCategory
}>()
const emit = defineEmits<{ sessionExpired: [] }>()

type LoadState = 'idle' | 'loading' | 'ready' | 'error'

const isAdmin = computed(() => props.user.role === 'admin')
const copy = computed(() => deviceGuideCopy[props.kind])
const resource = shallowRef<SetupContent | null>(null)
const loadState = shallowRef<LoadState>('idle')
const sourceHref = computed(() => configuredReference(resource.value, 'source'))
const guideHref = computed(() => configuredReference(resource.value, 'guide'))
const hasReference = computed(() => !!sourceHref.value || !!guideHref.value)

let requestGeneration = 0
let disposed = false

function isCurrent(generation: number): boolean {
  return !disposed && generation === requestGeneration && isAdmin.value
}

function isUnauthorized(cause: unknown): boolean {
  return cause instanceof ServiceError
    ? cause.status === 401 || cause.code === 'UNAUTHENTICATED'
    : typeof cause === 'object' &&
        cause !== null &&
        'status' in cause &&
        cause.status === 401
}

function reportUnauthorized(cause: unknown, generation: number): boolean {
  if (!isCurrent(generation) || !isUnauthorized(cause)) return false
  resource.value = null
  loadState.value = 'idle'
  emit('sessionExpired')
  return true
}

function clearResource(): void {
  resource.value = null
  loadState.value = 'idle'
}

async function loadResource(generation: number): Promise<void> {
  loadState.value = 'loading'
  try {
    const result = await props.services.setup.content(props.kind)
    if (!isCurrent(generation)) return
    resource.value = result.kind === props.kind ? result : null
    loadState.value = 'ready'
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (!reportUnauthorized(cause, generation)) loadState.value = 'error'
  }
}

function retry(): void {
  if (!isAdmin.value) return
  requestGeneration += 1
  resource.value = null
  void loadResource(requestGeneration)
}

watch(
  [
    () => props.user.id,
    () => props.user.householdId,
    () => props.user.role,
    () => props.kind,
  ],
  () => {
    requestGeneration += 1
    clearResource()
    if (isAdmin.value) void loadResource(requestGeneration)
  },
  { immediate: true, flush: 'sync' },
)

onUnmounted(() => {
  disposed = true
  requestGeneration += 1
  clearResource()
})
</script>

<template>
  <section
    class="device-guide"
    :class="`device-guide--${kind}`"
    :aria-labelledby="`${kind}-guide-title`"
  >
    <header class="device-guide__header">
      <h2 :id="`${kind}-guide-title`">{{ deviceGuideCopy.common.title }}</h2>
      <AppIcon :name="kind === 'esp32' ? 'device' : 'camera'" />
    </header>

    <p v-if="!isAdmin" class="device-guide__notice" role="alert">
      {{ deviceGuideCopy.common.adminOnly }}
    </p>

    <template v-else>
      <p class="device-guide__notice" role="note">{{ copy.statusNote }}</p>

      <p
        v-if="loadState === 'loading'"
        class="device-guide__state"
        role="status"
      >
        {{ deviceGuideCopy.common.loading }}
      </p>
      <div
        v-else-if="loadState === 'error'"
        class="device-guide__error"
        role="alert"
      >
        <p>{{ deviceGuideCopy.common.loadingFailed }}</p>
        <button class="device-guide__retry" type="button" @click="retry">
          <AppIcon name="refresh" />
          {{ deviceGuideCopy.common.retry }}
        </button>
      </div>
      <div v-else-if="loadState === 'ready'" class="device-guide__references">
        <a
          v-if="sourceHref"
          :href="sourceHref"
          target="_blank"
          rel="noopener noreferrer"
        >
          <AppIcon name="external" />
          {{ deviceGuideCopy.esp32.sourceLink }}
        </a>
        <a
          v-if="guideHref"
          :href="guideHref"
          target="_blank"
          rel="noopener noreferrer"
        >
          <AppIcon name="external" />
          {{ copy.guideLink }}
        </a>
        <p v-if="!hasReference" class="device-guide__state">
          {{ deviceGuideCopy.common.linkUnavailable }}
        </p>
        <p v-if="hasReference" class="device-guide__external-note">
          {{ deviceGuideCopy.common.externalLinkNote }}
        </p>
      </div>
    </template>
  </section>
</template>

<style scoped>
.device-guide {
  margin-top: 24px;
  padding: 20px 0 0;
  border-top: 1px solid #dce3d7;
  color: #233d37;
}

.device-guide__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.device-guide__header h2 {
  font-size: 1.0625rem;
  font-weight: 680;
  letter-spacing: -0.02em;
}

.device-guide__header :deep(.app-icon) {
  width: 1.25rem;
  height: 1.25rem;
  color: #536c53;
}

.device-guide__notice,
.device-guide__state,
.device-guide__error,
.device-guide__external-note {
  max-width: 72ch;
  font-size: 0.875rem;
  line-height: 1.7;
}

.device-guide__notice {
  margin-top: 13px;
  color: #53675a;
}

.device-guide__state {
  margin-top: 13px;
  color: #53675a;
}

.device-guide__error {
  margin-top: 13px;
  color: #925b3a;
}

.device-guide__retry {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  padding: 8px 12px;
  border: 0;
  border-radius: 8px;
  background: #eef2e8;
  color: #435d4c;
  font: inherit;
  font-size: 0.875rem;
  font-weight: 650;
}

.device-guide__retry:hover {
  background: #e4eadd;
}

.device-guide__references {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 15px;
}

.device-guide__references a {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: 8px;
  padding: 9px 12px;
  border: 1px solid #d4e0d1;
  border-radius: 8px;
  background: #e8efe5;
  color: #234e41;
  font-size: 0.875rem;
  font-weight: 650;
  text-decoration: none;
}

.device-guide__references a:hover {
  background: #dde9db;
}

.device-guide__external-note {
  flex-basis: 100%;
  color: #53675a;
}

.device-guide__references .device-guide__state {
  flex-basis: 100%;
  margin-top: 0;
}
</style>
