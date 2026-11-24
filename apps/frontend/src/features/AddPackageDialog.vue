<script setup lang="ts">
import {
  onBeforeUnmount,
  ref,
  shallowRef,
  useTemplateRef,
  type PropType,
} from 'vue'
import AppDialog from '../components/AppDialog.vue'
import { errorMessage } from '../lib/strings'
import type { ApiServices } from './api/contracts'
import { fillPackageDraft, type PackageDraft } from './package-draft'

const props = defineProps({
  analyzeScreenshot: {
    type: Function as PropType<ApiServices['shipments']['analyzeScreenshot']>,
    required: true,
  },
  mock: Boolean,
})
const emit = defineEmits<{ close: [] }>()

const maxScreenshotBytes = 5 * 1024 * 1024
const screenshotTypes = ['image/png', 'image/jpeg', 'image/webp']
const picker = useTemplateRef<HTMLInputElement>('screenshot-picker')
const file = shallowRef<File | null>(null)
const preview = ref('')
const busy = ref(false)
const feedback = ref('')
const error = ref('')
const draft = ref<PackageDraft>({
  resiNumber: '',
  courier: '',
  sender: '',
  products: '',
})
let request: AbortController | null = null

function clearScreenshot() {
  request?.abort()
  request = null
  busy.value = false
  file.value = null
  if (preview.value) URL.revokeObjectURL(preview.value)
  preview.value = ''
  feedback.value = ''
  error.value = ''
}

function selectScreenshot(event: Event) {
  const input = event.currentTarget as HTMLInputElement
  const next = input.files?.[0]
  input.value = ''
  if (!next) return

  clearScreenshot()
  if (!screenshotTypes.includes(next.type)) {
    error.value = 'Pilih tangkapan layar dalam format PNG, JPEG, atau WebP.'
  } else if (next.size > maxScreenshotBytes) {
    error.value =
      'Ukuran tangkapan layar melebihi 5 MiB. Pilih gambar yang lebih kecil.'
  } else if (!next.size) {
    error.value = 'File gambar kosong. Pilih tangkapan layar lain.'
  } else {
    file.value = next
    preview.value = URL.createObjectURL(next)
  }
}

async function autofill() {
  if (!file.value || busy.value) return
  const current = new AbortController()
  request = current
  busy.value = true
  error.value = ''
  feedback.value = ''
  try {
    const result = await props.analyzeScreenshot(file.value, current.signal)
    if (request !== current) return

    draft.value = fillPackageDraft(draft.value, result)
    feedback.value = Object.values(draft.value).every((value) => value.trim())
      ? 'Periksa kembali detail paket.'
      : 'Detail yang belum terbaca dapat diisi secara manual.'
  } catch (cause) {
    if (request === current) error.value = errorMessage(cause)
  } finally {
    if (request === current) {
      request = null
      busy.value = false
    }
  }
}

onBeforeUnmount(clearScreenshot)
</script>

<template>
  <AppDialog
    title="Tambah paket"
    description="Detail hanya tersedia selama formulir ini terbuka."
    @close="emit('close')"
  >
    <details class="package-screenshot">
      <summary>Isi dari tangkapan layar</summary>
      <div class="package-screenshot__body">
        <p class="field-help">PNG, JPEG, atau WebP hingga 5 MiB.</p>
        <input
          ref="screenshot-picker"
          type="file"
          :accept="screenshotTypes.join(',')"
          hidden
          @change="selectScreenshot"
        />
        <div class="package-screenshot__actions">
          <button
            class="button button--quiet"
            type="button"
            @click="picker?.click()"
          >
            {{ file ? 'Ganti gambar' : 'Pilih gambar' }}
          </button>
          <button
            v-if="file"
            class="text-button"
            type="button"
            @click="clearScreenshot"
          >
            Hapus gambar
          </button>
        </div>
        <img
          v-if="preview"
          class="package-screenshot__preview"
          :src="preview"
          alt="Pratinjau tangkapan layar"
        />
        <template v-if="file">
          <p class="field-help">
            {{
              mock
                ? 'Mode demo menggunakan contoh detail paket.'
                : 'Gambar asli akan dikirim ke OpenAI untuk membaca detail paket.'
            }}
          </p>
          <button
            class="button button--quiet"
            type="button"
            :disabled="busy"
            @click="autofill"
          >
            {{ error ? 'Coba lagi' : 'Isi detail dari gambar' }}
          </button>
        </template>
        <p v-if="busy || feedback" class="field-help" role="status">
          {{ busy ? 'Membaca tangkapan layar…' : feedback }}
        </p>
        <p v-if="error" class="field-error" role="alert">{{ error }}</p>
      </div>
    </details>

    <div class="package-draft">
      <label>
        Nomor resi
        <input
          v-model="draft.resiNumber"
          type="text"
          autocomplete="off"
          spellcheck="false"
        />
      </label>
      <label>
        Kurir
        <input v-model="draft.courier" type="text" autocomplete="off" />
      </label>
      <label>
        Nama pengirim
        <input v-model="draft.sender" type="text" autocomplete="off" />
      </label>
      <label>
        Nama produk
        <textarea
          v-model="draft.products"
          rows="3"
          placeholder="Satu nama produk per baris"
        />
      </label>
      <button
        class="button button--primary package-draft__done"
        type="button"
        @click="emit('close')"
      >
        Selesai meninjau
      </button>
    </div>
  </AppDialog>
</template>

<style scoped>
.package-screenshot {
  padding: 12px 14px;
  border: 1px solid #d6ded0;
  border-radius: 8px;
}

.package-screenshot summary {
  padding-block: 8px;
  cursor: pointer;
  font-weight: 650;
}

.package-screenshot__body,
.package-draft {
  display: grid;
  gap: 12px;
}

.package-screenshot__body {
  justify-items: start;
  padding-top: 8px;
}

.package-screenshot__body p,
.package-draft input {
  margin: 0;
}

.package-screenshot__actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.package-screenshot__preview {
  display: block;
  width: auto;
  max-width: 100%;
  max-height: 180px;
  object-fit: contain;
}

.package-draft {
  margin-top: 16px;
}

.package-draft label {
  display: grid;
  gap: 6px;
}

.package-draft textarea {
  width: 100%;
  padding: 12px 13px;
  border: 1px solid #d6ded0;
  border-radius: 5px;
  background: #fffefa;
  color: inherit;
  font: inherit;
  font-size: 1rem;
  resize: vertical;
}

.package-draft textarea:focus {
  outline: 2px solid #8da88e;
  outline-offset: 1px;
}

.package-draft__done {
  justify-self: end;
}
</style>
