import { ServiceError } from '../services/contracts'

export const deliveryCopy = {
  backToList: 'Kembali ke daftar',
  listDescription: 'Lihat paket yang terdeteksi di lokasi penerimaan ini.',
  subtitlePullHint: 'Tarik ke bawah untuk memperbarui.',
  searchLabel: 'Cari paket',
  searchPlaceholder: 'Nomor resi atau kurir',
  searchClear: 'Hapus pencarian',
  noResultsTitle: 'Tidak ada paket yang cocok',
  noResultsDescription:
    'Coba kata kunci lain atau hapus pencarian untuk melihat semua paket.',
  listHeading: 'Pengiriman terbaru',
  summaryTitle: 'Ringkasan paket',
  summaryToday: 'Hari ini',
  summaryAllTime: 'Total keseluruhan',
  summaryUnit: 'paket',
  summaryLoading: 'Memuat ringkasan…',
  summaryLoadError: 'Ringkasan paket belum dapat dimuat.',
  summaryRetry: 'Coba muat ringkasan lagi',
  summaryDateHint: 'Hari ini mengikuti tanggal pada perangkat Anda.',
  listReloading: 'Memuat ulang…',
  pullHint: 'Tarik ke bawah untuk memperbarui',
  pullRelease: 'Lepaskan untuk memperbarui',
  pullRefreshing: 'Memperbarui paket…',
  listLoading: 'Memuat pengiriman',
  detailsLoading: 'Memuat rincian pengiriman',
  detailsRefreshing: 'Memperbarui rincian pengiriman…',
  detailsSection: 'Rincian paket',
  resourceAvailability: 'Ketersediaan informasi',
  resourcePhoto: 'Foto',
  resourceTracking: 'Pelacakan',
  deliveryCount: (count: number) =>
    `${new Intl.NumberFormat().format(count)} pengiriman`,
  emptyTitle: 'Belum ada pengiriman',
  emptyDescription:
    'Pengiriman akan muncul di sini setelah perangkat ESP32 memindai resi paket.',
  listLoadError:
    'Daftar pengiriman tidak dapat dimuat. Periksa koneksi lalu coba lagi.',
  listDenied: 'Anda tidak memiliki akses ke daftar pengiriman ini.',
  listMissing: 'Daftar pengiriman tidak tersedia saat ini.',
  detailTitle: 'Rincian pengiriman',
  detailLoadError:
    'Rincian pengiriman tidak dapat dimuat. Periksa koneksi lalu coba lagi.',
  detailDenied: 'Anda tidak memiliki akses ke pengiriman ini.',
  detailMissing: 'Pengiriman ini tidak ditemukan atau sudah tidak tersedia.',
  sessionExpired: 'Sesi berakhir. Silakan masuk kembali.',
  loadingMore: 'Memuat pengiriman berikutnya…',
  loadMore: 'Muat pengiriman berikutnya',
  retryList: 'Coba muat daftar lagi',
  retryDetails: 'Coba muat rincian lagi',
  retryMore: 'Coba lagi',
  openDetails: 'Buka rincian',
  unknownCourier: 'Kurir belum diketahui',
  trackingSection: 'Detail pelacakan',
  service: 'Layanan',
  carrierStatus: 'Status kurir',
  sender: 'Pengirim',
  recipient: 'Penerima',
  origin: 'Asal',
  destination: 'Tujuan',
  trackingHistory: 'Riwayat pelacakan',
  noTrackingFields: 'Belum ada detail tambahan dari kurir.',
  noTrackingEvents: 'Belum ada riwayat pelacakan.',
  photoLoadFailed: 'Foto tidak dapat dimuat. Periksa koneksi lalu coba lagi.',
  demoPhoto: 'Ilustrasi demo',
  retryPhoto: 'Coba muat foto lagi',
  loadingPhoto: 'Memuat foto pengiriman…',
  loadingTracking: 'Sedang memeriksa detail pelacakan.',
} as const

export type DeliveryRequestArea = 'list' | 'detail'

export function deliveryRequestStatus(cause: unknown): number {
  return cause instanceof ServiceError ? cause.status : 0
}

export function deliveryRequestError(
  cause: unknown,
  area: DeliveryRequestArea,
): string {
  const status = deliveryRequestStatus(cause)
  if (status === 401) return deliveryCopy.sessionExpired
  if (status === 403)
    return area === 'list' ? deliveryCopy.listDenied : deliveryCopy.detailDenied
  if (status === 404)
    return area === 'list'
      ? deliveryCopy.listMissing
      : deliveryCopy.detailMissing
  return area === 'list'
    ? deliveryCopy.listLoadError
    : deliveryCopy.detailLoadError
}

export function formatDeliveryTimestamp(value: string): string {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date)
}
