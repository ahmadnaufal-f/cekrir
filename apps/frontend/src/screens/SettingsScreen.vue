<script setup lang="ts">
import type { AppUser } from '../types/app'
import { ui } from '../lib/strings'
import { shellCopy as copy } from '../lib/shell-copy'
defineProps<{ user: AppUser; signingOut: boolean }>()
const emit = defineEmits<{ logout: [] }>()
</script>
<template>
  <section class="settings-page">
    <h1>{{ copy.account }}</h1>
    <div class="panel account-panel">
      <h2>{{ user.displayName }}</h2>
      <dl>
        <div>
          <dt>{{ copy.identity }}</dt>
          <dd>{{ user.loginId }}</dd>
        </div>
        <div>
          <dt>{{ copy.role }}</dt>
          <dd>{{ user.role === 'admin' ? ui.admin : ui.member }}</dd>
        </div>
      </dl>
      <p class="supporting">{{ copy.session }}</p>
    </div>
    <slot />
    <button
      class="button button--quiet logout-button"
      :disabled="signingOut"
      @click="emit('logout')"
    >
      {{ signingOut ? copy.signingOut : ui.logout }}
    </button>
  </section>
</template>
<style scoped>
.settings-page {
  max-width: 760px;
}
.account-panel {
  margin-bottom: 24px;
}
dl {
  margin: 24px 0;
  display: grid;
  gap: 16px;
}
dt {
  color: #526557;
  font-size: 0.875rem;
}
dd {
  margin: 4px 0 0;
  overflow-wrap: anywhere;
}
.logout-button {
  margin-top: 24px;
}
</style>
