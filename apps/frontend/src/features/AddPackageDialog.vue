<script setup lang="ts">
import {
  onBeforeUnmount,
  nextTick,
  ref,
  shallowRef,
  useId,
  useTemplateRef,
  type PropType,
} from 'vue'
import AppDialog from '../components/AppDialog.vue'
import TabSelector from '../components/TabSelector.vue'
import { errorMessage } from '../lib/strings'
import type { ApiServices } from './api/contracts'
import {
  fillPackageDraft,
  indonesiaCouriers,
  isShopeeExpress,
  type PackageDraft,
} from './package-draft'

const props = defineProps({
  analyzeScreenshot: {
    type: Function as PropType<ApiServices['shipments']['analyzeScreenshot']>,
    required: true,
  },
  addExpected: {
    type: Function as PropType<ApiServices['shipments']['addExpected']>,
    required: true,
  },
  mock: Boolean,
})
const emit = defineEmits<{ close: []; saved: [id: string] }>()

const tabId = `add-package-${useId()}`
const tabs = [
  { value: 'manual', label: 'Isi manual', panelId: `${tabId}-manual-panel` },
  { value: 'ai', label: 'Pakai AI', panelId: `${tabId}-ai-panel` },
]
const activeTab = ref('manual')

const maxScreenshotBytes = 5 * 1024 * 1024
const screenshotTypes = ['image/png', 'image/jpeg', 'image/webp']
const picker = useTemplateRef<HTMLInputElement>('screenshot-picker')
const resiInput = useTemplateRef<HTMLInputElement>('resi-input')
const file = shallowRef<File | null>(null)
const preview = ref('')
const busy = ref(false)
const feedback = ref('')
const error = ref('')
const reviewNote = ref('')
const saving = ref(false)
const saveError = ref('')
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
    if (result.courier_service && !isShopeeExpress(result.courier_service)) {
      draft.value.courier = ''
      reviewNote.value =
        'Kurir pada tangkapan layar belum didukung. Pilih Shopee Express jika sesuai dengan paket.'
    } else {
      reviewNote.value =
        'Periksa detail dari tangkapan layar sebelum menyimpan.'
    }
    if (result.resi_number) {
      activeTab.value = 'manual'
      void nextTick(() => resiInput.value?.focus())
    } else {
      feedback.value =
        'Nomor resi belum terbaca. Pilih tangkapan layar lain atau isi secara manual.'
    }
  } catch (cause) {
    if (request === current) error.value = errorMessage(cause)
  } finally {
    if (request === current) {
      request = null
      busy.value = false
    }
  }
}

async function savePackage() {
  if (saving.value || busy.value) return
  const resi = draft.value.resiNumber.trim()
  const sender = draft.value.sender.trim()
  const products = draft.value.products
    .split('\n')
    .map((name) => name.trim())
    .filter(Boolean)
  saveError.value = ''
  if (!/^[A-Za-z0-9-]{3,64}$/.test(resi) || draft.value.courier !== 'spx') {
    saveError.value = 'Isi nomor resi yang valid dan pilih Shopee Express.'
    return
  }
  if (products.length > 20 || products.some((name) => [...name].length > 200)) {
    saveError.value =
      'Isi maksimal 20 nama produk, masing-masing hingga 200 karakter.'
    return
  }

  saving.value = true
  try {
    const packageItem = await props.addExpected({
      resi_number: resi,
      courier: 'spx',
      sender_name: sender || null,
      product_names: products,
    })
    emit('saved', packageItem.id)
  } catch (cause) {
    saveError.value = errorMessage(cause)
  } finally {
    saving.value = false
  }
}

onBeforeUnmount(clearScreenshot)
</script>

<template>
  <AppDialog title="Tambah paket" :busy="saving" @close="emit('close')">
    <TabSelector
      :id="tabId"
      v-model="activeTab"
      class="package-tabs"
      label="Cara menambah paket"
      :tabs="tabs"
    />

    <section
      v-show="activeTab === 'ai'"
      :id="tabs[1]?.panelId"
      :aria-labelledby="`${tabId}-ai`"
      role="tabpanel"
    >
      <div class="package-screenshot">
        <p>
          Unggah tangkapan layar pembelian yang menampilkan
          <strong>nomor resi</strong>. Jika ada, sertakan nama kurir, nama
          pengirim, dan informasi produk.
        </p>
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
    </section>

    <section
      v-show="activeTab === 'manual'"
      :id="tabs[0]?.panelId"
      :aria-labelledby="`${tabId}-manual`"
      role="tabpanel"
    >
      <form class="package-draft" @submit.prevent="savePackage">
        <p v-if="reviewNote" class="field-help" role="status">
          {{ reviewNote }}
        </p>
        <label>
          Nomor resi
          <input
            ref="resi-input"
            v-model="draft.resiNumber"
            type="text"
            autocomplete="off"
            spellcheck="false"
            maxlength="64"
            :readonly="saving"
            required
          />
        </label>
        <div class="package-draft__field">
          <label :for="`${tabId}-courier`">Kurir</label>
          <select
            :id="`${tabId}-courier`"
            v-model="draft.courier"
            :disabled="saving"
            required
          >
            <option disabled value="">Pilih kurir</option>
            <option
              v-for="courier in indonesiaCouriers"
              :key="courier.code"
              :value="courier.code"
              :disabled="courier.code !== 'spx'"
            >
              {{ courier.name }}
            </option>
          </select>
        </div>
        <label>
          <span
            >Nama pengirim
            <span class="package-draft__optional">(opsional)</span></span
          >
          <input
            v-model="draft.sender"
            type="text"
            autocomplete="off"
            maxlength="200"
            :readonly="saving"
          />
        </label>
        <label>
          <span
            >Nama produk
            <span class="package-draft__optional">(opsional)</span></span
          >
          <textarea
            v-model="draft.products"
            rows="3"
            placeholder="Satu nama produk per baris"
            :readonly="saving"
          />
        </label>
        <p v-if="saveError" class="field-error" role="alert">{{ saveError }}</p>
        <button
          class="button button--primary package-draft__done"
          type="submit"
          :disabled="saving || busy"
        >
          {{ saving ? 'Menyimpan…' : 'Simpan paket' }}
        </button>
      </form>
    </section>
  </AppDialog>
</template>

<style scoped>
.package-tabs {
  --card-inset: 18px;
}

.package-tabs :deep(.tab-selector__tab) {
  flex: 1;
}

.package-screenshot,
.package-draft {
  display: grid;
  gap: 12px;
  margin-top: 16px;
}

.package-screenshot {
  justify-items: start;
  line-height: 1.6;
}

.package-screenshot p,
.package-draft p,
.package-draft input,
.package-draft select {
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

.package-draft label,
.package-draft__field {
  display: grid;
  gap: 6px;
}

.package-draft__field label {
  margin: 0;
}

.package-draft__optional {
  color: #53675a;
  font-weight: 400;
}

.package-draft input {
  font-weight: 400;
}

.package-draft select,
.package-draft textarea {
  width: 100%;
  padding: 12px 13px;
  border: 1px solid #d6ded0;
  border-radius: 5px;
  background: #fffefa;
  color: inherit;
  font: inherit;
  font-size: 1rem;
  font-weight: 400;
}

.package-draft textarea {
  resize: vertical;
}

.package-draft select:focus,
.package-draft textarea:focus {
  outline: 2px solid #8da88e;
  outline-offset: 1px;
}

.package-draft__done {
  justify-self: end;
}
</style>
