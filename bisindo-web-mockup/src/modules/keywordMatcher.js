/**
 * KeywordMatcher - NLU and Visual Assistance Cards
 * Identifies public service keywords from spoken Indonesian and maps them to high-contrast visual cards.
 */

export const PUBLIC_SERVICE_REGISTRY = [
  {
    keyword: 'obat',
    alias: ['obat', 'resep', 'farmasi', 'apotek', 'pil', 'kapsul'],
    title: 'Obat & Farmasi',
    category: 'Layanan Farmasi / Ambil Resep',
    iconEmoji: '💊',
    color: '#10B981',
    guidance: 'Silakan tunjukkan nomor antrean/resep obat ke loket farmasi. Tunggu panggilan visual di layar antrean.'
  },
  {
    keyword: 'dokter',
    alias: ['dokter', 'pemeriksaan', 'konsultasi', 'poli', 'medis'],
    title: 'Pemeriksaan Dokter',
    category: 'Pemeriksaan Medis & Ruang Poli',
    iconEmoji: '🩺',
    color: '#3B82F6',
    guidance: 'Silakan menuju ruang pemeriksaan dokter. Dokter akan memanggil nama atau nomor antrean Anda.'
  },
  {
    keyword: 'bayar',
    alias: ['bayar', 'kasir', 'tagihan', 'pembayaran', 'biaya', 'uang', 'qris'],
    title: 'Loket Pembayaran / Kasir',
    category: 'Kasir & Transaksi Keuangan',
    iconEmoji: '💳',
    color: '#F59E0B',
    guidance: 'Siapkan metode pembayaran (kartu debit, QRIS, atau uang tunai). Minta tanda bukti/struk pembayaran.'
  },
  {
    keyword: 'tolong',
    alias: ['tolong', 'bantu', 'bantuan', 'petugas', 'panduan'],
    title: 'Bantuan Petugas',
    category: 'Layanan Bantuan & Aksesibilitas',
    iconEmoji: '🆘',
    color: '#EF4444',
    guidance: 'Petugas layanan siap mendampingi Anda. Jangan ragu menunjuk atau meminta bantuan lebih lanjut.'
  },
  {
    keyword: 'sakit',
    alias: ['sakit', 'darurat', 'igd', 'luka', 'pusing', 'nyeri', 'sesak'],
    title: 'Kondisi Sakit / Darurat',
    category: 'Tanggap Darurat / Prioritas',
    iconEmoji: '🚨',
    color: '#EC4899',
    guidance: 'Jika mengalami kondisi darurat, Anda berhak mendapatkan jalur prioritas di unit gawat darurat (IGD).'
  },
  {
    keyword: 'terima kasih',
    alias: ['terima kasih', 'makasih', 'sama-sama', 'trims'],
    title: 'Terima Kasih',
    category: 'Salam & Penutup Interaksi',
    iconEmoji: '🙏',
    color: '#8B5CF6',
    guidance: 'Terima kasih atas interaksinya! Senang bisa berkomunikasi dengan Anda secara lancar.'
  },
  {
    keyword: 'halo',
    alias: ['halo', 'hai', 'selamat pagi', 'selamat siang', 'selamat sore', 'selamat malam', 'salam'],
    title: 'Sapaan & Sambutan',
    category: 'Awal Percakapan',
    iconEmoji: '👋',
    color: '#06B6D4',
    guidance: 'Selamat datang! Petugas siap melayani kebutuhan Anda dengan ramah dan terbuka.'
  }
];

export class KeywordMatcher {
  constructor() {
    this.registry = PUBLIC_SERVICE_REGISTRY;
  }

  /**
   * Match keywords from a spoken or typed sentence
   * @param {string} sentence
   * @returns {Array} List of matched card objects
   */
  match(sentence) {
    if (!sentence || typeof sentence !== 'string') return [];

    const lower = sentence.toLowerCase();
    const matched = [];

    for (const item of this.registry) {
      const isMatched = item.alias.some(aliasWord => {
        // Match word boundaries or substring
        const regex = new RegExp(`\\b${aliasWord}\\b`, 'i');
        return regex.test(lower) || lower.includes(aliasWord);
      });

      if (isMatched && !matched.some(m => m.keyword === item.keyword)) {
        matched.push(item);
      }
    }

    return matched;
  }

  /**
   * Get default cards to display when no text has been transcribed yet
   */
  getDefaults() {
    return [
      this.registry.find(r => r.keyword === 'obat'),
      this.registry.find(r => r.keyword === 'bayar'),
      this.registry.find(r => r.keyword === 'dokter'),
      this.registry.find(r => r.keyword === 'tolong')
    ].filter(Boolean);
  }
}
