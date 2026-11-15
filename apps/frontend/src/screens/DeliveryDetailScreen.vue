<script setup lang="ts">
import { computed, onUnmounted, shallowRef, watch } from 'vue'
import DeliveryPhoto from '../components/DeliveryPhoto.vue'
import {
  deliveryCopy,
  deliveryRequestError,
  deliveryRequestStatus,
  formatDeliveryTimestamp,
} from '../lib/delivery-copy'
import { ui } from '../lib/strings'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, DeliveryDetail } from '../types/app'

const props = defineProps<{
  services: AppServices
  user: AppUser
  deliveryId: string
  refreshKey?: number
}>()

const emit = defineEmits<{
  back: []
  sessionExpired: []
}>()

const detail = shallowRef<DeliveryDetail | null>(null)
const detailError = shallowRef<unknown | null>(null)
const loading = shallowRef(true)
const refreshing = shallowRef(false)
const photoRefreshKey = shallowRef(0)
const detailErrorMessage = computed(() =>
  detailError.value ? deliveryRequestError(detailError.value, 'detail') : '',
)
const tracking = computed(() => detail.value?.tracking ?? null)
const trackingFields = computed<{ label: string; value: string }[]>(() => {
  const value = tracking.value
  if (!value) return []

  const fields = [
    { label: deliveryCopy.service, value: value.service },
    {
      label: deliveryCopy.carrierStatus,
      value: value.statusLabel || value.statusCode,
    },
    { label: deliveryCopy.sender, value: value.senderName },
    { label: deliveryCopy.recipient, value: value.recipientName },
    { label: deliveryCopy.origin, value: value.origin },
    { label: deliveryCopy.destination, value: value.destination },
  ]

  return fields.reduce<{ label: string; value: string }[]>(
    (available, field) => {
      if (field.value?.trim())
        available.push({ label: field.label, value: field.value })
      return available
    },
    [],
  )
})
const trackingEvents = computed(() => tracking.value?.events ?? [])
const hasTrackingData = computed(
  () => trackingFields.value.length > 0 || trackingEvents.value.length > 0,
)
const photoKey = computed(
  () => `${props.refreshKey ?? 0}:${photoRefreshKey.value}`,
)
const accountKey = computed(
  () => `${props.user.id}:${props.user.householdId}:${props.user.role}`,
)

let scopeVersion = 0
let requestVersion = 0

async function loadDetail(): Promise<void> {
  const scope = scopeVersion
  const request = ++requestVersion
  loading.value = detail.value === null
  refreshing.value = detail.value !== null
  detailError.value = null
  photoRefreshKey.value += 1

  try {
    const result = await props.services.deliveries.detail(props.deliveryId)
    if (scope !== scopeVersion || request !== requestVersion) return

    if (result.householdId !== props.user.householdId) {
      detail.value = null
      detailError.value = new ServiceError('forbidden', 'Access denied.', 403)
      return
    }

    detail.value = result
  } catch (cause) {
    if (scope !== scopeVersion || request !== requestVersion) return
    const status = deliveryRequestStatus(cause)
    if (status === 401 || status === 403 || status === 404) detail.value = null
    if (status === 401) emit('sessionExpired')
    detailError.value = cause
  } finally {
    if (scope === scopeVersion && request === requestVersion) {
      loading.value = false
      refreshing.value = false
    }
  }
}

function retryDetail(): void {
  void loadDetail()
}

watch(
  () =>
    [
      props.deliveryId,
      props.user.id,
      props.user.householdId,
      props.user.role,
      props.services,
    ] as const,
  () => {
    scopeVersion += 1
    requestVersion += 1
    detail.value = null
    detailError.value = null
    loading.value = true
    refreshing.value = false
    photoRefreshKey.value += 1
    void loadDetail()
  },
  { immediate: true },
)

watch(
  () => props.refreshKey,
  (value, previous) => {
    if (previous !== undefined && value !== previous) void loadDetail()
  },
)

onUnmounted(() => {
  scopeVersion += 1
  requestVersion += 1
})
</script>

<template>
  <section
    class="delivery-detail-screen"
    :aria-label="deliveryCopy.detailTitle"
  >
    <button
      class="button button--quiet delivery-detail__back"
      type="button"
      @click="emit('back')"
    >
      {{ deliveryCopy.backToList }}
    </button>

    <div v-if="detailError" class="banner banner--error" role="alert">
      <span>{{ detailErrorMessage }}</span>
      <button class="text-button" type="button" @click="retryDetail">
        {{ deliveryCopy.retryDetails }}
      </button>
    </div>
    <div v-else-if="refreshing" class="banner" role="status">
      {{ deliveryCopy.detailsRefreshing }}
    </div>

    <div
      v-if="loading"
      class="delivery-detail__skeleton"
      role="status"
      :aria-label="deliveryCopy.detailsLoading"
    >
      <span class="delivery-detail__skeleton-photo"></span>
      <span></span>
      <span></span>
    </div>

    <template v-else-if="detail">
      <header class="delivery-detail__header">
        <div>
          <h1 id="delivery-detail-title">{{ deliveryCopy.detailTitle }}</h1>
          <p class="delivery-detail__number">{{ detail.trackingNumber }}</p>
        </div>
        <div class="delivery-detail__scan">
          <span>{{ ui.scannedAt }}</span>
          <time :datetime="detail.scannedAt">{{
            formatDeliveryTimestamp(detail.scannedAt)
          }}</time>
        </div>
      </header>

      <DeliveryPhoto
        :key="accountKey"
        :service="services.deliveries"
        :delivery-id="detail.id"
        :tracking-number="detail.trackingNumber"
        :state="detail.photoState"
        :user-key="accountKey"
        :is-demo="services.mode === 'mock'"
        :refresh-key="photoKey"
        @session-expired="emit('sessionExpired')"
      />

      <section
        class="panel delivery-detail__panel"
        :aria-label="deliveryCopy.detailsSection"
      >
        <dl class="delivery-facts">
          <div>
            <dt>{{ ui.trackingNumber }}</dt>
            <dd>{{ detail.trackingNumber }}</dd>
          </div>
          <div v-if="detail.courier">
            <dt>{{ ui.courier }}</dt>
            <dd>{{ detail.courier.name }}</dd>
          </div>
        </dl>

        <section class="delivery-tracking" aria-labelledby="tracking-heading">
          <h2 id="tracking-heading">{{ deliveryCopy.trackingSection }}</h2>
          <p
            v-if="detail.trackingState === 'pending'"
            class="delivery-tracking__message"
            role="status"
          >
            {{ deliveryCopy.loadingTracking }}
          </p>
          <p
            v-else-if="detail.trackingState === 'unavailable'"
            class="delivery-tracking__message delivery-tracking__message--unavailable"
            role="status"
          >
            {{ ui.trackingUnavailable }}
          </p>
          <template v-else>
            <dl v-if="trackingFields.length" class="delivery-tracking__fields">
              <div v-for="field in trackingFields" :key="field.label">
                <dt>{{ field.label }}</dt>
                <dd>{{ field.value }}</dd>
              </div>
            </dl>
            <p v-else class="delivery-tracking__message">
              {{ deliveryCopy.noTrackingFields }}
            </p>

            <div v-if="trackingEvents.length" class="delivery-history">
              <h3>{{ deliveryCopy.trackingHistory }}</h3>
              <ol class="delivery-history__list">
                <li
                  v-for="(event, index) in trackingEvents"
                  :key="`${event.occurredAt ?? 'undated'}:${event.description}:${index}`"
                >
                  <strong>{{ event.description }}</strong>
                  <span
                    v-if="event.location"
                    class="delivery-history__location"
                  >
                    {{ event.location }}
                  </span>
                  <time v-if="event.occurredAt" :datetime="event.occurredAt">
                    {{ formatDeliveryTimestamp(event.occurredAt) }}
                  </time>
                </li>
              </ol>
            </div>
            <p v-else-if="hasTrackingData" class="delivery-history__empty">
              {{ deliveryCopy.noTrackingEvents }}
            </p>
          </template>
        </section>
      </section>
    </template>
  </section>
</template>

<style scoped>
.delivery-detail-screen {
  display: grid;
  gap: 24px;
  width: min(100%, 900px);
  margin: 0 auto;
  padding: 28px 0 64px;
}

.delivery-detail__back {
  justify-self: start;
  gap: 9px;
}

.delivery-detail__back span {
  font-size: 1.0625rem;
  line-height: 1;
}

.delivery-detail__header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 20px;
  margin-top: -6px;
}

.delivery-detail__header h1 {
  margin: 0 0 8px;
  font-size: 1.75rem;
  letter-spacing: -0.7px;
  line-height: 1.2;
}

.delivery-detail__number {
  color: #435d4c;
  font-size: 1.0625rem;
  font-weight: 700;
  overflow-wrap: anywhere;
}

.delivery-detail__scan {
  display: grid;
  flex-shrink: 0;
  gap: 4px;
  color: #667366;
  font-size: 0.8125rem;
  line-height: 1.5;
  text-align: right;
}

.delivery-detail__scan span {
  font-weight: 650;
}

.delivery-detail__panel {
  padding: 0 24px;
}

.delivery-facts,
.delivery-tracking__fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px 28px;
  margin: 0;
  padding: 22px 0;
}

.delivery-facts {
  border-bottom: 1px solid #e9ece3;
}

.delivery-facts > div,
.delivery-tracking__fields > div {
  min-width: 0;
}

.delivery-facts dt,
.delivery-tracking__fields dt {
  margin-bottom: 5px;
  color: #667366;
  font-size: 0.8125rem;
  font-weight: 600;
}

.delivery-facts dd,
.delivery-tracking__fields dd {
  margin: 0;
  color: #233d37;
  font-size: 0.875rem;
  line-height: 1.5;
  overflow-wrap: anywhere;
}

.delivery-tracking {
  padding: 22px 0 24px;
}

.delivery-tracking h2 {
  margin: 0;
  color: #233d37;
  font-size: 1.0625rem;
}

.delivery-tracking__message {
  margin-top: 14px;
  color: #667366;
  font-size: 0.8125rem;
  line-height: 1.6;
}

.delivery-tracking__message--unavailable {
  color: #875334;
}

.delivery-tracking__fields {
  padding-bottom: 0;
}

.delivery-history {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid #e9ece3;
}

.delivery-history h3 {
  margin: 0 0 14px;
  color: #435d4c;
  font-size: 0.875rem;
}

.delivery-history__list {
  display: grid;
  gap: 16px;
  margin: 0;
  padding-left: 19px;
}

.delivery-history__list li {
  padding-left: 3px;
  color: #233d37;
  line-height: 1.5;
}

.delivery-history__list strong {
  display: block;
  font-size: 0.8125rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.delivery-history__location,
.delivery-history__list time {
  display: block;
  margin-top: 3px;
  color: #667366;
  font-size: 0.8125rem;
}

.delivery-history__empty {
  margin-top: 14px;
  color: #667366;
  font-size: 0.8125rem;
}

.delivery-detail__skeleton {
  display: grid;
  gap: 14px;
}

.delivery-detail__skeleton span {
  width: min(360px, 65%);
  height: 13px;
  border-radius: 4px;
  background: #edf0e8;
}

.delivery-detail__skeleton .delivery-detail__skeleton-photo {
  width: 100%;
  height: auto;
  aspect-ratio: 16 / 9;
  border: 1px solid #dfe4d9;
  background: #f0f2e9;
}

@media (max-width: 620px) {
  .delivery-detail-screen {
    gap: 18px;
    padding: 22px 0 44px;
  }

  .delivery-detail__header {
    align-items: flex-start;
    flex-direction: column;
    gap: 8px;
  }

  .delivery-detail__header h1 {
    font-size: 1.5625rem;
  }

  .delivery-detail__scan {
    text-align: left;
  }

  .delivery-detail__panel {
    padding: 0 16px;
  }
}

@media (max-width: 440px) {
  .delivery-facts,
  .delivery-tracking__fields {
    grid-template-columns: minmax(0, 1fr);
    gap: 14px;
  }
}
</style>
