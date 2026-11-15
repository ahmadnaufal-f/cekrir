<script setup lang="ts">
import { onUnmounted, reactive, shallowRef, watch } from 'vue'
import type { AppServices } from '../services/contracts'
import { ServiceError } from '../services/contracts'
import type { AppUser } from '../types/app'
import { ui, errorMessage } from '../lib/strings'
import { authCopy as copy } from '../lib/auth-copy'

const props = defineProps<{ services: AppServices; signup: boolean }>()
const development = import.meta.env.DEV
const emit = defineEmits<{ authenticated: [user: AppUser]; switch: [] }>()
const form = reactive({
  loginId: '',
  password: '',
  displayName: '',
  email: '',
  householdName: '',
})
const errors = shallowRef<Record<string, string>>({})
const error = shallowRef('')
const pending = shallowRef(false)
let generation = 0
onUnmounted(() => {
  generation++
  form.password = ''
})
watch(
  () => props.signup,
  () => {
    generation++
    form.password = ''
    errors.value = {}
    error.value = ''
    pending.value = false
  },
)
async function submit() {
  if (pending.value) return
  const fields = props.signup
    ? (['displayName', 'email', 'householdName', 'password'] as const)
    : (['loginId', 'password'] as const)
  const next: Record<string, string> = {}
  for (const field of fields)
    if (!form[field].trim()) next[field] = copy.required
  if (props.signup && form.password.length < 8) next.password = copy.minPassword
  if (props.signup && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
    next.email = copy.emailInvalid
  errors.value = next
  if (Object.keys(next).length) return
  const current = ++generation
  pending.value = true
  error.value = ''
  try {
    const user = props.signup
      ? await props.services.auth.signup({
          ...form,
          email: form.email.trim(),
          displayName: form.displayName.trim(),
          householdName: form.householdName.trim(),
        })
      : await props.services.auth.login({
          loginId: form.loginId.trim(),
          password: form.password,
        })
    if (current === generation) {
      form.password = ''
      emit('authenticated', user)
    }
  } catch (cause) {
    if (current === generation) {
      error.value = errorMessage(cause)
      if (cause instanceof ServiceError) errors.value = cause.fieldErrors
    }
  } finally {
    if (current === generation) pending.value = false
  }
}
</script>

<template>
  <section class="auth-layout">
    <div class="auth-intro">
      <h1>{{ signup ? copy.signupTitle : copy.welcome }}</h1>
      <p>{{ signup ? copy.signupDescription : copy.description }}</p>
      <svg
        class="home-art"
        viewBox="0 0 280 180"
        fill="none"
        aria-hidden="true"
      >
        <path
          d="M30 88 140 20l110 68M57 72v90h166V72"
          stroke="currentColor"
          stroke-width="3"
          stroke-linejoin="round"
        />
        <path d="M111 162v-62h58v62" stroke="currentColor" stroke-width="3" />
        <path
          d="m170 137 30-17 30 17v33h-60z"
          fill="#d8bf90"
          stroke="#8d754e"
          stroke-width="2"
        />
        <path
          d="m170 137 30 16 30-16m-30 16v17m-15-41 30 16"
          stroke="#8d754e"
          stroke-width="2"
        />
      </svg>
    </div>
    <div class="panel auth-panel">
      <h2>{{ signup ? ui.signup : ui.login }}</h2>
      <p class="supporting">{{ signup ? copy.prototype : copy.loginHint }}</p>
      <p v-if="development && services.mode === 'mock'" class="banner">
        {{ copy.mockAccounts }}
      </p>
      <form novalidate :aria-busy="pending" @submit.prevent="submit">
        <template v-if="signup">
          <label for="displayName">{{ copy.name }}</label
          ><input
            id="displayName"
            v-model="form.displayName"
            name="name"
            autocomplete="name"
            required
            :aria-invalid="!!errors.displayName"
            aria-describedby="displayName-error"
            maxlength="100"
          /><span
            v-if="errors.displayName"
            id="displayName-error"
            class="field-error"
            >{{ errors.displayName }}</span
          >
          <label for="email">{{ copy.email }}</label
          ><input
            id="email"
            v-model="form.email"
            type="email"
            autocomplete="email"
            required
            :aria-invalid="!!errors.email"
            aria-describedby="email-error"
            maxlength="200"
          /><span v-if="errors.email" id="email-error" class="field-error">{{
            errors.email
          }}</span>
          <label for="householdName">{{ copy.household }}</label
          ><input
            id="householdName"
            v-model="form.householdName"
            autocomplete="organization"
            required
            :aria-invalid="!!errors.householdName"
            aria-describedby="household-error"
            maxlength="100"
          /><span
            v-if="errors.householdName"
            id="household-error"
            class="field-error"
            >{{ errors.householdName }}</span
          >
        </template>
        <template v-else
          ><label for="loginId">{{ copy.loginId }}</label
          ><input
            id="loginId"
            v-model="form.loginId"
            autocomplete="username"
            required
            :aria-invalid="!!errors.loginId"
            aria-describedby="login-error"
            maxlength="200"
          /><span v-if="errors.loginId" id="login-error" class="field-error">{{
            errors.loginId
          }}</span></template
        >
        <label for="password">{{ copy.password }}</label
        ><input
          id="password"
          v-model="form.password"
          type="password"
          :autocomplete="signup ? 'new-password' : 'current-password'"
          required
          :aria-invalid="!!errors.password"
          aria-describedby="password-error"
          maxlength="200"
        /><span
          v-if="errors.password"
          id="password-error"
          class="field-error"
          >{{ errors.password }}</span
        >
        <p v-if="error" class="banner banner--error" role="alert">
          {{ error }}
        </p>
        <button class="button button--primary" :disabled="pending">
          {{ pending ? ui.loading : signup ? ui.signup : ui.login }}
        </button>
      </form>
      <p class="auth-switch">
        {{ signup ? copy.existing : copy.adminHint }}
        <button class="text-button" @click="emit('switch')">
          {{ signup ? ui.login : ui.signup }}
        </button>
      </p>
    </div>
  </section>
</template>

<style scoped>
.auth-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 64px;
  padding: 56px 0;
  align-items: center;
}
.auth-intro p {
  max-width: 42ch;
  line-height: 1.75;
  color: #53675a;
}
.home-art {
  width: 240px;
  max-width: 100%;
  margin-top: 32px;
  color: #71866c;
}
.auth-panel {
  max-width: 480px;
  width: 100%;
}
.auth-panel h2 {
  margin-bottom: 12px;
}
.auth-panel .supporting {
  margin-bottom: 24px;
}
.auth-switch {
  margin-top: 24px;
  font-size: 0.875rem;
  line-height: 1.7;
}
@media (max-width: 680px) {
  .auth-layout {
    display: block;
    padding: 28px 0;
  }
  .auth-intro {
    margin-bottom: 28px;
  }
  .home-art {
    display: none;
  }
  .auth-panel {
    max-width: none;
  }
}
</style>
