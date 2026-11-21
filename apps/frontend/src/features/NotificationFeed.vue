<script setup lang="ts">
import { onUnmounted, ref, watch } from 'vue'
import type { ApiServices, PackageNotification } from './api/contracts'
import { errorMessage, formatTime } from '../lib/strings'
const props = defineProps<{
  services: ApiServices
  revision: number
  liveStatus: string
}>()
const emit = defineEmits<{ open: [id: string] }>()
const items = ref<PackageNotification[]>([])
const next = ref<number | null>(null)
const loading = ref(false)
const error = ref('')
let controller: AbortController | null = null
let version = 0
let pages = 1
async function load(more = false) {
  if (more && (loading.value || next.value === null)) return
  controller?.abort()
  controller = new AbortController()
  const current = ++version
  loading.value = true
  error.value = ''
  try {
    const loaded = more ? [...items.value] : []
    let offset: number | null = more ? next.value : 0
    for (
      let index = 0;
      index < (more ? 1 : pages) && offset !== null;
      index++
    ) {
      const result = await props.services.notifications.list(
        offset,
        controller.signal,
      )
      loaded.push(...result.items)
      offset = result.nextOffset
    }
    if (current !== version) return
    items.value = [...new Map(loaded.map((item) => [item.id, item])).values()]
    next.value = offset
    if (more) pages++
  } catch (cause) {
    if (current === version) error.value = errorMessage(cause)
  } finally {
    if (current === version) loading.value = false
  }
}
watch(
  () => props.revision,
  () => void load(),
  { immediate: true },
)
onUnmounted(() => {
  version++
  controller?.abort()
})
</script>
<template>
  <section>
    <div class="api-heading">
      <div>
        <p class="eyebrow">Pembaruan dalam aplikasi</p>
        <h1>Notifikasi</h1>
      </div>
      <button class="button button--quiet" :disabled="loading" @click="load()">
        Muat ulang
      </button>
    </div>
    <p class="supporting">
      {{
        liveStatus === 'connected'
          ? 'Pembaruan langsung terhubung.'
          : liveStatus === 'demo'
            ? 'Notifikasi simulasi.'
            : 'Pembaruan langsung sementara tidak tersedia. Daftar tetap dapat dimuat ulang.'
      }}
      Notifikasi latar belakang belum tersedia.
    </p>
    <p v-if="error" class="banner banner--error" role="alert">
      {{ error }} <button class="text-button" @click="load()">Coba lagi</button>
    </p>
    <p v-if="loading" role="status">Memuat notifikasi…</p>
    <p v-if="!loading && !items.length && !error" class="banner">
      Belum ada notifikasi.
    </p>
    <ol class="api-feed">
      <li v-for="item in items" :key="item.id" class="panel">
        <h2>{{ item.title }}</h2>
        <p>{{ item.message }}</p>
        <time class="supporting">{{ formatTime(item.created_at) }}</time
        ><button class="text-button" @click="emit('open', item.shipment_id)">
          Lihat paket
        </button>
      </li>
    </ol>
    <button
      v-if="next !== null"
      class="button button--quiet"
      :disabled="loading"
      @click="load(true)"
    >
      Muat lebih banyak
    </button>
  </section>
</template>
