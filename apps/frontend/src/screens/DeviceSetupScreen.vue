<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '../components/AppIcon.vue'
import DeviceSetupGuide from '../components/DeviceSetupGuide.vue'
import SetupStepCarousel from '../components/SetupStepCarousel.vue'
import { deviceGuideCopy } from '../lib/device-guide-copy'
import type { AppServices } from '../services/contracts'
import type { AppUser } from '../types/app'
import type { DeviceCategory } from '../types/device-ui'

const props = defineProps<{
  services: AppServices
  user: AppUser
  kind: DeviceCategory
}>()

const emit = defineEmits<{
  back: []
  register: []
  sessionExpired: []
}>()

const copy = computed(() => deviceGuideCopy[props.kind])
</script>

<template>
  <section class="device-setup-screen" :aria-labelledby="`${kind}-setup-title`">
    <button
      class="device-setup-screen__back"
      type="button"
      @click="emit('back')"
    >
      <AppIcon name="back" />
      Kembali ke perangkat
    </button>

    <header class="device-setup-screen__header">
      <h1 :id="`${kind}-setup-title`">{{ copy.title }}</h1>
      <p class="device-setup-screen__subtitle">{{ copy.subtitle }}</p>
      <p class="device-setup-screen__disclaimer">
        {{ deviceGuideCopy.common.illustrationDisclaimer }}
      </p>
    </header>

    <SetupStepCarousel :label="copy.title" :steps="copy.steps" />

    <div class="device-setup-screen__actions">
      <button
        class="device-setup-screen__register"
        type="button"
        @click="emit('register')"
      >
        <AppIcon name="plus" />
        {{ copy.registerAction }}
      </button>
    </div>

    <DeviceSetupGuide
      :services="services"
      :user="user"
      :kind="kind"
      @session-expired="emit('sessionExpired')"
    />
  </section>
</template>

<style scoped>
.device-setup-screen {
  width: min(100%, 920px);
  margin: 0 auto;
  padding: 0 0 52px;
  color: #233d37;
}

.device-setup-screen__back {
  display: inline-flex;
  min-height: 44px;
  align-items: center;
  gap: 8px;
  padding: 7px 0;
  border: 0;
  background: transparent;
  color: #435d4c;
  font-size: 0.875rem;
  font-weight: 650;
  text-align: left;
  text-decoration: underline;
  text-decoration-color: #9aab94;
  text-underline-offset: 4px;
}

.device-setup-screen__back:hover {
  color: #173e32;
  text-decoration-color: currentColor;
}

.device-setup-screen__header {
  margin: 17px 0 22px;
}

.device-setup-screen__header h1 {
  margin: 0;
  color: #233d37;
  font-size: clamp(1.75rem, 4vw, 2.25rem);
  font-weight: 700;
  letter-spacing: -0.04em;
  line-height: 1.16;
  text-wrap: balance;
}

.device-setup-screen__subtitle {
  max-width: 68ch;
  margin: 11px 0 0;
  color: #435d4c;
  font-size: 0.9375rem;
  line-height: 1.7;
}

.device-setup-screen__disclaimer {
  max-width: 72ch;
  margin: 8px 0 0;
  color: #53675a;
  font-size: 0.8125rem;
  line-height: 1.65;
}

.device-setup-screen__actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.device-setup-screen__register {
  display: inline-flex;
  min-height: 48px;
  align-items: center;
  justify-content: center;
  gap: 9px;
  padding: 11px 16px;
  border: 0;
  border-radius: 8px;
  background: #234e41;
  color: #f6f7f2;
  font-size: 0.875rem;
  font-weight: 680;
}

.device-setup-screen__register:hover {
  background: #173e32;
}

@media (max-width: 620px) {
  .device-setup-screen {
    padding-bottom: 40px;
  }

  .device-setup-screen__header {
    margin-top: 14px;
  }

  .device-setup-screen__subtitle {
    font-size: 0.875rem;
  }

  .device-setup-screen__actions {
    margin-top: 12px;
  }

  .device-setup-screen__register {
    width: 100%;
  }
}
</style>
