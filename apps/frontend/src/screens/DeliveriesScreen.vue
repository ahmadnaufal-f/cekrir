<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import DeliveryResourceStates from '../components/DeliveryResourceStates.vue'
import {
  deliveryCopy,
  deliveryRequestError,
  deliveryRequestStatus,
  formatDeliveryTimestamp,
} from '../lib/delivery-copy'
import { ui } from '../lib/strings'
import type { AppServices } from '../services/contracts'
import type { AppUser, DeliverySummary } from '../types/app'

const props = defineProps<{
  services: AppServices
  user: AppUser
  refreshKey?: number
}>()

const emit = defineEmits<{
  open: [id: string]
  sessionExpired: []
}>()

const deliveries = shallowRef<DeliverySummary[]>([])
const nextCursor = shallowRef<string | null>(null)
const listError = shallowRef<unknown | null>(null)
const moreError = shallowRef<unknown | null>(null)
const loading = shallowRef(true)
const refreshing = shallowRef(false)
const loadingMore = shallowRef(false)
const listErrorMessage = computed(() =>
  listError.value ? deliveryRequestError(listError.value, 'list') : '',
)
const moreErrorMessage = computed(() =>
  moreError.value ? deliveryRequestError(moreError.value, 'list') : '',
)

let scopeVersion = 0
let requestVersion = 0

function uniqueFirst(items: DeliverySummary[]): DeliverySummary[] {
  const seen = new Set<string>()
  return items.filter((item) => {
    if (seen.has(item.id)) return false
    seen.add(item.id)
    return true
  })
}

function forCurrentHousehold(items: DeliverySummary[]): DeliverySummary[] {
  return items.filter((item) => item.householdId === props.user.householdId)
}

function clearOnAuthFailure(cause: unknown): void {
  const status = deliveryRequestStatus(cause)
  if (status === 401 || status === 403 || status === 404) {
    deliveries.value = []
    nextCursor.value = null
  }
  if (status === 401) emit('sessionExpired')
}

async function loadFirstPage(preserveRows: boolean): Promise<void> {
  const scope = scopeVersion
  const request = ++requestVersion
  loadingMore.value = false
  moreError.value = null
  if (preserveRows) {
    refreshing.value = true
  } else {
    loading.value = true
    refreshing.value = false
  }
  listError.value = null

  try {
    const page = await props.services.deliveries.list()
    if (scope !== scopeVersion || request !== requestVersion) return
    const firstPage = uniqueFirst(forCurrentHousehold(page.items))
    deliveries.value = preserveRows
      ? uniqueFirst([...firstPage, ...deliveries.value])
      : firstPage
    nextCursor.value = page.nextCursor
  } catch (cause) {
    if (scope !== scopeVersion || request !== requestVersion) return
    clearOnAuthFailure(cause)
    listError.value = cause
  } finally {
    if (scope === scopeVersion && request === requestVersion) {
      loading.value = false
      refreshing.value = false
    }
  }
}

async function loadMore(): Promise<void> {
  const cursor = nextCursor.value
  if (!cursor || loading.value || refreshing.value || loadingMore.value) return

  const scope = scopeVersion
  const request = ++requestVersion
  loadingMore.value = true
  moreError.value = null

  try {
    const page = await props.services.deliveries.list(cursor)
    if (scope !== scopeVersion || request !== requestVersion) return
    deliveries.value = uniqueFirst([
      ...deliveries.value,
      ...forCurrentHousehold(page.items),
    ])
    nextCursor.value = page.nextCursor
  } catch (cause) {
    if (scope !== scopeVersion || request !== requestVersion) return
    clearOnAuthFailure(cause)
    moreError.value = cause
  } finally {
    if (scope === scopeVersion && request === requestVersion)
      loadingMore.value = false
  }
}

function retryList(): void {
  void loadFirstPage(deliveries.value.length > 0)
}

watch(
  () =>
    [
      props.user.id,
      props.user.householdId,
      props.user.role,
      props.services,
    ] as const,
  () => {
    scopeVersion += 1
    requestVersion += 1
    deliveries.value = []
    nextCursor.value = null
    listError.value = null
    moreError.value = null
    loading.value = true
    refreshing.value = false
    loadingMore.value = false
    void loadFirstPage(false)
  },
  { immediate: true },
)

watch(
  () => props.refreshKey,
  (value, previous) => {
    if (previous !== undefined && value !== previous)
      void loadFirstPage(deliveries.value.length > 0)
  },
)

onUnmounted(() => {
  scopeVersion += 1
  requestVersion += 1
})
</script>

<template>
  <section class="deliveries-screen" aria-labelledby="deliveries-screen-title">
    <header class="deliveries-screen__header">
      <div>
        <h1 id="deliveries-screen-title">{{ ui.deliveries }}</h1>
        <p>{{ deliveryCopy.listDescription }}</p>
      </div>
      <button
        class="button button--quiet deliveries-screen__refresh"
        type="button"
        :disabled="loading || refreshing"
        @click="retryList"
      >
        {{ refreshing ? deliveryCopy.listReloading : ui.refresh }}
      </button>
    </header>

    <div v-if="listError" class="banner banner--error" role="alert">
      <span>{{ listErrorMessage }}</span>
      <button class="text-button" type="button" @click="retryList">
        {{ deliveryCopy.retryList }}
      </button>
    </div>
    <div v-else-if="refreshing" class="banner" role="status">
      {{ deliveryCopy.listRefreshing }}
    </div>

    <section
      class="panel deliveries-panel"
      aria-labelledby="deliveries-heading"
    >
      <div class="deliveries-panel__heading">
        <h2 id="deliveries-heading">{{ deliveryCopy.listHeading }}</h2>
        <span v-if="!loading" class="muted">
          {{ deliveryCopy.deliveryCount(deliveries.length) }}
        </span>
      </div>

      <div
        v-if="loading"
        class="delivery-skeletons"
        role="status"
        :aria-label="deliveryCopy.listLoading"
      >
        <div v-for="index in 3" :key="index" class="delivery-skeleton">
          <span></span><span></span>
        </div>
      </div>

      <div
        v-else-if="!deliveries.length && !listError"
        class="empty-state deliveries-empty"
      >
        <h3>{{ deliveryCopy.emptyTitle }}</h3>
        <p>{{ deliveryCopy.emptyDescription }}</p>
      </div>

      <ol
        v-else-if="deliveries.length"
        class="delivery-list"
        :aria-busy="refreshing"
      >
        <li v-for="delivery in deliveries" :key="delivery.id">
          <button
            class="delivery-row"
            type="button"
            :aria-label="`${deliveryCopy.openDetails}: ${delivery.trackingNumber}`"
            @click="emit('open', delivery.id)"
          >
            <span class="delivery-row__main">
              <strong class="delivery-row__number">{{
                delivery.trackingNumber
              }}</strong>
              <span class="delivery-row__courier">
                {{ delivery.courier?.name || deliveryCopy.unknownCourier }}
              </span>
              <span class="delivery-row__time">
                <span>{{ ui.scannedAt }}</span>
                <time :datetime="delivery.scannedAt">{{
                  formatDeliveryTimestamp(delivery.scannedAt)
                }}</time>
              </span>
            </span>
            <DeliveryResourceStates
              class="delivery-row__states"
              :photo-state="delivery.photoState"
              :tracking-state="delivery.trackingState"
            />
          </button>
        </li>
      </ol>

      <div
        v-if="moreError"
        class="banner banner--error delivery-more-error"
        role="alert"
      >
        <span>{{ moreErrorMessage }}</span>
        <button class="text-button" type="button" @click="loadMore">
          {{ deliveryCopy.retryMore }}
        </button>
      </div>

      <button
        v-if="nextCursor && !loading && !listError"
        class="button button--quiet deliveries-panel__more"
        type="button"
        :disabled="loadingMore || refreshing"
        @click="loadMore"
      >
        {{ loadingMore ? deliveryCopy.loadingMore : deliveryCopy.loadMore }}
      </button>
    </section>
  </section>
</template>

<style scoped>
.deliveries-screen {
  width: min(100%, 820px);
  margin: 0 auto;
  padding: 42px 0 64px;
}

.deliveries-screen__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 26px;
}

.deliveries-screen__header h1 {
  margin: 0 0 8px;
  font-size: 1.875rem;
  letter-spacing: -0.8px;
  line-height: 1.2;
}

.deliveries-screen__header p {
  max-width: 60ch;
  color: #627060;
  font-size: 0.875rem;
  line-height: 1.6;
}

.deliveries-screen__refresh {
  flex-shrink: 0;
}

.deliveries-panel {
  padding: 0 24px;
}

.deliveries-panel__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  min-height: 66px;
  padding: 20px 0 14px;
  border-bottom: 1px solid #e9ece3;
}

.deliveries-panel__heading h2 {
  margin: 0;
  font-size: 1.0625rem;
}

.delivery-list {
  margin: 0;
  padding: 0;
  list-style: none;
}

.delivery-list > li + li {
  border-top: 1px solid #e9ece3;
}

.delivery-row {
  display: flex;
  width: 100%;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  padding: 18px 2px;
  border: 0;
  background: transparent;
  color: #233d37;
  text-align: left;
  transition: background-color 160ms ease-out;
}

.delivery-row:hover {
  background: #f6f7f2;
}

.delivery-row:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 2px;
}

.delivery-row__main {
  display: grid;
  min-width: 0;
  gap: 5px;
}

.delivery-row__number {
  overflow-wrap: anywhere;
  color: #233d37;
  font-size: 0.9375rem;
  font-weight: 700;
  line-height: 1.4;
}

.delivery-row__courier {
  color: #65725f;
  font-size: 0.8125rem;
}

.delivery-row__time {
  display: flex;
  flex-wrap: wrap;
  gap: 3px 7px;
  color: #667366;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.delivery-row__time span {
  font-weight: 650;
}

.delivery-row__states {
  justify-content: flex-end;
}

.deliveries-empty {
  margin-top: 18px;
  padding: 42px 20px;
}

.deliveries-empty h3 {
  margin: 0 0 8px;
  color: #435d4c;
  font-size: 1rem;
}

.deliveries-empty p {
  max-width: 56ch;
  margin: 0 auto;
  line-height: 1.7;
}

.delivery-skeletons {
  display: grid;
}

.delivery-skeleton {
  display: grid;
  gap: 10px;
  padding: 20px 2px;
  border-bottom: 1px solid #e9ece3;
}

.delivery-skeleton span {
  height: 10px;
  border-radius: 4px;
  background: #edf0e8;
}

.delivery-skeleton span:first-child {
  width: min(250px, 65%);
  height: 13px;
}

.delivery-skeleton span:last-child {
  width: min(170px, 45%);
}

.delivery-more-error {
  margin: 16px 0;
}

.deliveries-panel__more {
  width: 100%;
  justify-content: center;
  margin: 16px 0 20px;
}

@media (max-width: 640px) {
  .deliveries-screen {
    padding: 28px 0 46px;
  }

  .deliveries-screen__header {
    align-items: flex-start;
    gap: 12px;
  }

  .deliveries-screen__header h1 {
    font-size: 1.625rem;
  }

  .deliveries-screen__header p {
    font-size: 0.8125rem;
  }

  .deliveries-screen__refresh {
    padding: 10px 12px;
    font-size: 0.8125rem;
  }

  .deliveries-panel {
    padding: 0 16px;
  }

  .delivery-row {
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .delivery-row__states {
    justify-content: flex-start;
  }
}

@media (max-width: 390px) {
  .deliveries-screen__header {
    flex-direction: column;
  }
}
</style>
