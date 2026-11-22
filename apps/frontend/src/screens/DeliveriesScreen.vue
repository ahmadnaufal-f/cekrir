<script setup lang="ts">
import {
  computed,
  nextTick,
  onUnmounted,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue'
import DeliveryCard from '../components/DeliveryCard.vue'
import DeliveryCardSkeleton from '../components/DeliveryCardSkeleton.vue'
import DeliverySummaryCard from '../components/DeliverySummaryCard.vue'
import AppIcon from '../components/AppIcon.vue'
import PullToRefresh from '../components/PullToRefresh.vue'
import EmptyState from '../components/EmptyState.vue'
import SearchInput from '../components/SearchInput.vue'
import { useDeliveryTotals } from '../composables/useDeliveryTotals'
import {
  deliveryCopy,
  deliveryRequestError,
  deliveryRequestStatus,
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
const searchQuery = shallowRef('')
const hasMultipleDeliveries = shallowRef(false)
const hasSearch = computed(() => searchQuery.value.trim().length > 0)
const showSearch = computed(
  () => hasMultipleDeliveries.value || hasSearch.value,
)
const screen = useTemplateRef<HTMLElement>('screen')
const skeletonCount = computed(() => Math.max(3, deliveries.value.length))
const {
  query: totalsQuery,
  totals,
  pending: totalsPending,
  failed: totalsFailed,
  reload: reloadTotals,
} = useDeliveryTotals({
  service: () => props.services.deliveries,
  userKey: () =>
    `${props.user.id}:${props.user.householdId}:${props.user.role}`,
  refreshKey: () => props.refreshKey ?? 0,
  onSessionExpired: () => emit('sessionExpired'),
})
const refreshBusy = computed(
  () =>
    loading.value ||
    refreshing.value ||
    loadingMore.value ||
    totalsPending.value,
)
const summaryBlocked = computed(() =>
  [listError.value, moreError.value].some((cause) =>
    [401, 403, 404].includes(deliveryRequestStatus(cause)),
  ),
)
const listErrorMessage = computed(() =>
  listError.value ? deliveryRequestError(listError.value, 'list') : '',
)
const moreErrorMessage = computed(() =>
  moreError.value ? deliveryRequestError(moreError.value, 'list') : '',
)

let scopeVersion = 0
let requestVersion = 0
let focusedCard: string | null = null
let loadedSearch = ''
let resettingScope = false
let searchTimer: ReturnType<typeof setTimeout> | undefined

watch(
  totals,
  (value) => {
    if (value) hasMultipleDeliveries.value = value.receivedAllTime > 1
  },
  { flush: 'sync' },
)

watch(
  () => searchQuery.value.trim(),
  () => {
    if (resettingScope) return
    clearTimeout(searchTimer)
    requestVersion++
    deliveries.value = []
    nextCursor.value = null
    listError.value = null
    moreError.value = null
    loadingMore.value = false
    refreshing.value = false
    loading.value = true
    searchTimer = setTimeout(() => {
      searchTimer = undefined
      void loadFirstPage(false)
    }, 250)
  },
  { flush: 'sync' },
)

watch(refreshing, async (active) => {
  if (active) {
    const focused = document.activeElement
    focusedCard =
      focused instanceof HTMLAnchorElement &&
      screen.value?.contains(focused) &&
      focused.classList.contains('delivery-card')
        ? focused.getAttribute('href')
        : null
    return
  }
  const href = focusedCard
  focusedCard = null
  if (!href) return
  await nextTick()
  if (document.activeElement !== document.body) return
  Array.from(
    screen.value?.querySelectorAll<HTMLAnchorElement>('.delivery-card') ?? [],
  )
    .find((card) => card.getAttribute('href') === href)
    ?.focus({ preventScroll: true })
})

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
  clearTimeout(searchTimer)
  searchTimer = undefined
  const scope = scopeVersion
  const request = ++requestVersion
  const search = searchQuery.value.trim()
  const keepRows = preserveRows && search === loadedSearch
  loadingMore.value = false
  moreError.value = null
  if (keepRows) {
    refreshing.value = true
  } else {
    deliveries.value = []
    loading.value = true
    refreshing.value = false
  }
  listError.value = null

  try {
    const page = await props.services.deliveries.list(undefined, { search })
    if (
      scope !== scopeVersion ||
      request !== requestVersion ||
      search !== searchQuery.value.trim()
    )
      return
    const firstPage = uniqueFirst(forCurrentHousehold(page.items))
    deliveries.value = keepRows
      ? uniqueFirst([...firstPage, ...deliveries.value])
      : firstPage
    loadedSearch = search
    if (!search)
      hasMultipleDeliveries.value =
        firstPage.length > 1 || page.nextCursor !== null
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
  const search = loadedSearch
  if (!cursor || loading.value || refreshing.value || loadingMore.value) return

  const scope = scopeVersion
  const request = ++requestVersion
  loadingMore.value = true
  moreError.value = null

  try {
    const page = await props.services.deliveries.list(cursor, { search })
    if (
      scope !== scopeVersion ||
      request !== requestVersion ||
      search !== searchQuery.value.trim()
    )
      return
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

async function retryList(): Promise<void> {
  if (refreshBusy.value) return
  await Promise.all([
    loadFirstPage(deliveries.value.length > 0),
    reloadTotals(true),
  ])
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
    clearTimeout(searchTimer)
    searchTimer = undefined
    resettingScope = true
    searchQuery.value = ''
    resettingScope = false
    loadedSearch = ''
    hasMultipleDeliveries.value = false
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
    if (previous !== undefined && value !== previous) {
      void loadFirstPage(deliveries.value.length > 0)
    }
  },
)

onUnmounted(() => {
  clearTimeout(searchTimer)
  scopeVersion += 1
  requestVersion += 1
})
</script>

<template>
  <section
    ref="screen"
    class="deliveries-screen"
    aria-labelledby="deliveries-screen-title"
  >
    <header class="deliveries-screen__header">
      <div>
        <h1 id="deliveries-screen-title">{{ ui.deliveries }}</h1>
        <p>
          {{ deliveryCopy.listDescription
          }}<span class="deliveries-screen__touch-instruction">
            {{ ` ${deliveryCopy.subtitlePullHint}` }}</span
          >
        </p>
      </div>
    </header>

    <PullToRefresh :busy="refreshBusy" :on-refresh="retryList">
      <div v-if="listError" class="banner banner--error" role="alert">
        <span>{{ listErrorMessage }}</span>
        <button
          class="text-button"
          type="button"
          :disabled="refreshBusy"
          @click="retryList"
        >
          <AppIcon name="refresh" />
          {{ deliveryCopy.retryList }}
        </button>
      </div>

      <DeliverySummaryCard
        v-if="!summaryBlocked"
        :query="totalsQuery"
        :totals="totals"
        :pending="totalsPending"
        :failed="totalsFailed"
        @retry="reloadTotals(true)"
      />

      <section
        class="deliveries-panel"
        id="delivery-results"
        aria-labelledby="deliveries-heading"
        :aria-busy="loading || refreshing || loadingMore"
      >
        <div class="deliveries-panel__heading">
          <h2 id="deliveries-heading">{{ deliveryCopy.listHeading }}</h2>
        </div>

        <SearchInput
          v-if="showSearch"
          v-model="searchQuery"
          class="deliveries-panel__search"
          :label="deliveryCopy.searchLabel"
          :placeholder="deliveryCopy.searchPlaceholder"
          :clear-label="deliveryCopy.searchClear"
          controls="delivery-results"
        />

        <div
          v-if="loading || refreshing"
          class="delivery-skeletons"
          aria-hidden="true"
        >
          <DeliveryCardSkeleton v-for="index in skeletonCount" :key="index" />
        </div>

        <EmptyState
          v-else-if="!deliveries.length && !listError"
          :icon="hasSearch ? 'search' : 'package'"
          :title="
            hasSearch ? deliveryCopy.noResultsTitle : deliveryCopy.emptyTitle
          "
          :description="
            hasSearch
              ? deliveryCopy.noResultsDescription
              : deliveryCopy.emptyDescription
          "
        />

        <ol
          v-else-if="deliveries.length"
          class="delivery-list"
          :aria-busy="loadingMore"
        >
          <li v-for="delivery in deliveries" :key="delivery.id">
            <DeliveryCard :delivery="delivery" @open="emit('open', $event)" />
          </li>
          <li v-if="loadingMore" class="delivery-skeletons" aria-hidden="true">
            <DeliveryCardSkeleton v-for="index in 3" :key="index" />
          </li>
        </ol>

        <div
          v-if="moreError"
          class="banner banner--error delivery-more-error"
          role="alert"
        >
          <span>{{ moreErrorMessage }}</span>
          <button class="text-button" type="button" @click="loadMore">
            <AppIcon name="refresh" />
            {{ deliveryCopy.retryMore }}
          </button>
        </div>

        <button
          v-if="
            nextCursor && !loading && !refreshing && !loadingMore && !listError
          "
          class="button button--quiet deliveries-panel__more"
          type="button"
          @click="loadMore"
        >
          {{ deliveryCopy.loadMore }}
        </button>
      </section>
    </PullToRefresh>
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
.deliveries-screen__header > div {
  min-width: 0;
}

.deliveries-screen__header p {
  max-width: 60ch;
  color: #627060;
  font-size: 0.875rem;
  line-height: 1.6;
}

.deliveries-panel__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.deliveries-panel__heading h2 {
  margin: 0;
  font-size: 1.0625rem;
}
.deliveries-screen__touch-instruction {
  display: none;
}
@media (any-pointer: coarse) {
  .deliveries-screen__touch-instruction {
    display: inline;
  }
}
.deliveries-panel__search {
  margin-bottom: 16px;
}

.delivery-list {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.delivery-skeletons {
  display: grid;
  gap: 12px;
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
}
</style>
