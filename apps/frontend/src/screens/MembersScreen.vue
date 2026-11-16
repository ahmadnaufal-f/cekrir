<script setup lang="ts">
import AppIcon from '../components/AppIcon.vue'
import {
  computed,
  onUnmounted,
  reactive,
  shallowRef,
  useTemplateRef,
  watch,
} from 'vue'
import { adminCopy } from '../lib/admin-copy'
import { memberGuideCopy } from '../lib/member-guide-copy'
import { ServiceError } from '../services/contracts'
import type { AppServices } from '../services/contracts'
import type { AppUser, MemberInput } from '../types/app'

const props = defineProps<{ services: AppServices; user: AppUser }>()
const emit = defineEmits<{ sessionExpired: [] }>()

type MemberListState = 'loading' | 'ready' | 'error'
interface MemberCompletion {
  displayName: string
  loginId: string
  initialPassword: string
}

const copy = adminCopy.members
const members = shallowRef<readonly AppUser[]>([])
const listState = shallowRef<MemberListState>('loading')
const saving = shallowRef(false)
const errorMessage = shallowRef('')
const fieldErrors = shallowRef<Record<string, string>>({})
const completion = shallowRef<MemberCompletion | null>(null)
const completionPasswordVisible = shallowRef(false)
const completionNotice = shallowRef('')
const form = reactive({ displayName: '', loginId: '', initialPassword: '' })
const displayNameInput = useTemplateRef<HTMLInputElement>('displayNameInput')
const isAdmin = computed(() => props.user.role === 'admin')

let requestGeneration = 0
let disposed = false

function isCurrent(generation: number): boolean {
  return !disposed && generation === requestGeneration && isAdmin.value
}

function isUnauthorized(cause: unknown): boolean {
  return cause instanceof ServiceError
    ? cause.status === 401 || cause.code === 'UNAUTHENTICATED'
    : typeof cause === 'object' &&
        cause !== null &&
        'status' in cause &&
        cause.status === 401
}

function reportUnauthorized(cause: unknown, generation: number): boolean {
  if (!isCurrent(generation) || !isUnauthorized(cause)) return false
  emit('sessionExpired')
  return true
}

function clearSensitiveState(): void {
  form.initialPassword = ''
  completion.value = null
  completionPasswordVisible.value = false
  completionNotice.value = ''
}

function resetScreenState(): void {
  members.value = []
  listState.value = 'loading'
  saving.value = false
  errorMessage.value = ''
  fieldErrors.value = {}
  form.displayName = ''
  form.loginId = ''
  clearSensitiveState()
}

async function loadMembers(generation: number): Promise<void> {
  listState.value = 'loading'
  errorMessage.value = ''
  try {
    const result = await props.services.members.list()
    if (!isCurrent(generation)) return
    members.value = result
    listState.value = 'ready'
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (!reportUnauthorized(cause, generation)) {
      listState.value = 'error'
      errorMessage.value = copy.loadFailed
    }
  }
}

async function createMember(): Promise<void> {
  if (!isAdmin.value || saving.value) return
  const displayName = form.displayName.trim()
  const loginId = form.loginId.trim()
  const initialPassword = form.initialPassword
  if (!displayName || !loginId || !initialPassword) return

  const generation = requestGeneration
  const input: MemberInput = { displayName, loginId, initialPassword }
  saving.value = true
  errorMessage.value = ''
  fieldErrors.value = {}
  completion.value = null
  try {
    const created = await props.services.members.create(input)
    if (!isCurrent(generation)) return

    // Keep the service result in this screen only. Account creation does not
    // sign the admin in as the newly created member.
    if (!members.value.some((member) => member.id === created.id)) {
      members.value = [...members.value, created]
    }
    form.displayName = ''
    form.loginId = ''
    form.initialPassword = ''
    completion.value = {
      displayName: created.displayName,
      loginId: created.loginId,
      initialPassword,
    }
    completionPasswordVisible.value = false
    completionNotice.value = ''
  } catch (cause) {
    if (!isCurrent(generation)) return
    if (cause instanceof ServiceError && cause.status === 422)
      fieldErrors.value = cause.fieldErrors
    if (!reportUnauthorized(cause, generation))
      errorMessage.value = copy.createFailed
  } finally {
    if (isCurrent(generation)) saving.value = false
  }
}

function focusDisplayNameInput(): void {
  displayNameInput.value?.focus()
}

function dismissCompletion(): void {
  completion.value = null
  completionPasswordVisible.value = false
  completionNotice.value = ''
}

async function copyInitialPassword(): Promise<void> {
  const value = completion.value?.initialPassword
  if (!value) return
  try {
    if (!navigator.clipboard?.writeText)
      throw new Error('Clipboard unavailable')
    await navigator.clipboard.writeText(value)
    completionNotice.value = copy.passwordCopied
  } catch {
    completionNotice.value = copy.passwordCopyFailed
  }
}

watch(
  [() => props.user.id, () => props.user.householdId, () => props.user.role],
  () => {
    requestGeneration += 1
    resetScreenState()
    if (isAdmin.value) void loadMembers(requestGeneration)
  },
  { immediate: true, flush: 'sync' },
)

onUnmounted(() => {
  disposed = true
  requestGeneration += 1
  clearSensitiveState()
})
</script>

<template>
  <section class="admin-screen members-screen" aria-labelledby="members-title">
    <header class="admin-screen__header">
      <h1 id="members-title">{{ copy.title }}</h1>
      <p class="admin-screen__intro">{{ copy.intro }}</p>
    </header>

    <p
      v-if="!isAdmin"
      class="admin-screen__banner admin-screen__banner--error"
      role="alert"
    >
      {{ adminCopy.common.adminOnly }}
    </p>

    <template v-else>
      <p
        v-if="errorMessage"
        class="admin-screen__banner admin-screen__banner--error"
        role="alert"
      >
        {{ errorMessage }}
      </p>

      <section
        v-if="completion"
        class="admin-panel completion-panel"
        aria-labelledby="completion-title"
      >
        <h2 id="completion-title">{{ copy.completionTitle }}</h2>
        <p class="admin-panel__copy">{{ copy.completionIntro }}</p>
        <dl class="completion-details">
          <div>
            <dt>{{ copy.displayName }}</dt>
            <dd>{{ completion.displayName }}</dd>
          </div>
          <div>
            <dt>{{ copy.loginId }}</dt>
            <dd>{{ completion.loginId }}</dd>
          </div>
        </dl>
        <label class="admin-field completion-password">
          <span>{{ copy.initialPassword }}</span>
          <input
            :type="completionPasswordVisible ? 'text' : 'password'"
            :value="completion.initialPassword"
            readonly
            autocomplete="off"
          />
        </label>
        <div class="completion-panel__actions">
          <button
            class="admin-button admin-button--quiet"
            type="button"
            @click="completionPasswordVisible = !completionPasswordVisible"
          >
            <AppIcon :name="completionPasswordVisible ? 'eyeOff' : 'eye'" />
            {{
              completionPasswordVisible
                ? copy.completionHidePassword
                : copy.completionShowPassword
            }}
          </button>
          <button
            class="admin-button admin-button--quiet"
            type="button"
            @click="copyInitialPassword"
          >
            <AppIcon name="copy" />
            {{ copy.completionCopyPassword }}
          </button>
        </div>
        <p
          v-if="completionNotice"
          class="completion-panel__notice"
          role="status"
        >
          {{ completionNotice }}
        </p>
        <button
          class="admin-button admin-button--primary completion-panel__dismiss"
          type="button"
          @click="dismissCompletion"
        >
          <AppIcon name="check" />
          {{ copy.completionDismiss }}
        </button>
      </section>

      <div v-else class="members-layout">
        <section
          class="admin-panel member-list-panel"
          aria-labelledby="member-list-title"
        >
          <div class="admin-panel__heading">
            <h2 id="member-list-title">{{ copy.title }}</h2>
            <span v-if="listState === 'ready'" class="admin-pill">
              {{ members.length }} {{ copy.memberCount }}
            </span>
          </div>
          <p
            v-if="listState === 'loading'"
            class="admin-screen__status"
            role="status"
          >
            {{ adminCopy.common.loading }}
          </p>
          <div v-else-if="listState === 'error'" class="admin-empty">
            <p>{{ copy.loadFailed }}</p>
            <button
              class="admin-button admin-button--quiet"
              type="button"
              @click="loadMembers(requestGeneration)"
            >
              <AppIcon name="refresh" />
              {{ adminCopy.common.retry }}
            </button>
          </div>
          <div
            v-else-if="listState === 'ready' && members.length === 0"
            class="member-empty-guide"
            role="group"
            aria-labelledby="member-empty-guide-title"
          >
            <div class="member-empty-guide__heading">
              <span class="member-empty-guide__icon" aria-hidden="true">
                <AppIcon name="users" />
              </span>
              <div>
                <h3 id="member-empty-guide-title">
                  {{ memberGuideCopy.title }}
                </h3>
                <p>{{ memberGuideCopy.intro }}</p>
              </div>
            </div>
            <ol class="member-empty-guide__steps">
              <li v-for="step in memberGuideCopy.steps" :key="step.title">
                <strong>{{ step.title }}</strong>
                <p>{{ step.body }}</p>
              </li>
            </ol>
            <button
              class="admin-button admin-button--primary member-empty-guide__action"
              type="button"
              aria-controls="member-display-name"
              @click="focusDisplayNameInput"
            >
              <AppIcon name="plus" />
              {{ memberGuideCopy.action }}
            </button>
          </div>
          <ul v-else class="member-list">
            <li v-for="member in members" :key="member.id" class="member-card">
              <span class="member-card__avatar" aria-hidden="true">{{
                member.displayName.slice(0, 1).toUpperCase()
              }}</span>
              <span class="member-card__details">
                <strong>{{ member.displayName }}</strong>
                <span>{{ member.loginId }}</span>
              </span>
              <span class="member-card__role">{{
                adminCopy.common.memberRole
              }}</span>
            </li>
          </ul>
        </section>

        <section
          class="admin-panel member-form-panel"
          aria-labelledby="create-member-title"
        >
          <h2 id="create-member-title">{{ copy.createTitle }}</h2>
          <form class="admin-form" @submit.prevent="createMember">
            <label class="admin-field">
              <span>{{ copy.displayName }}</span>
              <input
                id="member-display-name"
                ref="displayNameInput"
                v-model.trim="form.displayName"
                required
                maxlength="100"
                :placeholder="copy.displayNamePlaceholder"
                autocomplete="name"
                :aria-invalid="!!fieldErrors.displayName"
                aria-describedby="member-name-error"
              />
              <span
                v-if="fieldErrors.displayName"
                id="member-name-error"
                class="admin-field__error"
                >{{ fieldErrors.displayName }}</span
              >
            </label>
            <label class="admin-field">
              <span>{{ copy.loginId }}</span>
              <input
                v-model.trim="form.loginId"
                required
                maxlength="160"
                :placeholder="copy.loginIdPlaceholder"
                autocomplete="username"
                :aria-invalid="!!fieldErrors.loginId"
                aria-describedby="member-login-error"
              />
              <span
                v-if="fieldErrors.loginId"
                id="member-login-error"
                class="admin-field__error"
                >{{ fieldErrors.loginId }}</span
              >
            </label>
            <label class="admin-field">
              <span>{{ copy.initialPassword }}</span>
              <input
                v-model="form.initialPassword"
                required
                type="password"
                autocomplete="new-password"
                :aria-invalid="!!fieldErrors.initialPassword"
                aria-describedby="member-password-error"
              />
              <span
                v-if="fieldErrors.initialPassword"
                id="member-password-error"
                class="admin-field__error"
                >{{ fieldErrors.initialPassword }}</span
              >
            </label>
            <button
              class="admin-button admin-button--primary"
              type="submit"
              :disabled="saving"
            >
              <AppIcon name="plus" />
              {{ saving ? copy.creating : copy.create }}
            </button>
          </form>
        </section>
      </div>
    </template>
  </section>
</template>

<style scoped>
.admin-screen {
  width: min(100%, 1040px);
  margin: 0 auto;
  padding: 44px 0 64px;
  color: #233d37;
}

.admin-screen__header {
  margin-bottom: 28px;
}

.admin-screen__header h1 {
  margin: 0 0 10px;
  font-size: 1.75rem;
  letter-spacing: -1.5px;
  line-height: 1.15;
}

.admin-screen__intro,
.admin-panel__copy {
  max-width: 640px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.7;
}

.admin-screen__banner {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #d3ddc7;
  border-radius: 8px;
  background: #e9eedf;
  color: #526b46;
  font-size: 0.875rem;
  line-height: 1.6;
}

.admin-screen__banner--error {
  border-color: #e6ccba;
  background: #f9e9df;
  color: #925b3a;
}

.members-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 360px);
  align-items: start;
  gap: 18px;
}

.admin-panel {
  min-width: 0;
  padding: clamp(20px, 4vw, 28px);
  border: 1px solid #e0e4d9;
  border-radius: 12px;
  background: #fffefa;
  box-shadow: 0 10px 28px #233d3708;
}

.admin-panel__heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.admin-panel__heading h2,
.member-form-panel h2,
.completion-panel h2 {
  font-size: 1.1875rem;
  letter-spacing: -0.5px;
}

.admin-panel__copy {
  margin-top: 12px;
  font-size: 0.875rem;
}

.admin-pill {
  flex: 0 0 auto;
  padding: 7px 10px;
  border: 1px solid #d7dfd0;
  border-radius: 999px;
  background: #eef2e8;
  color: #536c53;
  font-size: 0.8125rem;
}

.admin-screen__status,
.admin-empty {
  margin-top: 18px;
  padding: 16px;
  border: 1px dashed #cfd8ca;
  border-radius: 8px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.6;
}

.admin-empty .admin-button {
  margin-top: 12px;
}

.member-empty-guide {
  margin-top: 18px;
  padding-top: 20px;
  border-top: 1px solid #e9ece3;
  color: #53675a;
}

.member-empty-guide__heading {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.member-empty-guide__icon {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: #e5ebdd;
  color: #426749;
}

.member-empty-guide__heading h3 {
  margin: 2px 0 5px;
  color: #233d37;
  font-size: 1.0625rem;
  letter-spacing: -0.35px;
  line-height: 1.35;
}

.member-empty-guide__heading p,
.member-empty-guide__steps p {
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.65;
}

.member-empty-guide__steps {
  display: grid;
  gap: 14px;
  margin: 18px 0 0;
  padding-left: 21px;
}

.member-empty-guide__steps li {
  padding-left: 3px;
}

.member-empty-guide__steps li::marker {
  color: #426749;
  font-size: 0.875rem;
  font-weight: 700;
}

.member-empty-guide__steps strong {
  display: block;
  margin-bottom: 3px;
  color: #435d4c;
  font-size: 0.875rem;
}

.member-empty-guide__action {
  margin-top: 20px;
}

.member-list {
  display: grid;
  gap: 10px;
  margin: 18px 0 0;
  padding: 0;
  list-style: none;
}

.member-card {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 12px;
  padding: 13px 0;
  border-bottom: 1px solid #e9ece3;
}

.member-card:last-child {
  border-bottom: 0;
}

.member-card__avatar {
  display: grid;
  width: 40px;
  height: 40px;
  flex: 0 0 auto;
  place-items: center;
  border-radius: 50%;
  background: #e5ebdd;
  color: #426749;
  font-size: 0.9375rem;
  font-weight: 700;
}

.member-card__details {
  display: grid;
  min-width: 0;
  flex: 1 1 auto;
  gap: 4px;
}

.member-card__details strong,
.member-card__details span {
  overflow-wrap: anywhere;
}

.member-card__details strong {
  font-size: 0.875rem;
}

.member-card__details span {
  color: #53675a;
  font-size: 0.8125rem;
}

.member-card__role {
  flex: 0 0 auto;
  color: #53675a;
  font-size: 0.8125rem;
}

.admin-form {
  display: grid;
  gap: 16px;
  margin-top: 20px;
}

.admin-field {
  display: grid;
  gap: 7px;
  color: #435d4c;
  font-size: 0.8125rem;
  font-weight: 600;
}

.admin-field input {
  width: 100%;
  min-height: 46px;
  padding: 11px 13px;
  border: 1px solid #d6ded0;
  border-radius: 7px;
  background: #fffefa;
  color: #233d37;
  font: inherit;
  font-size: 0.875rem;
}

.admin-field input::placeholder {
  color: #53675a;
}

.admin-field input:focus {
  outline: 2px solid #8da88e;
  outline-offset: 2px;
}

.admin-button {
  gap: 8px;
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  justify-content: center;
  padding: 11px 15px;
  border: 0;
  border-radius: 7px;
  font: inherit;
  font-size: 0.8125rem;
  font-weight: 600;
  text-align: center;
}

.admin-button--primary {
  background: #234e41;
  color: #f6f7ef;
}

.admin-button--primary:hover:not(:disabled) {
  background: #173e32;
}

.admin-button--quiet {
  background: #eef2e8;
  color: #536c53;
}

.admin-button:disabled {
  cursor: default;
  opacity: 0.58;
}

.completion-panel {
  max-width: 620px;
  margin: 0 auto;
  border-color: #d4dfcf;
  background: #f8faf4;
}

.completion-details {
  display: grid;
  gap: 12px;
  margin: 22px 0 0;
}

.completion-details div {
  padding: 12px 14px;
  border-radius: 7px;
  background: #eef2e8;
}

.completion-details dt {
  color: #53675a;
  font-size: 0.8125rem;
}

.completion-details dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
  color: #233d37;
  font-size: 0.875rem;
  font-weight: 600;
}

.completion-password {
  margin-top: 18px;
}

.completion-password input {
  letter-spacing: 0.08em;
}

.completion-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 9px;
  margin-top: 12px;
}

.completion-panel__notice {
  margin-top: 12px;
  color: #536c53;
  font-size: 0.8125rem;
}

.completion-panel__dismiss {
  margin-top: 20px;
}

@media (max-width: 740px) {
  .admin-screen {
    padding: 30px 0 48px;
  }

  .members-layout {
    grid-template-columns: minmax(0, 1fr);
  }
}
</style>
