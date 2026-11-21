<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import type { ApiServices, User } from './api/contracts'
import { errorMessage } from '../lib/strings'
import { ServiceError } from '../services/contracts'
const props = defineProps<{ services: ApiServices }>()
const items = ref<User[]>([])
const loading = ref(false)
const saving = ref(false)
const error = ref('')
const pending = ref<User | null>(null)
let disposed = false
async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await props.services.users.list()
    if (!disposed) items.value = result
  } catch (cause) {
    if (!disposed) error.value = errorMessage(cause)
  } finally {
    if (!disposed) loading.value = false
  }
}
async function confirm() {
  if (!pending.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const user = await props.services.users.role(
      pending.value.id,
      pending.value.role === 'admin' ? 'member' : 'admin',
    )
    if (!disposed) {
      items.value = items.value.map((item) =>
        item.id === user.id ? user : item,
      )
      pending.value = null
    }
  } catch (cause) {
    if (!disposed)
      error.value =
        cause instanceof ServiceError && cause.status === 409
          ? 'Peran tidak dapat diubah. Alihkan lokasi penerimaan yang dimiliki pengguna ini terlebih dahulu.'
          : errorMessage(cause)
  } finally {
    if (!disposed) saving.value = false
  }
}
onMounted(load)
onUnmounted(() => {
  disposed = true
})
</script>
<template>
  <section>
    <div class="api-heading">
      <div>
        <p class="eyebrow">Administrasi akun</p>
        <h1>Pengguna dan peran</h1>
      </div>
      <button
        class="button button--quiet"
        :disabled="loading || saving"
        @click="load"
      >
        Muat ulang
      </button>
    </div>
    <p class="supporting">
      Daftar pengguna API bersama. Pembuatan anggota lokasi penerimaan belum
      tersedia.
    </p>
    <p v-if="error" role="alert" class="banner banner--error">{{ error }}</p>
    <p v-if="loading" role="status">Memuat pengguna…</p>
    <p v-if="!loading && !items.length && !error">Belum ada pengguna.</p>
    <div
      v-if="pending"
      class="panel"
      role="region"
      aria-label="Konfirmasi perubahan peran"
    >
      <h2>Ubah peran {{ pending.full_name }}?</h2>
      <p>
        Peran baru: {{ pending.role === 'admin' ? 'Anggota' : 'Admin' }}.
        Perubahan berlaku segera, termasuk untuk akun Anda sendiri.
      </p>
      <div class="api-actions">
        <button
          class="button button--primary"
          :disabled="saving"
          @click="confirm"
        >
          {{ saving ? 'Menyimpan…' : 'Konfirmasi perubahan' }}</button
        ><button
          class="button button--quiet"
          :disabled="saving"
          @click="pending = null"
        >
          Batal
        </button>
      </div>
    </div>
    <div class="api-grid">
      <article v-for="item in items" :key="item.id" class="panel">
        <h2>{{ item.full_name }}</h2>
        <p>{{ item.email }}</p>
        <p>
          {{ item.role === 'admin' ? 'Admin' : 'Anggota' }} ·
          {{ item.is_active ? 'Aktif' : 'Tidak aktif' }}
        </p>
        <button class="text-button" :disabled="saving" @click="pending = item">
          Ubah peran
        </button>
      </article>
    </div>
  </section>
</template>
