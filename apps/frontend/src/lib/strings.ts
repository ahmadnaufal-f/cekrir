// Bahasa Indonesia is a reversible prototype default. Keep UI copy in this module.
export const ui = {
  brand: 'cekrir',
  deliveries: 'Paket diterima',
  packages: 'Paket',
  devices: 'Perangkat',
  members: 'Anggota',
  setup: 'Panduan',
  settings: 'Akun',
  login: 'Masuk',
  signup: 'Buat lokasi dan akun admin',
  logout: 'Keluar',
  back: 'Kembali',
  retry: 'Coba lagi',
  refresh: 'Muat ulang',
  loading: 'Memuat…',
  saving: 'Menyimpan…',
  mock: 'Demo · data simulasi',
  live: 'Mode live · integrasi belum tersedia',
  mockNote:
    'Akun, paket, foto, perangkat, dan notifikasi di sini adalah simulasi. Tidak terhubung ke perangkat atau layanan nyata.',
  admin: 'Admin',
  member: 'Anggota',
  denied: 'Halaman ini hanya untuk admin.',
  photo: 'Foto pengiriman',
  photoPending: 'Foto sedang diproses',
  photoUnavailable: 'Foto tidak tersedia',
  trackingPending: 'Memeriksa detail pelacakan',
  trackingUnavailable: 'Detail pelacakan tidak tersedia',
  photoReady: 'Foto tersedia',
  trackingReady: 'Pelacakan tersedia',
  scannedAt: 'Waktu pemindaian',
  trackingNumber: 'Nomor resi',
  courier: 'Kurir',
  error: 'Permintaan gagal. Silakan coba lagi.',
  unavailable:
    'Integrasi belum tersedia. Kontrak backend masih perlu disepakati.',
}
export function formatTime(value: string): string {
  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}
export function errorMessage(cause: unknown): string {
  return cause instanceof Error ? cause.message : ui.error
}
