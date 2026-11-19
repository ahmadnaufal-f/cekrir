<script setup lang="ts">
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import type { ApiServices, Shipment, User } from './api/contracts'
import { validateShipment } from './api/contracts'
import { errorMessage, formatTime } from '../lib/strings'
import { ServiceError } from '../services/contracts'
const props = defineProps<{
  services: ApiServices
  user: User
  id: string | null
  revision: number
}>()
const emit = defineEmits<{ open: [id: string]; back: [] }>()
const items = ref<Shipment[]>([])
const selected = ref<Shipment | null>(null)
const loading = ref(false)
const moreLoading = ref(false)
const mutation = ref(false)
const error = ref('')
const formError = ref('')
const fieldErrors = ref<Record<string, string>>({})
const next = ref<number | null>(null)
const pages = ref(1)
const input = reactive({ courier: '', resi_number: '' })
const statusLabels = {
  pending: 'Menunggu',
  in_transit: 'Dalam perjalanan',
  delivered: 'Terkirim',
  exception: 'Kendala',
}
let controller: AbortController | null = null
let version = 0
let disposed = false
const title = computed(() => (props.id ? 'Detail paket' : 'Paket'))
const unique = (values: Shipment[]) => [
  ...new Map(values.map((item) => [item.id, item])).values(),
]
async function load(fresh = false) {
  controller?.abort()
  controller = new AbortController()
  const current = ++version
  loading.value = true
  error.value = ''
  moreLoading.value = false
  try {
    if (props.id) {
      const result = await props.services.shipments.find(
        props.id,
        controller.signal,
        fresh,
      )
      if (current === version) selected.value = result
    } else {
      const loaded: Shipment[] = []
      let offset: number | null = 0
      for (let page = 0; page < pages.value && offset !== null; page++) {
        const result = await props.services.shipments.list(
          offset,
          controller.signal,
        )
        loaded.push(...result.items)
        offset = result.nextOffset
      }
      if (current !== version) return
      items.value = unique(loaded)
      next.value = offset
    }
  } catch (cause) {
    if (
      current === version &&
      !(cause instanceof ServiceError && cause.code === 'cancelled')
    )
      error.value = errorMessage(cause)
  } finally {
    if (current === version) loading.value = false
  }
}
async function more() {
  if (next.value === null || loading.value || moreLoading.value) return
  const current = version
  moreLoading.value = true
  error.value = ''
  try {
    const result = await props.services.shipments.list(
      next.value,
      controller?.signal,
    )
    if (current !== version) return
    items.value = unique([...items.value, ...result.items])
    next.value = result.nextOffset
    pages.value++
  } catch (cause) {
    if (current === version) error.value = errorMessage(cause)
  } finally {
    if (current === version) moreLoading.value = false
  }
}
async function create() {
  fieldErrors.value = validateShipment(input)
  if (mutation.value || Object.keys(fieldErrors.value).length) return
  mutation.value = true
  formError.value = ''
  try {
    const item = await props.services.shipments.create({ ...input })
    if (disposed) return
    input.courier = ''
    input.resi_number = ''
    items.value = unique([item, ...items.value])
    emit('open', item.id)
  } catch (cause) {
    formError.value = errorMessage(cause)
    if (cause instanceof ServiceError) fieldErrors.value = cause.fieldErrors
  } finally {
    mutation.value = false
  }
}
async function refreshTracking() {
  const current = version
  if (!selected.value || mutation.value) return
  mutation.value = true
  error.value = ''
  try {
    const result = await props.services.shipments.refresh(selected.value.id)
    if (current === version) selected.value = result
  } catch (cause) {
    error.value = errorMessage(cause)
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
  disposed = true
  version++
  controller?.abort()
})
</script>
<template>
  <section>
    <div class="api-heading">
      <div>
        <p class="eyebrow">Catatan pengiriman bersama</p>
        <h1>{{ title }}</h1>
      </div>
      <button
        class="button button--quiet"
        :disabled="loading"
        @click="load(true)"
      >
        Muat ulang
      </button>
    </div>
    <p v-if="error" class="banner banner--error" role="alert">
      {{ error }}
      <button class="text-button" @click="load(true)">Coba lagi</button>
    </p>
    <p v-if="loading" role="status">Memuat paket…</p>
    <template v-if="id">
      <button class="text-button" @click="emit('back')">← Semua paket</button>
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
        <button
          v-if="user.role === 'admin'"
          class="button button--primary"
          :disabled="mutation"
          @click="refreshTracking"
        >
          {{ mutation ? 'Memeriksa…' : 'Periksa pelacakan' }}
        </button>
        <h3>Riwayat pelacakan</h3>
        <p v-if="!selected.history.length">Belum ada riwayat pelacakan.</p>
        <ol class="api-history">
          <li v-for="(event, index) in selected.history" :key="index">
            <time>{{ formatTime(event.occurred_at) }}</time>
            <p>{{ event.description }}</p>
            <p v-if="event.location" class="supporting">{{ event.location }}</p>
          </li>
        </ol>
      </article>
      <p v-else-if="!loading && !error" class="banner">
        Paket tidak ditemukan dalam daftar yang tersedia.
      </p>
      <p class="supporting">
        Catatan menampilkan data pelacakan terakhir yang tersimpan.
      </p>
    </template>
    <template v-else>
      <form class="panel api-form" @submit.prevent="create">
        <h2>Tambahkan paket</h2>
        <div class="api-columns">
          <label
            >Kode kurir<input
              v-model="input.courier"
              placeholder="jne"
              required
              maxlength="32"
              :aria-invalid="!!fieldErrors.courier"
              aria-describedby="courier-error"
            /><span id="courier-error" class="field-error">{{
              fieldErrors.courier
            }}</span></label
          ><label
            >Nomor resi<input
              v-model="input.resi_number"
              required
              maxlength="64"
              :aria-invalid="!!fieldErrors.resi_number"
              aria-describedby="resi-error"
            /><span id="resi-error" class="field-error">{{
              fieldErrors.resi_number
            }}</span></label
          >
        </div>
        <p v-if="formError" role="alert" class="banner banner--error">
          {{ formError }}
        </p>
        <button class="button button--primary" :disabled="mutation">
          {{ mutation ? 'Menyimpan…' : 'Tambahkan paket' }}
        </button>
      </form>
      <p v-if="!loading && !items.length && !error" class="banner">
        Belum ada paket. Tambahkan resi atau tunggu deteksi kamera.
      </p>
      <div class="api-grid">
        <article v-for="item in items" :key="item.id" class="panel">
          <p class="eyebrow">
            {{ item.courier.toUpperCase() }} · {{ statusLabels[item.status] }}
          </p>
          <h2>
            <a
              :href="`#/shipments/${encodeURIComponent(item.id)}`"
              @click.prevent="emit('open', item.id)"
              >{{ item.resi_number }}</a
            >
          </h2>
          <p>{{ item.summary }}</p>
          <p class="supporting">
            Ditambahkan {{ formatTime(item.created_at) }}
          </p>
          <p v-if="item.provider === 'demo'" class="mode-label">
            Pelacakan demo
          </p>
        </article>
      </div>
      <button
        v-if="next !== null"
        class="button button--quiet"
        :disabled="loading || moreLoading"
        @click="more"
      >
        {{ moreLoading ? 'Memuat…' : 'Muat lebih banyak' }}
      </button>
    </template>
  </section>
</template>
