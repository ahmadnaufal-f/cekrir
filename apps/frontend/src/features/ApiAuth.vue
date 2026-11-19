<script setup lang="ts">
import { reactive, ref } from 'vue'
import type { ApiServices } from './api/contracts'
import { validateRegistration } from './api/contracts'
import { ServiceError } from '../services/contracts'
const props = defineProps<{ services: ApiServices }>()
const mode = ref<'login' | 'register' | 'resend'>('login')
const form = reactive({ email: '', password: '', full_name: '' })
const busy = ref(false)
const message = ref('')
const error = ref('')
const errors = ref<Record<string, string>>({})
let attempt = 0
function switchMode(next: typeof mode.value) {
  attempt++
  mode.value = next
  form.password = ''
  errors.value = {}
  error.value = ''
  busy.value = false
}
async function submit() {
  if (busy.value) return
  errors.value = mode.value === 'register' ? validateRegistration(form) : {}
  if (Object.keys(errors.value).length) return
  busy.value = true
  error.value = ''
  message.value = ''
  const version = ++attempt
  try {
    if (mode.value === 'login')
      await props.services.auth.login({
        email: form.email,
        password: form.password,
      })
    else {
      if (mode.value === 'register')
        await props.services.auth.register({ ...form })
      else
        await props.services.auth.resend({
          email: form.email,
          password: form.password,
        })
      if (version !== attempt) return
      message.value =
        props.services.mode === 'mock'
          ? 'Simulasi: akun menunggu verifikasi. Gunakan akun demo untuk masuk; tidak ada email dikirim.'
          : 'Periksa email Anda dan konfirmasikan melalui tombol pada tautan verifikasi. Setelah itu, masuk di sini.'
      switchMode('login')
    }
  } catch (cause) {
    if (version !== attempt) return
    errors.value = cause instanceof ServiceError ? cause.fieldErrors : {}
    error.value =
      cause instanceof ServiceError && cause.status === 401
        ? 'Email atau kata sandi salah, atau email belum diverifikasi. Anda dapat mengirim ulang verifikasi.'
        : cause instanceof ServiceError && cause.status === 409
          ? 'Email sudah terdaftar. Coba masuk atau kirim ulang verifikasi.'
          : cause instanceof Error
            ? cause.message
            : 'Permintaan gagal.'
  } finally {
    if (version === attempt) {
      busy.value = false
      form.password = ''
    }
  }
}
</script>
<template>
  <section class="auth-layout">
    <div>
      <p class="eyebrow">Pantau perjalanan paket</p>
      <h1>Selamat datang.</h1>
      <p class="supporting">
        Masuk untuk melihat catatan paket dan pembaruan pelacakan.
      </p>
      <p class="banner">
        Catatan paket saat ini digunakan bersama oleh pengguna API. Pemisahan
        lokasi penerimaan belum tersedia.
      </p>
    </div>
    <div class="panel">
      <h2>
        {{
          mode === 'register'
            ? 'Buat akun anggota'
            : mode === 'resend'
              ? 'Kirim ulang verifikasi'
              : 'Masuk'
        }}
      </h2>
      <p v-if="services.mode === 'mock'" class="supporting">
        Demo: admin@demo.test atau member@demo.test · kata sandi demo12345678.
      </p>
      <p v-if="message" class="banner" role="status">{{ message }}</p>
      <form class="api-form" @submit.prevent="submit">
        <label v-if="mode === 'register'"
          >Nama lengkap<input
            v-model="form.full_name"
            required
            maxlength="200"
            autocomplete="name"
            :aria-invalid="!!errors.full_name"
            aria-describedby="name-error"
          /><span id="name-error" class="field-error">{{
            errors.full_name
          }}</span></label
        >
        <label
          >Email<input
            v-model="form.email"
            type="email"
            required
            maxlength="320"
            autocomplete="username"
            :aria-invalid="!!errors.email"
            aria-describedby="email-error"
          /><span id="email-error" class="field-error">{{
            errors.email
          }}</span></label
        >
        <label
          >Kata sandi<input
            v-model="form.password"
            type="password"
            required
            :maxlength="mode === 'register' ? 72 : 256"
            :autocomplete="
              mode === 'register' ? 'new-password' : 'current-password'
            "
            :aria-invalid="!!errors.password"
            aria-describedby="password-error"
          /><span id="password-error" class="field-error">{{
            errors.password
          }}</span></label
        >
        <p v-if="mode === 'register'" class="supporting">
          Minimal 12 karakter, maksimal 72 byte UTF-8. Akun perlu verifikasi
          email sebelum masuk.
        </p>
        <p v-if="error" role="alert" class="banner banner--error">
          {{ error }}
        </p>
        <button class="button button--primary" :disabled="busy">
          {{
            busy
              ? 'Memproses…'
              : mode === 'register'
                ? 'Daftar'
                : mode === 'resend'
                  ? 'Kirim verifikasi'
                  : 'Masuk'
          }}
        </button>
      </form>
      <div class="api-actions">
        <button
          v-if="mode !== 'login'"
          class="text-button"
          @click="switchMode('login')"
        >
          Kembali ke masuk</button
        ><button
          v-if="mode !== 'register'"
          class="text-button"
          @click="switchMode('register')"
        >
          Buat akun</button
        ><button
          v-if="mode !== 'resend'"
          class="text-button"
          @click="switchMode('resend')"
        >
          Kirim ulang verifikasi
        </button>
      </div>
    </div>
  </section>
</template>
