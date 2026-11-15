export const authCopy = {
  welcome: 'Selamat datang di rumah.',
  description:
    'Lihat paket yang dipindai di rumah Anda, bersama seluruh anggota rumah tangga.',
  signupTitle: 'Mulai dari rumah Anda.',
  signupDescription:
    'Buat akun admin untuk menyiapkan perangkat dan menambahkan anggota.',
  loginId: 'Identitas masuk',
  password: 'Kata sandi',
  name: 'Nama Anda',
  email: 'Email',
  household: 'Nama rumah tangga',
  loginHint: 'Gunakan akun yang dibuat admin rumah tangga Anda.',
  adminHint: 'Belum punya rumah tangga?',
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
