<script setup lang="ts">
import { onBeforeUnmount, onMounted, useId, useTemplateRef } from 'vue'
import AppIcon from './AppIcon.vue'

const props = withDefaults(
  defineProps<{
    title: string
    description?: string
    busy?: boolean
    closeLabel?: string
  }>(),
  {
    busy: false,
    closeLabel: 'Tutup',
  },
)

const emit = defineEmits<{ close: [] }>()

const dialog = useTemplateRef<HTMLDialogElement>('dialog')
const titleId = `app-dialog-title-${useId()}`
const descriptionId = `app-dialog-description-${useId()}`

let opener: HTMLElement | null = null
let previousBodyOverflow: string | null = null
let previousBodyOverflowPriority = ''

onMounted(() => {
  const element = dialog.value
  if (!element) return

  const body = element.ownerDocument.body
  const activeElement = element.ownerDocument.activeElement
  opener = activeElement instanceof HTMLElement ? activeElement : null
  previousBodyOverflow = body.style.getPropertyValue('overflow')
  previousBodyOverflowPriority = body.style.getPropertyPriority('overflow')
  body.style.setProperty('overflow', 'hidden')

  if (!element.open) element.showModal()
})

onBeforeUnmount(() => {
  const element = dialog.value
  if (element?.open) element.close()

  const body = element?.ownerDocument.body
  if (body && previousBodyOverflow !== null) {
    if (previousBodyOverflow) {
      body.style.setProperty(
        'overflow',
        previousBodyOverflow,
        previousBodyOverflowPriority,
      )
    } else {
      body.style.removeProperty('overflow')
    }
  }

  if (opener?.isConnected) opener.focus({ preventScroll: true })
})

function requestClose() {
  if (!props.busy) emit('close')
}

function handleCancel(event: Event) {
  event.preventDefault()
  requestClose()
}

function handleKeydown(event: KeyboardEvent) {
  if (event.key !== 'Tab') return
  const element = dialog.value
  if (!element) return
  const controls = Array.from(
    element.querySelectorAll<HTMLElement>(
      'a[href], button, input, select, textarea, summary, [tabindex]',
    ),
  ).filter(
    (control) =>
      control.tabIndex >= 0 &&
      !control.matches(':disabled') &&
      !control.closest('[inert]') &&
      control.getClientRects().length > 0 &&
      (!control.checkVisibility || control.checkVisibility()) &&
      getComputedStyle(control).visibility === 'visible',
  )
  const first = controls[0]
  const last = controls.at(-1)
  if (!first || !last) {
    event.preventDefault()
    element.focus()
    return
  }
  const active = element.ownerDocument.activeElement
  if (event.shiftKey && (active === first || active === element)) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && (active === last || active === element)) {
    event.preventDefault()
    first.focus()
  }
}
</script>

<template>
  <dialog
    ref="dialog"
    class="app-dialog"
    tabindex="-1"
    aria-modal="true"
    :aria-labelledby="titleId"
    :aria-describedby="props.description ? descriptionId : undefined"
    :aria-busy="props.busy || undefined"
    @cancel="handleCancel"
    @keydown="handleKeydown"
  >
    <header class="app-dialog__header">
      <h2 :id="titleId" class="app-dialog__title">{{ props.title }}</h2>
      <button
        class="app-dialog__close"
        type="button"
        :aria-label="props.closeLabel"
        :disabled="props.busy"
        autofocus
        @click="requestClose"
      >
        <AppIcon name="close" />
      </button>
    </header>
    <div class="app-dialog__body">
      <p
        v-if="props.description"
        :id="descriptionId"
        class="app-dialog__description"
      >
        {{ props.description }}
      </p>
      <div class="app-dialog__content"><slot /></div>
    </div>
  </dialog>
</template>

<style scoped>
.app-dialog {
  position: fixed;
  inset: 0;
  display: flex;
  width: min(calc(100% - 2rem), 32.5rem);
  max-width: 32.5rem;
  max-height: calc(
    100vh - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px) -
      2rem
  );
  max-height: calc(
    100dvh - env(safe-area-inset-top, 0px) - env(safe-area-inset-bottom, 0px) -
      2rem
  );
  flex-direction: column;
  margin: auto;
  padding: 0;
  overflow: hidden;
  border: 1px solid #d6ded0;
  border-radius: 12px;
  background: #fffefa;
  color: #233d37;
  box-shadow: 0 18px 42px rgb(23 42 34 / 22%);
}

.app-dialog::backdrop {
  background: rgb(24 38 32 / 48%);
}

.app-dialog:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 3px;
}

.app-dialog__header {
  display: flex;
  flex: 0 0 auto;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 20px 22px;
  border-bottom: 1px solid #dfe4d9;
}

.app-dialog__title {
  min-width: 0;
  margin: 0;
  color: #233d37;
  font-size: clamp(1.125rem, 4vw, 1.375rem);
  font-weight: 650;
  line-height: 1.35;
  overflow-wrap: anywhere;
}

.app-dialog__close {
  display: grid;
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  place-items: center;
  margin: -5px -6px 0 0;
  padding: 0;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: #53675a;
}

.app-dialog__close:hover:not(:disabled) {
  background: #eef2e8;
  color: #233d37;
}

.app-dialog__close:focus-visible {
  outline: 3px solid #b88736;
  outline-offset: 1px;
}

.app-dialog__body {
  min-height: 0;
  overflow-y: auto;
  overscroll-behavior: contain;
  padding: 20px 22px calc(20px + env(safe-area-inset-bottom, 0px));
  -webkit-overflow-scrolling: touch;
}

.app-dialog__description {
  margin: 0 0 18px;
  color: #53675a;
  font-size: 1rem;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.app-dialog__content {
  min-width: 0;
  color: #233d37;
}

@media (max-width: 420px) {
  .app-dialog__header {
    padding: 16px 18px;
  }

  .app-dialog__body {
    padding-right: 18px;
    padding-left: 18px;
  }
}
</style>
