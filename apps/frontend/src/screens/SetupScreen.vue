<script setup lang="ts">
import DeviceSetupGuide from '../components/DeviceSetupGuide.vue'
import { adminCopy } from '../lib/admin-copy'
import type { AppServices } from '../services/contracts'
import type { AppUser } from '../types/app'

defineProps<{ services: AppServices; user: AppUser }>()
const emit = defineEmits<{ sessionExpired: [] }>()
</script>

<template>
  <section class="admin-screen setup-screen" aria-labelledby="setup-title">
    <header class="admin-screen__header">
      <h1 id="setup-title">{{ adminCopy.setup.title }}</h1>
      <p class="admin-screen__intro">{{ adminCopy.setup.intro }}</p>
    </header>

    <p
      v-if="user.role !== 'admin'"
      class="admin-screen__banner admin-screen__banner--error"
      role="alert"
    >
      {{ adminCopy.common.adminOnly }}
    </p>

    <div v-else class="setup-guides">
      <DeviceSetupGuide
        :services="services"
        :user="user"
        kind="esp32"
        @session-expired="emit('sessionExpired')"
      />
      <DeviceSetupGuide
        :services="services"
        :user="user"
        kind="bardi"
        @session-expired="emit('sessionExpired')"
      />
    </div>
  </section>
</template>

<style scoped>
.admin-screen {
  width: min(100%, 920px);
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
  letter-spacing: -1px;
  line-height: 1.2;
}

.admin-screen__intro {
  max-width: 700px;
  color: #53675a;
  font-size: 0.875rem;
  line-height: 1.7;
}

.admin-screen__banner {
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid #e6ccba;
  border-radius: 8px;
  background: #f9e9df;
  color: #925b3a;
  font-size: 0.875rem;
  line-height: 1.6;
}

.setup-guides {
  display: grid;
  gap: 22px;
}

@media (max-width: 620px) {
  .admin-screen {
    padding: 30px 0 48px;
  }
}
</style>
