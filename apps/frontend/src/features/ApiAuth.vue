<script setup lang="ts">
import { computed, nextTick, reactive, ref, useTemplateRef } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import type { ApiServices } from './api/contracts'
import { validateRegistration } from './api/contracts'
import { ServiceError } from '../services/contracts'
const props = defineProps<{ services: ApiServices }>()
const mode = ref<'login' | 'register' | 'resend'>('login')
const modeCopy = {
  login: { title: 'Masuk', action: 'Masuk', description: '' },
  register: {
    title: 'Buat akun anggota',
    action: 'Daftar',
    description: 'Verifikasi email diperlukan sebelum Anda dapat masuk.',
  },
  resend: {
    title: 'Kirim ulang verifikasi',
    action: 'Kirim verifikasi',
    description: 'Gunakan email dan kata sandi akun yang belum diverifikasi.',
  },
}
const copy = computed(() => modeCopy[mode.value])
const heading = useTemplateRef('auth-heading')
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
  void nextTick(() => heading.value?.focus())
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
  <section class="auth-layout" aria-labelledby="auth-intro-title">
    <div class="auth-intro">
      <h1 id="auth-intro-title">Pantau perjalanan paket.</h1>
      <p class="auth-intro__description">
        Lihat catatan paket dan pembaruan pelacakan dalam satu tempat.
      </p>
    </div>
    <div class="auth-panel">
      <div class="auth-panel__content">
        <PageHeader class="auth-panel__heading">
          <template #title>
            <h2
              id="auth-heading"
              ref="auth-heading"
              class="page-title"
              tabindex="-1"
            >
              {{ copy.title }}
            </h2>
          </template>
          <p v-if="copy.description">
            {{ copy.description }}
          </p>
        </PageHeader>

        <div v-if="services.mode === 'mock'" class="auth-demo">
          <p>
            <strong v-if="mode === 'login'">Akun demo · </strong>Data simulasi,
            tanpa email, perangkat, atau notifikasi nyata.
          </p>
          <template v-if="mode === 'login'">
            <p>admin@demo.test atau member@demo.test</p>
            <p>Kata sandi <strong>demo12345678</strong></p>
          </template>
        </div>
        <p v-if="message && mode === 'login'" class="banner" role="status">
          {{ message }}
        </p>

        <form
          class="auth-form"
          aria-labelledby="auth-heading"
          :aria-busy="busy"
          @submit.prevent="submit"
        >
          <div v-if="mode === 'register'" class="auth-field">
            <label for="auth-name">Nama lengkap</label>
            <input
              id="auth-name"
              v-model="form.full_name"
              name="full_name"
              required
              maxlength="200"
              autocomplete="name"
              :aria-invalid="!!errors.full_name"
              :aria-describedby="
                errors.full_name ? 'auth-name-error' : undefined
              "
            />
            <p v-if="errors.full_name" id="auth-name-error" class="field-error">
              {{ errors.full_name }}
            </p>
          </div>

          <div class="auth-field">
            <label for="auth-email">Email</label>
            <input
              id="auth-email"
              v-model="form.email"
              name="email"
              type="email"
              required
              maxlength="320"
              autocomplete="username"
              :aria-invalid="!!errors.email"
              :aria-describedby="errors.email ? 'auth-email-error' : undefined"
            />
            <p v-if="errors.email" id="auth-email-error" class="field-error">
              {{ errors.email }}
            </p>
          </div>

          <div class="auth-field">
            <label for="auth-password">Kata sandi</label>
            <input
              id="auth-password"
              v-model="form.password"
              name="password"
              type="password"
              required
              :maxlength="mode === 'register' ? 72 : 256"
              :autocomplete="
                mode === 'register' ? 'new-password' : 'current-password'
              "
              :aria-invalid="!!errors.password"
              :aria-describedby="
                errors.password
                  ? 'auth-password-error'
                  : mode === 'register'
                    ? 'auth-password-hint'
                    : undefined
              "
            />
            <p
              v-if="errors.password"
              id="auth-password-error"
              class="field-error"
            >
              {{ errors.password }}
            </p>
            <p
              v-else-if="mode === 'register'"
              id="auth-password-hint"
              class="field-help"
            >
              Minimal 12 karakter, maksimal 72 byte UTF-8.
            </p>
          </div>

          <p v-if="error" role="alert" class="banner banner--error">
            {{ error }}
          </p>
          <button class="button button--primary" :disabled="busy">
            {{ busy ? 'Memproses…' : copy.action }}
          </button>
        </form>

        <div class="auth-actions">
          <button
            v-if="mode !== 'login'"
            class="text-button"
            @click="switchMode('login')"
          >
            Kembali ke masuk
          </button>
          <button
            v-if="mode !== 'register'"
            class="text-button"
            @click="switchMode('register')"
          >
            Buat akun
          </button>
          <button
            v-if="mode !== 'resend'"
            class="text-button"
            @click="switchMode('resend')"
          >
            Kirim ulang verifikasi
          </button>
        </div>
      </div>
    </div>
    <p class="auth-note">
      Semua pengguna berbagi catatan paket. Catatan belum dipisah per lokasi.
    </p>
  </section>
</template>

<style scoped>
.auth-layout {
  --auth-border: #dce2d8;
  --auth-surface: #fffefa;
  --auth-pine: #153c36;
  --auth-photo: url('../assets/auth-doorstep.webp');
  display: grid;
  grid-template-columns: minmax(0, 1fr);
}

.auth-intro {
  position: relative;
  isolation: isolate;
  display: grid;
  align-content: center;
  min-height: clamp(6rem, 27vw, 8.5rem);
  padding: 1rem;
  padding-inline-start: var(--card-text-inset);
  padding-inline-end: 34%;
  overflow: hidden;
  border-radius: 20px 20px 0 0;
  background: var(--auth-pine);
  color: var(--auth-surface);
}

.auth-intro::before {
  position: absolute;
  z-index: -1;
  inset: 0 0 0 53%;
  content: '';
  background:
    linear-gradient(90deg, var(--auth-pine), #153c36d4 18%, transparent 65%),
    var(--auth-photo) center 88% / cover;
}

.auth-intro h1 {
  margin: 0;
  font-size: clamp(1.375rem, 6vw, 1.875rem);
  line-height: 1.12;
  letter-spacing: -0.035em;
  overflow-wrap: anywhere;
}

.auth-intro__description {
  display: none;
}

.auth-note {
  margin-top: 14px;
  padding-inline: var(--card-text-inset);
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.6;
}

.auth-panel {
  padding-block: clamp(1rem, 5vw, 1.75rem);
  padding-inline: var(--card-inset);
  border: 1px solid var(--auth-border);
  border-top: 0;
  border-radius: 0 0 20px 20px;
  background: var(--auth-surface);
  box-shadow: 0 12px 28px #233d370e;
}

.auth-panel__content {
  display: grid;
  gap: 16px;
  min-width: 0;
}

.auth-panel__heading {
  --page-header-offset: 0;
  --page-header-gap: 0;
  --page-header-row-height: 0;
  --page-header-inset: 0px;
}

.auth-demo {
  padding: 12px 14px;
  border: 1px solid #e0e6d9;
  border-radius: 10px;
  background: #f1f4ec;
  color: #455a4c;
  font-size: 0.8125rem;
}

.auth-demo p + p {
  margin-top: 3px;
}

.auth-panel .banner {
  margin: 0;
  padding: 12px 14px;
  border-radius: 10px;
}

.auth-form {
  gap: 16px;
}

.auth-field {
  display: grid;
  gap: 6px;
  min-width: 0;
}

.auth-field label,
.auth-field input,
.auth-field .field-error,
.auth-field .field-help {
  margin: 0;
}

.auth-field input,
.auth-form .button {
  min-height: 48px;
  border-radius: 8px;
}

.auth-field input {
  min-width: 0;
  background: #fff;
}

.auth-field input[aria-invalid='true'] {
  border-color: #ac694f;
}

.auth-form .button {
  margin-top: 4px;
  font-size: 0.9375rem;
  font-weight: 650;
}

.auth-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 0 12px;
  border-top: 1px solid #e0e4d9;
  padding-top: 6px;
}

.auth-actions .text-button {
  justify-content: start;
  padding-inline: 0;
  color: var(--accent);
  font-size: 0.875rem;
  font-weight: 650;
  text-align: start;
}

@media (width > 760px) {
  .auth-layout {
    grid-template-columns: minmax(0, 0.95fr) minmax(0, 1.05fr);
    grid-template-rows: auto 1fr;
    grid-template-areas:
      'intro panel'
      'note panel';
    min-height: calc(36rem + 2px);
    overflow: hidden;
    border: 1px solid var(--auth-border);
    border-radius: 24px;
    background: var(--auth-surface);
    box-shadow: 0 16px 44px #233d3712;
  }

  .auth-layout::before {
    grid-area: 1 / 1 / 3 / 2;
    content: '';
    background:
      linear-gradient(180deg, #142f27f2, #142f27b3 37%, transparent 66%),
      var(--auth-photo) center bottom / cover,
      var(--auth-pine);
  }

  .auth-intro {
    grid-area: intro;
    display: block;
    min-height: 0;
    padding: var(--auth-intro-padding) var(--auth-intro-padding) 0;
    border-radius: 0;
    background: none;
  }

  .auth-intro::before {
    content: none;
  }

  .auth-intro h1 {
    max-width: 15ch;
    margin-bottom: 14px;
    font-size: clamp(2rem, 4vw, 3.125rem);
    line-height: 1.08;
    letter-spacing: -0.045em;
    text-wrap: balance;
  }

  .auth-intro__description {
    display: block;
    max-width: 34ch;
    color: #e2eadf;
    line-height: 1.6;
  }

  .auth-note {
    position: relative;
    grid-area: note;
    align-self: start;
    max-width: 42ch;
    margin: 20px var(--auth-intro-padding) var(--auth-intro-padding);
    padding: 0;
    color: #e2eadf;
    font-size: 0.875rem;
  }

  .auth-note::before {
    position: absolute;
    inset-block: 0;
    inset-inline-start: -12px;
    border-inline-start: 2px solid #b5c8a2;
    content: '';
  }

  .auth-panel {
    grid-area: panel;
    display: grid;
    align-items: center;
    padding: clamp(1.75rem, 5vw, 3.75rem);
    border: 0;
    border-radius: 0;
    box-shadow: none;
  }

  .auth-panel__content {
    gap: 20px;
    width: 100%;
    max-width: 25rem;
    margin-inline: auto;
  }
}
</style>
