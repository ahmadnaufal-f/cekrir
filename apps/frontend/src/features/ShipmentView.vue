<script setup lang="ts">
import { computed, onUnmounted, ref, shallowRef, watch } from 'vue'
import { useRouter } from 'vue-router'
import BackButton from '../components/BackButton.vue'
import DeliveryCard from '../components/DeliveryCard.vue'
import DeliveryCardSkeleton from '../components/DeliveryCardSkeleton.vue'
import DeliverySummaryCard from '../components/DeliverySummaryCard.vue'
import EmptyState from '../components/EmptyState.vue'
import PageHeader from '../components/PageHeader.vue'
import PullToRefresh from '../components/PullToRefresh.vue'
import RefreshButton from '../components/RefreshButton.vue'
import SearchInput from '../components/SearchInput.vue'
import type { ApiServices, Shipment, User } from './api/contracts'
import { deliveryCopy as copy } from '../lib/delivery-copy'
import { getCalendarDate } from '../lib/delivery-date'
import { normalizeDeliverySearch } from '../lib/delivery-search'
import { errorMessage, formatTime } from '../lib/strings'
import { ServiceError } from '../services/contracts'
import type { DeliveryTotals } from '../types/app'
const props = defineProps<{
  services: ApiServices
  user: User
  id: string | null
  revision: number
  notifiedShipmentId?: string
}>()
const emit = defineEmits<{ open: [id: string]; back: [] }>()
const router = useRouter()
const items = shallowRef<Shipment[]>([])
const selected = ref<Shipment | null>(null)
const loading = ref(false)
const historyLoading = ref(false)
const historyError = ref('')
const mutation = ref(false)
const trackingUpdated = ref(false)
const error = ref('')
const next = ref<number | null>(null)
const displayPageSize = 20
const visibleLimit = ref(displayPageSize)
const searchQuery = ref('')
const query = computed(() => normalizeDeliverySearch(searchQuery.value))
const showSearch = computed(
  () => items.value.length > 1 || next.value !== null || !!query.value,
)
const matching = computed(() => {
  if (!query.value) return items.value
  return items.value.filter(({ resi_number, courier }) =>
    normalizeDeliverySearch(`${resi_number} ${courier}`).includes(query.value),
  )
})
const visibleItems = computed(() => matching.value.slice(0, visibleLimit.value))
const reportingDay = shallowRef(new Date())
const timeZone = new Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'
const totalsQuery = computed(() => ({
  date: getCalendarDate(reportingDay.value, timeZone),
  timeZone,
}))
const busy = computed(() => loading.value || historyLoading.value)
const totals = computed<DeliveryTotals | null>((previous) => {
  if (error.value || historyError.value) return null
  if (busy.value) return previous ?? null
  if (next.value !== null) return null
  const today = reportingDay.value.toDateString()
  return {
    ...totalsQuery.value,
    receivedToday: items.value.filter(
      ({ created_at }) => new Date(created_at).toDateString() === today,
    ).length,
    receivedAllTime: items.value.length,
  }
})
const statusLabels = {
  pending: 'Menunggu',
  in_transit: 'Dalam perjalanan',
  delivered: 'Terkirim',
  exception: 'Kendala',
}
let controller: AbortController | null = null
let version = 0
const title = computed(() => (props.id ? 'Detail paket' : 'Paket'))
const unique = (values: Shipment[]) => [
  ...new Map(values.map((item) => [item.id, item])).values(),
]
function shipmentErrorMessage(cause: unknown) {
  return cause instanceof ServiceError && cause.status === 503
    ? 'Layanan paket sedang tidak tersedia. Coba lagi.'
    : errorMessage(cause)
}

function deliveryCard(item: Shipment) {
  return {
    id: item.id,
    trackingNumber: item.resi_number,
    courier: { code: item.courier, name: item.courier.toUpperCase() },
    scannedAt: item.created_at,
    photoState: 'unavailable' as const,
    trackingState: 'ready' as const,
  }
}
watch(query, () => {
  visibleLimit.value = displayPageSize
})
async function load(fresh = false) {
  controller?.abort()
  controller = new AbortController()
  const current = ++version
  loading.value = true
  error.value = ''
  trackingUpdated.value = false
  historyLoading.value = false
  historyError.value = ''
  next.value = null
  try {
    if (props.id) {
      const result = await props.services.shipments.find(
        props.id,
        controller.signal,
        fresh,
      )
      if (current === version) selected.value = result
    } else {
      reportingDay.value = new Date()
      const result = await props.services.shipments.list(0, controller.signal)
      if (current !== version) return
      items.value = unique(result.items)
      next.value = result.nextOffset
      loading.value = false
      await loadHistory()
    }
  } catch (cause) {
    if (
      current === version &&
      !(cause instanceof ServiceError && cause.code === 'cancelled')
    )
      error.value = shipmentErrorMessage(cause)
  } finally {
    if (current === version) loading.value = false
  }
}
async function loadHistory() {
  if (
    !controller ||
    next.value === null ||
    loading.value ||
    historyLoading.value
  )
    return
  const current = version
  const signal = controller.signal
  const loaded = new Map(items.value.map((item) => [item.id, item]))
  historyLoading.value = true
  historyError.value = ''
  try {
    while (next.value !== null) {
      const result = await props.services.shipments.list(next.value, signal)
      if (current !== version) return
      for (const item of result.items) loaded.set(item.id, item)
      next.value = result.nextOffset
    }
  } catch (cause) {
    if (current === version) historyError.value = shipmentErrorMessage(cause)
  } finally {
    if (current === version) {
      items.value = [...loaded.values()]
      historyLoading.value = false
    }
  }
}
function retryTotals() {
  return historyError.value ? loadHistory() : load(true)
}
const refresh = () => load(true)
async function refreshTracking() {
  const current = version
  if (!selected.value || loading.value || mutation.value) return
  mutation.value = true
  error.value = ''
  trackingUpdated.value = false
  try {
    const result = await props.services.shipments.refresh(selected.value.id)
    if (current === version) {
      selected.value = result
      trackingUpdated.value = true
    }
  } catch (cause) {
    if (current === version) error.value = shipmentErrorMessage(cause)
  } finally {
    mutation.value = false
  }
}
watch(
  () => [props.id, props.revision],
  (value, previous) => {
    selected.value = null
    void load(Boolean(previous && value[1] !== previous[1]))
  },
  { immediate: true },
)
onUnmounted(() => {
  version++
  controller?.abort()
})
</script>
<template>
  <section :class="{ 'focused-page': id }" aria-labelledby="shipments-title">
    <div v-if="id" class="sticky-header focused-page__back">
      <BackButton label="Kembali ke semua paket" @click="emit('back')" />
    </div>
    <div :class="{ 'focused-page__content': id }">
      <PageHeader
        :class="{ 'focused-page__heading': id }"
        :title="title"
        title-id="shipments-title"
      >
        <template #actions>
          <RefreshButton
            :loading="busy"
            :disabled="busy || mutation"
            @click="refresh"
          />
        </template>
        <p v-if="id">
          Catatan menampilkan data pelacakan terakhir yang tersimpan.
        </p>
        <p v-else>
          Catatan pengiriman bersama.<span class="shipment-page__touch-hint">
            {{ ` ${copy.subtitlePullHint}` }}</span
          >
        </p>
      </PageHeader>
      <p v-if="error" class="banner banner--error shipment-notice" role="alert">
        {{ error }}
        <button class="text-button" @click="load(true)">Coba lagi</button>
      </p>
      <p v-if="id && loading && !selected" class="content-inset" role="status">
        Memuat paket…
      </p>
      <template v-if="id">
        <article v-if="selected" class="panel api-detail">
          <p class="eyebrow">
            {{ selected.courier.toUpperCase() }} ·
            {{ statusLabels[selected.status] }}
          </p>
          <h2>{{ selected.resi_number }}</h2>
          <p>{{ selected.summary }}</p>
          <p v-if="selected.provider === 'demo'" class="banner">
            Pelacakan demo — contoh data, bukan hasil kurir langsung.
          </p>
          <dl class="api-facts">
            <div>
              <dt>Sumber</dt>
              <dd>{{ selected.source === 'camera' ? 'Kamera' : 'Manual' }}</dd>
            </div>
            <div>
              <dt>Ditambahkan</dt>
              <dd>{{ formatTime(selected.created_at) }}</dd>
            </div>
            <div>
              <dt>Deteksi terakhir</dt>
              <dd>
                {{
                  selected.last_detected_at
                    ? formatTime(selected.last_detected_at)
                    : 'Belum ada'
                }}
              </dd>
            </div>
            <div>
              <dt>Pelacakan diperiksa</dt>
              <dd>{{ formatTime(selected.checked_at) }}</dd>
            </div>
            <div>
              <dt>Penyedia</dt>
              <dd>{{ selected.provider }}</dd>
            </div>
          </dl>
          <div v-if="user.role === 'admin'" class="shipment-tracking">
            <button
              class="button button--primary"
              type="button"
              :disabled="loading"
              :aria-disabled="mutation || undefined"
              @click="refreshTracking"
            >
              {{ mutation ? 'Memeriksa…' : 'Periksa pelacakan' }}
            </button>
            <p class="shipment-tracking__status" role="status">
              {{ trackingUpdated ? 'Pemeriksaan pelacakan selesai.' : '' }}
            </p>
          </div>
          <h3>Riwayat pelacakan</h3>
          <p v-if="!selected.history.length">Belum ada riwayat pelacakan.</p>
          <ol class="api-history">
            <li v-for="(event, index) in selected.history" :key="index">
              <time>{{ formatTime(event.occurred_at) }}</time>
              <p>{{ event.description }}</p>
              <p v-if="event.location" class="supporting">
                {{ event.location }}
              </p>
            </li>
          </ol>
        </article>
        <p v-else-if="!loading && !error" class="banner shipment-notice">
          Paket tidak ditemukan dalam daftar yang tersedia.
        </p>
      </template>
      <PullToRefresh v-else :busy="busy" :on-refresh="refresh">
        <DeliverySummaryCard
          :query="totals ?? totalsQuery"
          :totals="totals"
          :pending="busy && !totals"
          :failed="!!(error || historyError)"
          @retry="retryTotals"
        />

        <slot name="after-summary" />

        <section
          aria-labelledby="shipment-list-title"
          class="shipment-list-panel"
        >
          <h2 id="shipment-list-title" class="content-inset">
            {{ copy.listHeading }}
          </h2>
          <SearchInput
            v-if="showSearch"
            v-model="searchQuery"
            :label="copy.searchLabel"
            :placeholder="copy.searchPlaceholder"
            :clear-label="copy.searchClear"
            controls="shipment-results"
          />
          <div id="shipment-results" :aria-busy="busy">
            <div v-if="busy && !items.length" class="shipment-cards">
              <DeliveryCardSkeleton v-for="index in 3" :key="index" />
            </div>
            <p
              v-else-if="busy && !visibleItems.length"
              class="content-inset"
              role="status"
            >
              Memeriksa riwayat paket…
            </p>
            <EmptyState
              v-else-if="!visibleItems.length && !error && !historyError"
              class="shipment-list-panel__empty"
              :icon="query ? 'search' : 'package'"
              :title="query ? copy.noResultsTitle : copy.emptyTitle"
              :description="
                query ? copy.noResultsDescription : copy.emptyDescription
              "
            />
            <ol v-else-if="visibleItems.length" class="shipment-cards">
              <li v-for="item in visibleItems" :key="item.id">
                <DeliveryCard
                  :delivery="deliveryCard(item)"
                  :href="
                    router.resolve({
                      name: 'shipment-detail',
                      params: { id: item.id },
                    }).href
                  "
                  :is-new="item.id === notifiedShipmentId"
                  timestamp-label="Ditambahkan"
                  @open="emit('open', $event)"
                >
                  <span class="supporting">
                    {{ statusLabels[item.status]
                    }}{{ item.provider === 'demo' ? ' · Pelacakan demo' : '' }}
                  </span>
                  <span class="supporting">{{ item.summary }}</span>
                </DeliveryCard>
              </li>
            </ol>
            <p
              v-if="historyError && query"
              class="banner banner--error shipment-notice"
              role="alert"
            >
              Sebagian riwayat paket belum dimuat. {{ historyError }}
              <button class="text-button" type="button" @click="retryTotals">
                {{ copy.retryMore }}
              </button>
            </p>
          </div>
          <button
            v-if="matching.length > visibleLimit"
            class="button button--quiet shipment-list-panel__more"
            type="button"
            @click="visibleLimit += displayPageSize"
          >
            {{ copy.loadMore }}
          </button>
        </section>
      </PullToRefresh>
    </div>
  </section>
</template>

<style scoped>
.shipment-page__touch-hint {
  display: none;
}

@media (any-pointer: coarse) {
  .shipment-page__touch-hint {
    display: inline;
  }
}

.shipment-notice {
  padding-inline: var(--card-inset);
}

.shipment-tracking {
  display: grid;
  gap: 6px;
}

.shipment-tracking__status {
  min-height: 1.65em;
  color: var(--accent);
  font-size: 0.875rem;
}

.shipment-list-panel {
  display: grid;
  gap: 16px;
}

.shipment-list-panel__empty {
  align-items: flex-start;
  padding-inline: var(--card-inset);
  text-align: start;
}

.shipment-cards {
  display: grid;
  gap: 12px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.shipment-list-panel__more {
  width: 100%;
  justify-content: flex-start;
  padding-inline: var(--card-text-inset);
}
</style>
