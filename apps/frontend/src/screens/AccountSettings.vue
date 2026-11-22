<script setup lang="ts">
import { computed } from 'vue'
import PageHeader from '../components/PageHeader.vue'
import ShipmentNotificationSettings from '../components/ShipmentNotificationSettings.vue'
import type { ApiServices, User } from '../features/api/contracts'
import { ui } from '../lib/strings'

const props = defineProps<{
  user: User
  services: ApiServices
  liveStatus: string
  notifications: boolean
  checkingNotificationPermission: boolean
  notificationSettingMessage: string
}>()
const emit = defineEmits<{
  logout: []
  'update:notifications': [enabled: boolean]
}>()
const accountName = computed(() => props.user.full_name?.trim())
</script>

<template>
  <section class="api-settings" aria-labelledby="settings-title">
    <PageHeader
      class="api-settings__heading"
      :title="ui.settings"
      title-id="settings-title"
    />
    <article class="panel">
      <h2>{{ accountName || user.email }}</h2>
      <p v-if="accountName">{{ user.email }}</p>
      <p>{{ user.role === 'admin' ? 'Admin' : 'Anggota' }}</p>
      <p class="supporting">
        Sesi disimpan sementara. Muat ulang halaman atau tutup aplikasi untuk
        mengakhiri sesi lokal. Keluar tidak mencabut token di server.
      </p>
      <button class="button button--quiet" @click="emit('logout')">
        Keluar
      </button>
    </article>
    <ShipmentNotificationSettings
      :enabled="notifications"
      :checking-permission="checkingNotificationPermission"
      :preference-message="notificationSettingMessage"
      :account-id="user.id"
      :shipments="services.shipments"
      @update:enabled="emit('update:notifications', $event)"
    />
    <article class="panel">
      <h2>Ketersediaan layanan</h2>
      <p>
        Catatan paket digunakan bersama; pemisahan lokasi penerimaan belum
        tersedia.
      </p>
      <p>
        Foto pengiriman, pembayaran, dan notifikasi latar belakang belum
        tersedia di aplikasi ini.
      </p>
      <p>
        Pembaruan langsung:
        {{
          liveStatus === 'connected'
            ? 'terhubung'
            : services.mode === 'mock'
              ? 'simulasi'
              : 'sementara tidak tersedia'
        }}.
      </p>
    </article>
  </section>
</template>
