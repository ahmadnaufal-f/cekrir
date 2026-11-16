<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import { configuredReference } from '../lib/setup-reference'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, SetupContent } from '../types/app'

const props = defineProps<{
  services: AppServices
  user: AppUser
  kind: 'esp32' | 'bardi'
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
    <h3 :id="`${kind}-guide-title`">
      <AppIcon :name="kind === 'esp32' ? 'device' : 'camera'" />
      {{ copy.title }}
    </h3>

    <p v-if="!isAdmin" class="device-guide__notice" role="alert">
      {{ deviceGuideCopy.common.adminOnly }}
    </p>

    <template v-else>
      <p class="device-guide__description">{{ copy.description }}</p>

      <ol class="device-guide__steps">
        <li v-for="step in copy.steps" :key="step">{{ step }}</li>
      </ol>

      <p v-if="kind === 'esp32'" class="device-guide__notice" role="note">
        {{ deviceGuideCopy.esp32.scaffoldNote }}
      </p>
      <p v-else class="device-guide__notice" role="status">
        {{ deviceGuideCopy.bardi.pending }}
      </p>

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
          {{
            kind === 'esp32'
              ? deviceGuideCopy.esp32.guideLink
              : deviceGuideCopy.bardi.guideLink
          }}
        </a>
        <p v-if="!hasReference && kind === 'esp32'" class="device-guide__state">
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
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #e9ece3;
  color: #435d4c;
}

.device-guide h3 {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.9375rem;
  font-weight: 650;
}

.device-guide__description,
.device-guide__steps,
.device-guide__notice,
.device-guide__state,
.device-guide__error,
.device-guide__external-note {
  max-width: 72ch;
  font-size: 0.8125rem;
  line-height: 1.65;
}

.device-guide__description {
  margin-top: 8px;
  color: #53675a;
}

.device-guide__steps {
  display: grid;
  gap: 8px;
  margin: 14px 0 0;
  padding-left: 1.25rem;
  color: #435d4c;
}

.device-guide__steps li {
  padding-left: 2px;
}

.device-guide__notice {
  margin-top: 14px;
  color: #53675a;
}

.device-guide__state {
  margin-top: 14px;
  color: #53675a;
}

.device-guide__error {
  margin-top: 14px;
  color: #925b3a;
}

.device-guide__retry {
  gap: 8px;
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  margin-top: 8px;
  padding: 8px 12px;
  border: 0;
  border-radius: 7px;
  background: #eef2e8;
  color: #536c53;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
}

.device-guide__retry:hover {
  background: #e4eadd;
}

.device-guide__references {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 14px;
}

.device-guide__references a {
  gap: 8px;
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  padding: 9px 12px;
  border-radius: 7px;
  background: #234e41;
  color: #f6f7ef;
  font-size: 0.8125rem;
  font-weight: 600;
  text-decoration: none;
}

.device-guide__references a:hover {
  background: #173e32;
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
