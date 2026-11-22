<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import AppDialog from '../components/AppDialog.vue'
import AppIcon from '../components/AppIcon.vue'
import PageHeader from '../components/PageHeader.vue'
import RefreshButton from '../components/RefreshButton.vue'
import type { ApiServices, User } from './api/contracts'
import { accountInitials } from '../lib/account-initials'
import { errorMessage, ui } from '../lib/strings'
import { ServiceError } from '../services/contracts'

const props = defineProps<{ services: ApiServices; currentUserId: string }>()
const items = ref<User[]>([])
const loading = ref(false)
const loaded = ref(false)
const saving = ref(false)
const listError = ref('')
const saveError = ref('')
const notice = ref('')
const pending = ref<User | null>(null)
const number = new Intl.NumberFormat()
const roleLabels = { admin: ui.admin, member: ui.member }
const lastAdminMessage = 'Minimal satu admin aktif diperlukan.'
const nextRole = computed(() =>
  pending.value?.role === 'admin' ? 'member' : 'admin',
)
const demotionBlocked = computed(
  () => pending.value?.role === 'admin' && !hasOtherActiveAdmin(pending.value),
)
const members = computed(() =>
  items.value.map((user) => ({
    ...user,
    name: displayName(user),
    initials: accountInitials(user.full_name),
    demotionBlocked: user.role === 'admin' && !hasOtherActiveAdmin(user),
  })),
)

let disposed = false

function displayName(user: User): string {
  return user.full_name?.trim() || user.email
}

function hasOtherActiveAdmin(user: User): boolean {
  return items.value.some(
    (account) =>
      account.id !== user.id && account.role === 'admin' && account.is_active,
  )
}

async function load() {
  if (loading.value || saving.value) return
  loading.value = true
  listError.value = ''
  notice.value = ''
  try {
    const result = await props.services.users.list()
    if (!disposed) {
      items.value = result
      loaded.value = true
    }
  } catch (cause) {
    if (!disposed) listError.value = errorMessage(cause)
  } finally {
    if (!disposed) loading.value = false
  }
}

function openRoleChange(user: User, event: MouseEvent) {
  if (event.currentTarget instanceof HTMLButtonElement)
    event.currentTarget.focus({ preventScroll: true })
  notice.value = ''
  saveError.value = ''
  pending.value = user
}

async function confirm() {
  const target = pending.value
  if (!target || saving.value || demotionBlocked.value) return
  const role = nextRole.value
  saving.value = true
  saveError.value = ''
  try {
    if (role === 'member') {
      const latest = await props.services.users.list()
      if (disposed) return
      items.value = latest
      if (
        latest.find((account) => account.id === target.id)?.role !== target.role
      ) {
        saveError.value =
          'Daftar akun sudah diperbarui. Tutup dialog untuk meninjau perubahan.'
        return
      }
      if (!hasOtherActiveAdmin(target)) {
        saveError.value = lastAdminMessage
        return
      }
    }
    const user = await props.services.users.role(target.id, role)
    if (!disposed) {
      items.value = items.value.map((item) =>
        item.id === user.id ? user : item,
      )
      notice.value = `Peran ${displayName(user)} diperbarui menjadi ${roleLabels[user.role]}.`
      pending.value = null
    }
  } catch (cause) {
    if (!disposed)
      saveError.value =
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
  <section class="members-page" aria-labelledby="members-heading">
    <PageHeader title="Pengguna dan peran" title-id="members-heading">
      <template #actions>
        <RefreshButton
          class="members-page__refresh"
          :loading="loading"
          :disabled="loading || saving"
          @click="load"
        />
      </template>
      <p v-if="loaded" class="members-page__count">
        {{ number.format(items.length) }} akun
      </p>
    </PageHeader>

    <div v-if="listError" class="banner banner--error" role="alert">
      <p>{{ listError }}</p>
      <button type="button" class="text-button" @click="load">
        {{ ui.retry }}
      </button>
    </div>
    <p v-if="notice" class="banner members-page__notice" role="status">
      {{ notice }}
    </p>
    <p
      v-if="loading && !items.length"
      class="panel members-page__state"
      role="status"
    >
      Memuat pengguna… <AppIcon name="loading" />
    </p>
    <p
      v-else-if="loaded && !items.length && !listError"
      class="panel members-page__state"
    >
      Belum ada pengguna. <AppIcon name="users" />
    </p>

    <ul
      v-if="members.length"
      class="member-list"
      aria-label="Daftar pengguna"
      :aria-busy="loading"
    >
      <li v-for="member in members" :key="member.id" class="member-row">
        <span class="member-row__avatar" aria-hidden="true">
          <span v-if="member.initials">{{ member.initials }}</span>
          <AppIcon v-else name="user" />
        </span>
        <div class="member-row__identity">
          <h2>
            {{ member.name }}
            <span v-if="member.id === currentUserId" class="member-row__self"
              >Anda</span
            >
          </h2>
          <p v-if="member.name !== member.email">{{ member.email }}</p>
        </div>
        <div class="member-row__management">
          <div class="member-row__metadata">
            <span
              class="member-row__role"
              :class="{ 'member-row__role--admin': member.role === 'admin' }"
            >
              {{ roleLabels[member.role] }}
            </span>
            <span
              class="member-row__status"
              :class="{ 'member-row__status--active': member.is_active }"
            >
              {{ member.is_active ? 'Aktif' : 'Tidak aktif' }}
            </span>
          </div>
          <button
            type="button"
            class="button button--quiet member-row__action"
            :aria-label="`Ubah peran ${member.name}`"
            :aria-describedby="
              member.demotionBlocked
                ? `admin-role-note-${member.id}`
                : undefined
            "
            :disabled="loading || saving || member.demotionBlocked"
            @click="openRoleChange(member, $event)"
          >
            Ubah peran
          </button>
          <p
            v-if="member.demotionBlocked"
            :id="`admin-role-note-${member.id}`"
            class="member-row__role-note"
          >
            {{ lastAdminMessage }}
          </p>
        </div>
      </li>
    </ul>
    <p v-if="loaded" class="content-inset members-page__context">
      Daftar akun digunakan bersama. Penambahan anggota per lokasi belum
      tersedia.
    </p>

    <AppDialog
      v-if="pending"
      :title="`Ubah peran ${displayName(pending)}?`"
      :description="
        pending.id === currentUserId && nextRole === 'member'
          ? 'Beralih ke Anggota akan langsung menutup akses Anda ke Perangkat dan Pengguna.'
          : undefined
      "
      :busy="saving"
      @close="pending = null"
    >
      <dl class="role-change">
        <div>
          <dt>Peran saat ini</dt>
          <dd>{{ roleLabels[pending.role] }}</dd>
        </div>
        <div>
          <dt>Peran baru</dt>
          <dd>{{ roleLabels[nextRole] }}</dd>
        </div>
      </dl>
      <p
        v-if="saveError"
        class="banner banner--error role-change__error"
        role="alert"
      >
        {{ saveError }}
      </p>
      <div class="role-change__actions">
        <button
          type="button"
          class="button button--quiet"
          :disabled="saving"
          @click="pending = null"
        >
          Batal
        </button>
        <button
          type="button"
          class="button button--primary"
          :disabled="saving || demotionBlocked"
          @click="confirm"
        >
          {{ saving ? ui.saving : 'Konfirmasi perubahan' }}
        </button>
      </div>
    </AppDialog>
  </section>
</template>

<style scoped>
.members-page > .banner {
  padding-inline: var(--card-inset);
}

.members-page__context {
  margin-top: 14px;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.6;
}

.members-page__state {
  display: flex;
  align-items: center;
  gap: 10px;
  color: var(--muted);
}

.member-list {
  margin: 0;
  padding: 0;
  border: 1px solid #dce2d8;
  border-radius: 14px;
  background: #fffefa;
  list-style: none;
}

.member-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  grid-template-areas:
    'identity avatar'
    'management management';
  align-items: start;
  gap: 4px 12px;
  padding: 14px var(--card-inset);
}

.member-row + .member-row {
  border-top: 1px solid #e4e8df;
}

.member-row__avatar {
  grid-area: avatar;
  display: grid;
  width: 2.75rem;
  height: 2.75rem;
  place-items: center;
  border: 1px solid #dce2d8;
  border-radius: 50%;
  background: #e9eedf;
  color: var(--accent);
  font-size: 0.8125rem;
  font-weight: 700;
}

.member-row__identity {
  grid-area: identity;
  overflow-wrap: anywhere;
}

.member-row__identity h2 {
  font-size: 1rem;
  font-weight: 700;
  line-height: 1.4;
}

.member-row__identity p {
  margin-top: 3px;
  color: var(--muted);
  font-size: 0.875rem;
  line-height: 1.5;
}

.member-row__self {
  margin-inline-start: 4px;
  color: var(--muted);
  font-size: 0.75rem;
  font-weight: 500;
  white-space: nowrap;
}

.member-row__management,
.member-row__metadata {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  min-width: 0;
}

.member-row__management {
  grid-area: management;
  justify-content: space-between;
}

.member-row__role,
.member-row__status {
  color: var(--muted);
  font-size: 0.75rem;
  line-height: 1.45;
}

.member-row__role {
  padding: 4px 8px;
  border-radius: 999px;
  background: #f0f2e9;
  font-weight: 650;
}

.member-row__role--admin {
  background: #e2eee4;
  color: var(--accent);
}

.member-row__status::before {
  display: inline-block;
  width: 6px;
  height: 6px;
  margin-inline-end: 5px;
  border-radius: 50%;
  background: #8a9489;
  vertical-align: 0.1em;
  content: '';
}

.member-row__status--active::before {
  background: #4c7953;
}

.member-row__action {
  max-width: 100%;
  padding: 8px 12px;
  border-radius: 8px;
  color: var(--accent);
  font-size: 0.8125rem;
  font-weight: 650;
  overflow-wrap: anywhere;
}

.member-row__action:hover:not(:disabled) {
  background-color: #e2eadd;
}

.member-row__role-note {
  flex-basis: 100%;
  color: var(--muted);
  font-size: 0.8125rem;
  line-height: 1.45;
}

.role-change {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 20px;
  margin: 0;
  padding: 14px;
  border-radius: 8px;
  background: #f0f2e9;
}

.role-change > div {
  flex: 1 1 7rem;
}

.role-change dt {
  color: var(--muted);
  font-size: 0.875rem;
}

.role-change dd {
  margin: 4px 0 0;
  font-weight: 650;
}

.role-change__error {
  margin: 16px 0 0;
}

.role-change__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: end;
  gap: 8px;
  margin-top: 18px;
}

@media (min-width: 700px) {
  .member-row {
    grid-template-columns: minmax(0, 1fr) minmax(0, 16rem) auto;
    grid-template-areas: 'identity management avatar';
    align-items: center;
    gap: 14px;
    padding-block: 16px;
  }
}
</style>
