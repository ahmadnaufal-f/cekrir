export const serviceCopy = {
  invalidPath: 'Alamat API tidak valid.',
  nativeHttps: 'Aplikasi Android memerlukan alamat API HTTPS absolut.',
  connection: 'Tidak dapat menghubungi server. Periksa koneksi lalu coba lagi.',
  failed: 'Permintaan gagal. Coba lagi.',
  unavailable:
    'Integrasi rumah tangga belum tersedia. Kontrak backend masih perlu disepakati.',
  http: {
    401: 'Sesi berakhir. Silakan masuk lagi.',
    403: 'Anda tidak memiliki akses ke paket ini.',
    404: 'Paket tidak ditemukan.',
    409: 'Hanya satu ESP32 yang dapat didaftarkan.',
    422: 'Periksa isian formulir.',
    429: 'Terlalu banyak permintaan. Coba lagi nanti.',
  } as Record<number, string>,
}
