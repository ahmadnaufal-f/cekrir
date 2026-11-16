<script setup lang="ts">
import { onUnmounted, shallowRef, watch } from 'vue'
import AppIcon from './AppIcon.vue'
import { deliveryCopy, deliveryRequestStatus } from '../lib/delivery-copy'
import { ui } from '../lib/strings'
import type { DeliveryService } from '../services/contracts'
import type { ResourceState } from '../types/app'

const props = defineProps<{
  service: DeliveryService
  deliveryId: string
  trackingNumber: string
  state: ResourceState
  userKey: string
  isDemo: boolean
  refreshKey?: string | number
}>()

const emit = defineEmits<{ sessionExpired: [] }>()

type PhotoViewState = ResourceState | 'error'
const viewState = shallowRef<PhotoViewState>('pending')
const imageUrl = shallowRef<string | null>(null)
let requestVersion = 0

function releaseImage(): void {
  if (imageUrl.value) URL.revokeObjectURL(imageUrl.value)
  imageUrl.value = null
}

function handleImageError(event: Event): void {
  const image = event.currentTarget as HTMLImageElement | null
  if (!image || image.src !== imageUrl.value) return
  releaseImage()
  viewState.value = 'error'
}

async function loadPhoto(version = ++requestVersion): Promise<void> {
  releaseImage()

  if (props.state !== 'ready') {
    viewState.value = props.state
    return
  }

  viewState.value = 'pending'
  try {
    const image = await props.service.photo(props.deliveryId)
    if (version !== requestVersion) return
    const nextUrl = URL.createObjectURL(image)
    imageUrl.value = nextUrl
    viewState.value = 'ready'
  } catch (cause) {
    if (version !== requestVersion) return
    if (deliveryRequestStatus(cause) === 401) emit('sessionExpired')
    viewState.value = 'error'
  }
}

watch(
  () =>
    [
      props.service,
      props.deliveryId,
      props.userKey,
      props.state,
      props.refreshKey,
    ] as const,
  (_value, _previous, onCleanup) => {
    const version = ++requestVersion
    onCleanup(() => {
      if (requestVersion === version) requestVersion += 1
    })
    void loadPhoto(version)
  },
  { immediate: true },
)

onUnmounted(() => {
  requestVersion += 1
  releaseImage()
})
</script>

<template>
  <figure class="delivery-photo">
    <div
      class="delivery-photo__frame"
      :aria-busy="viewState === 'pending'"
      :aria-label="ui.photo"
    >
      <img
        v-if="viewState === 'ready' && imageUrl"
        class="delivery-photo__image"
        :src="imageUrl"
        :alt="`${ui.photo}: ${trackingNumber}${isDemo ? ` · ${deliveryCopy.demoPhoto}` : ''}`"
        @error="handleImageError"
      />
      <div
        v-else-if="viewState === 'pending'"
        class="delivery-photo__placeholder"
        role="status"
      >
        <span class="delivery-photo__skeleton" aria-hidden="true"></span>
        <span>{{ deliveryCopy.loadingPhoto }}</span>
      </div>
      <div
        v-else-if="viewState === 'unavailable'"
        class="delivery-photo__placeholder"
        role="status"
      >
        <strong>{{ ui.photoUnavailable }}</strong>
      </div>
      <div v-else class="delivery-photo__placeholder" role="status">
        <div>
          <strong>{{ ui.photoUnavailable }}</strong>
          <p>{{ deliveryCopy.photoLoadFailed }}</p>
        </div>
        <button class="button button--quiet" type="button" @click="loadPhoto()">
          <AppIcon name="refresh" />
          {{ deliveryCopy.retryPhoto }}
        </button>
      </div>
    </div>
    <figcaption class="delivery-photo__caption">
      <AppIcon name="camera" />
      {{ ui.photo }}
      <span v-if="isDemo && viewState === 'ready'"
        >· {{ deliveryCopy.demoPhoto }}</span
      >
    </figcaption>
  </figure>
</template>

<style scoped>
.delivery-photo {
  margin: 0;
}

.delivery-photo__frame {
  display: grid;
  min-height: 190px;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  place-items: center;
  border: 1px solid #dfe4d9;
  border-radius: 9px;
  background: #f0f2e9;
  color: #536c53;
}

.delivery-photo__image {
  display: block;
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.delivery-photo__placeholder {
  display: grid;
  justify-items: center;
  gap: 14px;
  max-width: 420px;
  padding: 28px;
  text-align: center;
  line-height: 1.6;
}

.delivery-photo__placeholder strong {
  color: #435d4c;
}

.delivery-photo__placeholder p {
  margin-top: 4px;
  color: #667366;
  font-size: 0.8125rem;
}

.delivery-photo__skeleton {
  width: min(180px, 45vw);
  height: 7px;
  border-radius: 4px;
  background: #d8e0d1;
}

.delivery-photo__caption {
  margin-top: 9px;
  color: #65725f;
  font-size: 0.8125rem;
  font-weight: 600;
}

@media (max-width: 480px) {
  .delivery-photo__frame {
    min-height: 160px;
  }
}
</style>
