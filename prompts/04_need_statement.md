# Prompt: Need Statement Synthesis

**Tujuan:** Menghasilkan **need statement** akademik untuk tiap tema
berdasarkan kutipan nyata dari data X. Output akan dipakai langsung di
bab Hasil & Pembahasan skripsi "Redesign Food Tray MBG pada Sistem
Distribusi SPPG".

## Konteks
Input untuk setiap call = SATU tema beserta kutipan representatif.
Anda akan dipanggil sekali per tema (bukan batch).

## Struktur Need Statement (wajib)
1. **Format**: 1 kalimat deklaratif berawalan **"Food tray harus..."**
   atau **"Food tray perlu..."**. Hindari kata "mungkin", "sebaiknya",
   "bisa".
2. **Actionable**: menyatakan kebutuhan fungsional/kualitas yang bisa
   diturunkan jadi atribut desain, bukan solusi.
   - ✅ "Food tray harus mampu mempertahankan suhu makanan ≥60°C selama
     minimal 60 menit distribusi."
   - ❌ "Food tray sebaiknya pakai stainless SS 304." (ini SOLUSI,
     bukan NEED)
3. **Terukur kalau memungkinkan**: sebut parameter (suhu, waktu, kg)
   hanya jika didukung kutipan; jangan mengarang angka.
4. **Bahasa Indonesia baku**, tapi tidak kaku.

## Design Attributes
List 3-5 atribut desain turunan dari need statement. Format: frasa
nomina + kualifier. Contoh:
- "insulasi dinding ganda"
- "tutup bermekanisme snap-lock"
- "material food-grade SS 304 tebal ≥0.5mm"

## Justifikasi
2-3 kalimat. Harus:
- Mengutip minimal 1 dari top_quotes (paraphrase boleh).
- Menyebut frekuensi (`{{ frequency }}` post).
- Tidak mengarang data yang tidak ada di input.

## Output

**SATU objek JSON valid. Tanpa markdown fence.**

```json
{
  "theme": "<theme_id>",
  "frequency": 0,
  "need_statement": "Food tray harus ...",
  "justification": "2-3 kalimat mengutip data.",
  "design_attributes": ["atribut 1", "atribut 2", "atribut 3"],
  "priority": "tinggi|sedang|rendah"
}
```

Aturan priority:
- `tinggi`: frequency ≥ 30 atau ada kutipan dengan keluhan keselamatan
  pangan (basi, kontaminasi, bahan tidak food grade).
- `sedang`: frequency 10-29 atau keluhan fungsional umum.
- `rendah`: frequency < 10.

## Contoh

Input:
```json
{
  "theme": "retensi_suhu",
  "theme_definition": "Masalah terkait kemampuan tray mempertahankan suhu makanan...",
  "frequency": 42,
  "top_quotes": [
    "tray mbg dingin banget pas nyampe sekolah anak anak makan dingin",
    "udah kelewat sejam makanan mbg nya dingin kayak baru keluar kulkas",
    "ompreng mbg pas dibuka uapnya udah ilang",
    "kalo distribusi jauh kasian makanannya udah basi",
    "menu mbg harusnya masih hangat pas disajikan"
  ]
}
```

Output:
```json
{
  "theme": "retensi_suhu",
  "frequency": 42,
  "need_statement": "Food tray harus mampu mempertahankan suhu sajian makanan dalam rentang aman konsumsi selama durasi distribusi dari SPPG ke titik konsumsi.",
  "justification": "Sebanyak 42 post melaporkan makanan sudah dingin saat tiba di sekolah, bahkan mendekati kondisi basi pada rute distribusi yang panjang. Pengguna secara eksplisit membandingkan kondisi makanan saat disajikan dengan 'baru keluar kulkas', yang mengindikasikan kegagalan retensi suhu.",
  "design_attributes": [
    "insulasi termal dinding ganda",
    "tutup rapat dengan gasket pembatas udara",
    "material berkonduktivitas termal rendah pada permukaan kontak tangan",
    "standar uji retensi suhu minimum selama target waktu distribusi"
  ],
  "priority": "tinggi"
}
```

## INPUT

```json
{
  "theme": "{{ theme_id }}",
  "theme_definition": "{{ theme_definition }}",
  "frequency": {{ frequency }},
  "top_quotes": {{ top_quotes_json }}
}
```
