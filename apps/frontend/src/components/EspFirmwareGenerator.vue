<script setup lang="ts">
import { reactive, shallowRef } from 'vue'
import { generateEspConfig } from '../lib/esp-firmware'

const props = defineProps<{ deviceId: string; deviceKey: string }>()
const form = reactive({ wifiSsid: '', wifiPassword: '', apiBaseUrl: 'https://api.cekrir.bakuretsumagic.my.id/api/v1', rootCa: '', courier: 'jne' })
const error = shallowRef('')

function download(): void {
  try {
    const contents = generateEspConfig({ ...form, deviceId: props.deviceId, deviceKey: props.deviceKey })
    const url = URL.createObjectURL(new Blob([contents], { type: 'text/plain;charset=utf-8' }))
    const link = document.createElement('a')
    link.href = url
    link.download = 'config.h'
    link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    error.value = ''
  } catch (cause) {
    error.value = cause instanceof Error ? cause.message : 'Could not create configuration.'
  }
}
</script>

<template>
  <form class="admin-form" @submit.prevent="download">
    <h3>Siapkan konfigurasi ESP32</h3>
    <p>Konfigurasi dibuat di perangkat ini dan berisi kata sandi Wi-Fi serta kunci ESP32. Jangan bagikan atau masukkan ke Git.</p>
    <label class="admin-field">Nama Wi-Fi 2.4 GHz <input v-model="form.wifiSsid" required autocomplete="off" /></label>
    <label class="admin-field">Kata sandi Wi-Fi <input v-model="form.wifiPassword" type="password" autocomplete="off" /></label>
    <label class="admin-field">Alamat API <input v-model="form.apiBaseUrl" type="url" required /></label>
    <label class="admin-field">Kode kurir <input v-model="form.courier" required pattern="[a-z0-9_-]{2,32}" /></label>
    <label class="admin-field">Sertifikat root CA API (PEM) <textarea v-model="form.rootCa" required rows="4" /></label>
    <p>Simpan file sebagai <code>apps/esp32/include/config.h</code>, lalu build dan upload environment <code>esp32_s3_cam_onboarded</code> melalui PlatformIO.</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <button class="admin-button admin-button--primary" type="submit">Unduh config.h</button>
  </form>
</template>
