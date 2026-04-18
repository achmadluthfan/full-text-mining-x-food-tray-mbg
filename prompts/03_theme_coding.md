# Prompt: Theme Coding (Multi-label)

**Tujuan:** Memberi **label tema isu desain** ke tiap post. Multi-label
diperbolehkan (1 post bisa punya >1 tema).

## Daftar Tema TERTUTUP (ENUM)

Hanya 6 nilai berikut yang diperbolehkan. **Dilarang** mengarang tema
baru. Jika post tidak cocok tema mana pun → kembalikan `"themes": []`.

| theme_id | Definisi singkat |
|---|---|
| `retensi_suhu` | Isu suhu: makanan cepat dingin, panas tidak tahan, basi. |
| `kebocoran_tumpah` | Kuah bocor, tumpah, tutup tidak rapat. |
| `material_keamanan` | Material tray (stainless, food grade, karat, ketahanan). |
| `higienitas` | Kebersihan, sanitasi, potensi kontaminasi. |
| `handling_stackability` | Tumpuk, ikat, angkut, stabilitas saat distribusi. |
| `ergonomi_penggunaan` | Berat, susah dibuka/cuci/bawa, kenyamanan petugas & siswa. |

## Aturan Coding
1. **Multi-label**: jika post menyinggung >1 isu, berikan semua label
   yang relevan. Contoh: "kuahnya tumpah pas diikat rafia" →
   `["kebocoran_tumpah", "handling_stackability"]`.
2. **Minimal sinyal tekstual**: jangan memberi label kalau hanya
   asumsi. Harus ada kata/frasa anchor atau makna jelas.
3. **Jangan paksakan label**: lebih baik `[]` daripada salah label.
4. **Fokus ke wadah**, bukan ke makanan/programnya. Post "makanannya
   kurang enak" tanpa konteks wadah → `[]`.

## Keyword Anchor (Hint, bukan keharusan)

- retensi_suhu: dingin, panas, hangat, suhu, basi, cepat basi
- kebocoran_tumpah: tumpah, bocor, kuah, tutup, rapat, tidak rapat, ga rapat
- material_keamanan: stainless, ss 304, food grade, bahan, karat, plastik
- higienitas: higienis, sanitasi, kotor, bersih, kontaminasi, cuci
- handling_stackability: ikat, rafia, tumpuk, angkut, handling, stabil, jatuh
- ergonomi_penggunaan: berat, susah, ribet, nyaman, pegang, mudah dibawa

## Output

**JSON array valid. Tanpa markdown fence, tanpa prosa.**

```json
[
  {
    "tweet_id": "string",
    "themes": ["retensi_suhu", "kebocoran_tumpah"],
    "rationale": "max 20 kata"
  }
]
```

Validasi: setiap item `themes` HARUS termasuk salah satu dari 6 enum di
atas. Item di luar enum akan dibuang.

## Contoh

Input:
```json
[
  {"tweet_id":"201","text_clean":"tray mbg dingin banget pas nyampe sekolah anak anak makan dingin"},
  {"tweet_id":"202","text_clean":"petugas cape angkut ompreng ditumpuk 20 diikat rafia jatuh satu baris tadi"},
  {"tweet_id":"203","text_clean":"mbg itu makanan apa sih menunya"}
]
```

Output:
```json
[
  {"tweet_id":"201","themes":["retensi_suhu"],"rationale":"keluhan makanan dingin saat sampai sekolah"},
  {"tweet_id":"202","themes":["handling_stackability","ergonomi_penggunaan"],"rationale":"diikat rafia, tumpukan jatuh, beban petugas"},
  {"tweet_id":"203","themes":[],"rationale":"pertanyaan menu, bukan isu wadah"}
]
```

## INPUT
```json
{{ posts_json }}
```
