import type { DeviceCategory, DeviceGuideStep } from '../types/device-ui'
import esp32Register from '../assets/device-setup/esp32-register.svg'
import esp32Credential from '../assets/device-setup/esp32-credential.svg'
import esp32ManualConfig from '../assets/device-setup/esp32-manual-config.svg'
import esp32HardwareCheck from '../assets/device-setup/esp32-hardware-check.svg'
import tuyaDownloadQr from '../assets/device-setup/tuya-download-qr.png'
import tuyaAddDevice from '../assets/device-setup/tuya-add-device.png'
import tuyaOnvifMenu from '../assets/device-setup/tuya-onvif-menu.png'
import tuyaOnvifSettings from '../assets/device-setup/tuya-onvif-settings.png'
import bardiRegisterCamera from '../assets/device-setup/bardi-register-camera.svg'
import bardiSelectCamera from '../assets/device-setup/bardi-select-camera.svg'
import courierCameraPosition from '../assets/device-setup/courier-camera-position.png'

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

const tuyaCameraSteps: readonly DeviceGuideStep[] = [
  {
    id: 'install-tuya',
    title: 'Instal aplikasi Tuya',
    description:
      'Pindai kode QR atau buka Google Play untuk menginstal Tuya. Daftarkan kamera di Tuya agar bisa terhubung ke layanan web Tuya. Aplikasi BARDI tidak mendukung koneksi ini.',
    image: tuyaDownloadQr,
    imageAlt: 'Kode QR untuk membuka aplikasi Tuya di Google Play.',
    download: {
      href: 'https://play.google.com/store/apps/details?id=com.tuya.smart',
      label: 'Buka Tuya di Google Play',
    },
  },
  {
    id: 'pair-camera',
    title: 'Tambahkan kamera di Tuya',
    description:
      'Di halaman utama Tuya, ketuk tombol + di kanan atas, lalu pilih Add Device. Ikuti petunjuk di aplikasi sampai kamera muncul di daftar perangkat.',
    image: tuyaAddDevice,
    imageAlt: 'Tombol tambah di kanan atas mengarah ke pilihan Add Device.',
  },
  {
    id: 'open-onvif',
    title: 'Buka pengaturan ONVIF',
    description:
      'Buka kamera yang sudah ditambahkan. Masuk ke pengaturan kamera, lalu ketuk Onvif di bagian Advanced Settings.',
    image: tuyaOnvifMenu,
    imageAlt: 'Pilihan Onvif di bagian Advanced Settings.',
  },
  {
    id: 'configure-onvif',
    title: 'Aktifkan ONVIF dan atur kata sandi',
    description:
      'Nyalakan Onvif Switch dan catat IP address yang ditampilkan. Ketuk Set a New Password atau Reset Password, lalu buat dan simpan kata sandi ONVIF untuk langkah berikutnya.',
    image: tuyaOnvifSettings,
    imageAlt: 'Onvif Switch aktif, diikuti IP address dan Reset Password.',
  },
  {
    id: 'register-camera',
    title: 'Daftarkan kamera di Cekrir',
    description:
      'Kembali ke Cekrir. Buka Perangkat, pilih tab Kamera, lalu ketuk Daftarkan perangkat. Masukkan nama kamera, alamat IP, dan kata sandi ONVIF yang tadi Anda catat.',
    image: bardiRegisterCamera,
    imageAlt:
      'Formulir pendaftaran kamera dengan kolom koneksi dan simbol kamera.',
  },
  {
    id: 'check-courier-view',
    title: 'Periksa area kedatangan kurir',
    description:
      'Arahkan kamera ke tempat kurir biasanya berdiri saat mengantar paket. Cek tampilan langsung di Tuya dan pastikan kurir terlihat jelas dari posisi tersebut.',
    image: courierCameraPosition,
    imageAlt: 'Kamera mengarah ke tempat kurir berdiri di pintu masuk.',
  },
  {
    id: 'select-camera',
    title: 'Pilih satu kamera pengiriman',
    description:
      'Jika ada beberapa kamera terdaftar, pilih kamera yang paling jelas menghadap area penerimaan paket. Minta pengelola Cekrir menetapkan kamera tersebut sebagai kamera pengiriman.',
    image: bardiSelectCamera,
    imageAlt:
      'Tiga kamera terdaftar dengan satu kamera ditandai sebagai pilihan.',
  },
]

interface DeviceSetupCopy {
  title: string
  subtitle: string
  registeredSubtitle?: string
  statusNote: string
  steps: readonly DeviceGuideStep[]
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
      'Pendaftaran perangkat dan pengaturan kamera belum tersedia.',
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
    registeredSubtitle:
      'ESP32 sudah terdaftar. Buka kembali langkah penyiapan dan referensi firmware di bawah.',
    statusNote:
      'Firmware masih berupa scaffold. Konfigurasi dan koneksi perangkat belum diverifikasi; aplikasi tidak mengonfigurasi atau mem-flash firmware. Penggunaan kredensial pada firmware masih menunggu kesepakatan integrasi.',
    steps: esp32Steps,
    sourceLink: 'Lihat sumber firmware',
    guideLink: 'Baca panduan ESP32',
  },
  bardi: {
    title: 'Panduan penyiapan kamera dengan Tuya',
    subtitle: 'Hubungkan kamera di Tuya, lalu daftarkan di Cekrir.',
    statusNote:
      'Foto pengiriman menggunakan kamera Tuya yang ditetapkan oleh pengelola Cekrir.',
    steps: tuyaCameraSteps,
    guideLink: 'Buka referensi kamera',
  },
} satisfies Record<DeviceCategory, DeviceSetupCopy> & {
  common: DeviceGuideCommonCopy
}
