export const deviceGuideCopy = {
  common: {
    adminOnly: 'Panduan perangkat hanya tersedia untuk admin lokasi ini.',
    loading: 'Memuat referensi panduan…',
    loadingFailed: 'Referensi panduan belum dapat dimuat.',
    retry: 'Coba lagi',
    linkUnavailable: 'Tautan referensi yang disetujui belum tersedia.',
    externalLinkNote: 'Tautan dibuka di browser eksternal.',
  },
  esp32: {
    title: 'Petunjuk penyiapan ESP32',
    disclosure: 'Buka petunjuk penyiapan ESP32',
    description:
      'Daftarkan perangkat di sini, lalu gunakan sumber dan README untuk konfigurasi manual dan pengujian perangkat.',
    steps: [
      'Daftarkan ESP32 dengan nama yang mudah dikenali menggunakan formulir di bawah.',
      'Setelah berhasil, salin kredensial yang ditampilkan satu kali sebelum menutup atau meninggalkan layar.',
      'Buka sumber firmware dan README untuk langkah konfigurasi manual serta pengujian hardware.',
    ],
    scaffoldNote:
      'Panduan firmware masih berupa scaffold. Konfigurasi dan koneksi perangkat belum diverifikasi. Aplikasi ini tidak memasang firmware; penggunaan kredensial perangkat masih menunggu kesepakatan integrasi.',
    sourceLink: 'Lihat sumber firmware',
    guideLink: 'Baca panduan ESP32',
  },
  bardi: {
    title: 'Petunjuk kamera BARDI',
    disclosure: 'Baca petunjuk kamera BARDI',
    description:
      'Daftarkan nama kamera, lalu pilih kamera yang akan dipakai untuk paket.',
    steps: [
      'Alamat RTSP dan kredensial bersifat opsional pada formulir. Informasi koneksi hanya dikirim saat disimpan dan tidak ditampilkan kembali.',
      'Pilih satu kamera sebagai kamera pengiriman setelah kamera terdaftar.',
      'Pastikan model kamera mendukung akses yang Anda perlukan melalui dokumentasi resmi untuk model tersebut.',
    ],
    pending:
      'Panduan BARDI masih menunggu validasi lokal. Alamat RTSP, kredensial, dan keberhasilan koneksi belum dikonfirmasi; jangan mengandalkan nilai bawaan.',
    guideLink: 'Buka referensi BARDI',
  },
} as const
