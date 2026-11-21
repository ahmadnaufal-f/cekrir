import type { DeviceCategory, DeviceGuideStep } from '../types/device-ui'
import esp32Register from '../assets/device-setup/esp32-register.svg'
import esp32Credential from '../assets/device-setup/esp32-credential.svg'
import esp32ManualConfig from '../assets/device-setup/esp32-manual-config.svg'
import esp32HardwareCheck from '../assets/device-setup/esp32-hardware-check.svg'
import bardiPrepareCamera from '../assets/device-setup/bardi-prepare-camera.svg'
import bardiRegisterCamera from '../assets/device-setup/bardi-register-camera.svg'
import bardiSelectCamera from '../assets/device-setup/bardi-select-camera.svg'

const esp32Steps: readonly DeviceGuideStep[] = [
  {
    id: 'register',
    title: 'Daftarkan perangkat di aplikasi',
    description:
      'Tambahkan satu ESP32 untuk lokasi ini dengan nama yang mudah dikenali. Pendaftaran menyimpan identitas perangkat; status koneksinya belum diperiksa.',
    image: esp32Register,
    imageAlt:
      'Ilustrasi formulir pendaftaran perangkat yang terhubung dengan papan ESP32.',
  },
  {
    id: 'credential',
    title: 'Amankan kredensial sekali tampil',
    description:
      'Kredensial konfigurasi hanya ditampilkan sekali setelah pendaftaran. Simpan secara pribadi sebelum meninggalkan layar; penggunaannya pada firmware masih menunggu kesepakatan integrasi.',
    image: esp32Credential,
    imageAlt: 'Kartu kredensial tersimpan di balik simbol kunci dan pelindung.',
  },
  {
    id: 'manual-config',
    title: 'Buka sumber dan README',
    description:
      'Lanjutkan konfigurasi manual dan proses flash di luar aplikasi menggunakan sumber firmware dan README proyek. Cocokkan profil papan dengan perangkat yang benar-benar digunakan.',
    image: esp32ManualConfig,
    imageAlt: 'Dokumentasi proyek dan layar konfigurasi manual berdampingan.',
  },
  {
    id: 'hardware-check',
    title: 'Uji perangkat pada lokasi',
    description:
      'Gunakan langkah pengujian di README untuk pemeriksaan hardware. Pemicu berbasis kedekatan dan cahaya serta buzzer belum dituntaskan atau diverifikasi.',
    image: esp32HardwareCheck,
    imageAlt:
      'Pemeriksaan hardware pada papan kamera dengan satu pemeriksaan belum selesai.',
  },
]

const bardiSteps: readonly DeviceGuideStep[] = [
  {
    id: 'prepare-camera',
    title: 'Siapkan kamera dan jaringan',
    description:
      'Gunakan kamera BARDI yang memang Anda miliki dan panduan untuk modelnya. Periksa alamat RTSP serta data masuk dari sumber milik Anda; aplikasi tidak menetapkan nilai bawaan.',
    image: bardiPrepareCamera,
    imageAlt:
      'Ilustrasi kamera dan jaringan lokasi di samping panduan perangkat.',
  },
  {
    id: 'register-camera',
    title: 'Daftarkan nama dan koneksi opsional',
    description:
      'Masukkan nama kamera. Jika konfigurasi RTSP diperlukan, alamat dan data masuk bersifat opsional, dikirim saat disimpan, lalu tidak ditampilkan kembali.',
    image: bardiRegisterCamera,
    imageAlt:
      'Formulir pendaftaran kamera dengan kolom koneksi dan simbol kamera.',
  },
  {
    id: 'select-camera',
    title: 'Pilih satu kamera pengiriman',
    description:
      'Setelah kamera terdaftar, pilih satu sebagai kamera untuk foto paket. Pendaftaran atau konfigurasi tersimpan tidak membuktikan kamera sudah tersambung.',
    image: bardiSelectCamera,
    imageAlt:
      'Tiga kamera terdaftar dengan satu kamera ditandai sebagai pilihan.',
  },
]

interface DeviceSetupCopy {
  title: string
  subtitle: string
  statusNote: string
  steps: readonly DeviceGuideStep[]
  registerAction: string
  sourceLink?: string
  guideLink: string
}

interface DeviceGuideCommonCopy {
  title: string
  adminOnly: string
  illustrationDisclaimer: string
  registrationUnavailable: string
  loading: string
  loadingFailed: string
  retry: string
  linkUnavailable: string
  externalLinkNote: string
}

export const deviceGuideCopy = {
  common: {
    title: 'Status panduan dan referensi',
    adminOnly: 'Panduan perangkat hanya tersedia untuk admin lokasi ini.',
    illustrationDisclaimer: 'Ilustrasi alur penyiapan.',
    registrationUnavailable:
      'Pendaftaran perangkat dan pengaturan kamera belum tersedia di mode live.',
    loading: 'Memuat referensi…',
    loadingFailed: 'Referensi belum dapat dimuat.',
    retry: 'Coba lagi',
    linkUnavailable: 'Belum ada tautan referensi yang disetujui.',
    externalLinkNote: 'Tautan dibuka di browser eksternal.',
  },
  esp32: {
    title: 'Panduan penyiapan ESP32',
    subtitle:
      'Daftarkan di aplikasi, lalu lanjutkan konfigurasi firmware di luar aplikasi.',
    statusNote:
      'Firmware masih berupa scaffold. Konfigurasi dan koneksi perangkat belum diverifikasi; aplikasi tidak mengonfigurasi atau mem-flash firmware. Penggunaan kredensial pada firmware masih menunggu kesepakatan integrasi.',
    steps: esp32Steps,
    registerAction: 'Daftarkan perangkat',
    sourceLink: 'Lihat sumber firmware',
    guideLink: 'Baca panduan ESP32',
  },
  bardi: {
    title: 'Panduan penyiapan kamera BARDI',
    subtitle:
      'Siapkan kamera, simpan konfigurasi, lalu pilih kamera pengiriman.',
    statusNote:
      'Pengujian lokal pada unit milik sendiri mencakup login ONVIF/PTZ, pemutaran RTSP/TCP di VLC, dan satu gambar JPEG melalui FFmpeg. Panduan lengkap, pengambilan berulang, dan verifikasi backend masih menunggu. Pendaftaran atau konfigurasi tersimpan tidak membuktikan koneksi kamera.',
    steps: bardiSteps,
    registerAction: 'Daftarkan perangkat',
    guideLink: 'Buka referensi BARDI',
  },
} satisfies Record<DeviceCategory, DeviceSetupCopy> & {
  common: DeviceGuideCommonCopy
}
