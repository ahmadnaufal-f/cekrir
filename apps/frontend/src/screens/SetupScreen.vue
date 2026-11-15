<script setup lang="ts">
import { computed, onUnmounted, reactive, watch } from 'vue'
import { adminCopy } from '../lib/admin-copy'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, SetupContent } from '../types/app'

const props = defineProps<{ services: AppServices; user: AppUser }>()
const emit = defineEmits<{ sessionExpired: [] }>()

type SetupKind = SetupContent['kind']
type LoadState = 'idle' | 'loading' | 'ready' | 'error'

const copy = adminCopy.setup
const content = reactive<Record<SetupKind, SetupContent | null>>({
  esp32: null,
  bardi: null,
})
const loadState = reactive<Record<SetupKind, LoadState>>({
  esp32: 'idle',
  bardi: 'idle',
})
const loadError = reactive<Record<SetupKind, string>>({ esp32: '', bardi: '' })
const isAdmin = computed(() => props.user.role === 'admin')

const esp32SourceHref = computed(() =>
  configuredReference(content.esp32, 'source'),
)
const esp32GuideHref = computed(() =>
  configuredReference(content.esp32, 'guide'),
)
const bardiGuideHref = computed(() =>
  configuredReference(content.bardi, 'guide'),
)

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
  emit('sessionExpired')
  return true
}

function configuredReference(
  resource: SetupContent | null,
  target: 'source' | 'guide',
): string | null {
  if (!resource) return null
  const reference = target === 'source' ? resource.sourceUrl : resource.guideUrl
  if (!reference) return null

  const knownEsp32Paths = {
    source: 'apps/esp32/src/main.cpp',
    guide: 'apps/esp32/README.md',
  }
  const relativePath = reference.replace(/^\/+/, '')
  if (resource.kind === 'esp32' && relativePath === knownEsp32Paths[target]) {
    return `https://github.com/ahmadnaufal-f/cekrir/blob/bc45600de0906a4b7995ac71118025259072c8a5/${relativePath}`
  }

  try {
    const url = new URL(reference)
    if (
      url.protocol !== 'https:' ||
      url.origin !== 'https://github.com' ||
      url.username ||
      url.password ||
      url.search ||
      url.hash
    ) {
      return null
    }

    const prefix = '/ahmadnaufal-f/cekrir/blob/'
    if (!url.pathname.startsWith(prefix)) return null
    const pathAfterRevision = url.pathname
      .slice(prefix.length)
      .split('/')
      .slice(1)
      .join('/')
    if (resource.kind === 'esp32') {
      return pathAfterRevision === knownEsp32Paths[target]
        ? url.toString()
        : null
    }

    // BARDI guides are not present in the scaffold yet. Accept one only when
    // the setup service explicitly supplies a documentation URL in this repo.
    const isBardiGuide =
      target === 'guide' &&
      /^(?:apps|docs)\/bardi\/[A-Za-z0-9._/-]+\.md$/.test(pathAfterRevision) &&
      !pathAfterRevision.split('/').includes('..')
    return isBardiGuide ? url.toString() : null
  } catch {
    return null
  }
}

function clearContent(): void {
  content.esp32 = null
  content.bardi = null
  loadState.esp32 = 'idle'
  loadState.bardi = 'idle'
  loadError.esp32 = ''
  loadError.bardi = ''
}

async function loadContent(kind: SetupKind, generation: number): Promise<void> {
  loadState[kind] = 'loading'
  loadError[kind] = ''
  try {
    const result = await props.services.setup.content(kind)
    if (!isCurrent(generation)) return
    content[kind] = result
    loadState[kind] = 'ready'
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (!reportUnauthorized(cause, generation)) {
      loadState[kind] = 'error'
      loadError[kind] = copy.loadingFailed
    }
  }
}

function retry(kind: SetupKind): void {
  if (!isAdmin.value) return
  void loadContent(kind, requestGeneration)
}

watch(
  [() => props.user.id, () => props.user.householdId, () => props.user.role],
  () => {
    requestGeneration += 1
    clearContent()
    if (!isAdmin.value) return
    void loadContent('esp32', requestGeneration)
    void loadContent('bardi', requestGeneration)
  },
  { immediate: true, flush: 'sync' },
)

onUnmounted(() => {
  disposed = true
  requestGeneration += 1
  clearContent()
})
</script>

<template>
  <section class="admin-screen setup-screen" aria-labelledby="setup-title">
    <header class="admin-screen__header">
      <h1 id="setup-title">{{ copy.title }}</h1>
      <p class="admin-screen__intro">{{ copy.intro }}</p>
    </header>

    <p
      v-if="!isAdmin"
      class="admin-screen__banner admin-screen__banner--error"
      role="alert"
    >
      {{ adminCopy.common.adminOnly }}
    </p>

    <div v-else class="setup-list">
      <section class="admin-panel" aria-labelledby="esp32-setup-title">
        <h2 id="esp32-setup-title">{{ copy.esp32Title }}</h2>
        <p class="admin-panel__copy">{{ copy.esp32Description }}</p>

        <p
          v-if="loadState.esp32 === 'loading'"
          class="setup-state"
          role="status"
        >
          {{ adminCopy.common.loading }}
        </p>
        <div
          v-else-if="loadState.esp32 === 'error'"
          class="setup-state setup-state--error"
          role="alert"
        >
          {{ loadError.esp32 }}
          <button
            class="admin-button admin-button--quiet"
            type="button"
            @click="retry('esp32')"
          >
            {{ adminCopy.common.retry }}
          </button>
        </div>
        <div v-else class="setup-links">
          <a
            v-if="esp32SourceHref"
            :href="esp32SourceHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ copy.sourceLink }}
          </a>
          <a
            v-if="esp32GuideHref"
            :href="esp32GuideHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ copy.guideLink }}
          </a>
          <p v-if="!esp32SourceHref && !esp32GuideHref" class="setup-state">
            {{ copy.linkUnavailable }}
          </p>
          <p v-if="esp32SourceHref || esp32GuideHref" class="setup-links__note">
            {{ copy.externalLinkNote }}
          </p>
        </div>
      </section>

      <section class="admin-panel" aria-labelledby="bardi-setup-title">
        <h2 id="bardi-setup-title">{{ copy.bardiTitle }}</h2>
        <p class="setup-pending" role="status">{{ copy.bardiPending }}</p>

        <p
          v-if="loadState.bardi === 'loading'"
          class="setup-state"
          role="status"
        >
          {{ adminCopy.common.loading }}
        </p>
        <div
          v-else-if="loadState.bardi === 'error'"
          class="setup-state setup-state--error"
          role="alert"
        >
          {{ loadError.bardi }}
          <button
            class="admin-button admin-button--quiet"
            type="button"
            @click="retry('bardi')"
          >
            {{ adminCopy.common.retry }}
          </button>
        </div>
        <div v-else class="setup-links">
          <a
            v-if="bardiGuideHref"
            :href="bardiGuideHref"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ copy.guideLink }}
          </a>
          <p v-else class="setup-state">{{ copy.linkUnavailable }}</p>
          <p v-if="bardiGuideHref" class="setup-links__note">
            {{ copy.externalLinkNote }}
          </p>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.admin-screen {
  width: min(100%, 920px);
  margin: 0 auto;
  padding: 44px 0 64px;
  color: #233d37;
}

.admin-screen__header {
  margin-bottom: 28px;
}

.admin-screen__header h1 {
  margin: 0 0 10px;
  font-size: 1.75rem;
  letter-spacing: -1px;
  line-height: 1.2;
}

.admin-screen__intro,
.admin-panel__copy {
  max-width: 700px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.7;
}

.admin-screen__banner {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #d3ddc7;
  border-radius: 8px;
  background: #e9eedf;
  color: #526b46;
  font-size: 0.875rem;
  line-height: 1.6;
}

.admin-screen__banner--error {
  border-color: #e6ccba;
  background: #f9e9df;
  color: #925b3a;
}

.setup-list {
  display: grid;
  gap: 18px;
}

.admin-panel {
  padding: clamp(20px, 4vw, 28px);
  border: 1px solid #e0e4d9;
  border-radius: 12px;
  background: #fffefa;
  box-shadow: 0 10px 28px #233d3708;
}

.admin-panel h2 {
  font-size: 1.25rem;
  letter-spacing: -0.5px;
}

.admin-panel__copy {
  margin-top: 10px;
  font-size: 0.875rem;
}

.setup-pending {
  margin-top: 16px;
  padding: 13px 15px;
  border: 1px solid #e6dcc1;
  border-radius: 8px;
  background: #f8f3e6;
  color: #79673f;
  font-size: 0.875rem;
  line-height: 1.6;
}

.setup-state {
  margin-top: 16px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.6;
}

.setup-state--error {
  color: #925b3a;
}

.setup-links {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
  margin-top: 18px;
}

.setup-links a {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  padding: 10px 14px;
  border-radius: 7px;
  background: #234e41;
  color: #f6f7ef;
  font-size: 0.875rem;
  font-weight: 600;
  text-decoration: none;
}

.setup-links a:hover {
  background: #173e32;
}

.setup-links__note {
  flex-basis: 100%;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.admin-button {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  margin-left: 10px;
  padding: 9px 13px;
  border: 0;
  border-radius: 7px;
  background: #eef2e8;
  color: #536c53;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
}

.admin-button:focus-visible,
.setup-links a:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 3px;
}

@media (max-width: 620px) {
  .admin-screen {
    padding: 30px 0 48px;
  }
}
</style>
