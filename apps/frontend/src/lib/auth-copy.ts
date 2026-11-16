export const authCopy = {
  welcome: 'Selamat datang.',
  description:
    'Pantau paket yang dipindai di lokasi penerimaan dan bagikan aksesnya dengan anggota lain.',
  signupTitle: 'Siapkan lokasi penerimaan Anda.',
  signupDescription:
    'Buat akun admin untuk mengatur perangkat dan menambahkan anggota di lokasi ini.',
  loginId: 'Identitas masuk',
  password: 'Kata sandi',
  name: 'Nama Anda',
  email: 'Email',
  household: 'Nama lokasi penerimaan',
  householdHint: 'Contoh: rumah, kantor, atau toko.',
  loginHint: 'Gunakan akun yang dibuat admin untuk lokasi penerimaan ini.',
  adminHint: 'Belum mendaftarkan lokasi penerimaan?',
  existing: 'Sudah punya akun?',
  mockAccounts: import.meta.env.DEV
    ? 'Akun demo: admin@demo.test atau anggota · kata sandi demo1234. Data hanya disimpan selama sesi pengembangan.'
    : '',
  required: 'Lengkapi isian ini.',
  minPassword: 'Gunakan setidaknya 8 karakter.',
  emailInvalid: 'Masukkan alamat email yang valid.',
  prototype:
    'Isian akun adalah rancangan sementara sampai kontrak backend disepakati.',
}
