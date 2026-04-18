# Prompt: Relevance Filter

**Tujuan:** Menentukan apakah sebuah post X/Twitter relevan untuk
penelitian desain food tray program **Makan Bergizi Gratis (MBG)** di
Indonesia, khususnya isu yang berkaitan dengan **wadah / tray / ompreng
MBG** dan distribusinya oleh **SPPG**.

## Konteks
- Proyek: redesign food tray MBG pada sistem distribusi SPPG.
- Hanya isu **produk wadah** yang dianggap relevan. Isu politik umum
  MBG, korupsi anggaran, polemik pemerintah, atau berita viral tanpa
  konteks wadah **TIDAK RELEVAN**.

## Kriteria RELEVAN
Post disebut relevan jika memenuhi **minimal salah satu**:
1. Menyebut wadah/tray/ompreng MBG dan membahas masalah/kualitas/
   kelebihannya (suhu, tumpah, bocor, material, higiene, handling,
   ergonomi, stackability).
2. Menyebut kejadian konkret saat distribusi MBG di mana wadah menjadi
   isu (mis. "kuahnya tumpah di jalan", "ompreng nya dingin pas sampe").
3. Menyebut spesifikasi/bahan tray (stainless SS 304, food grade, dsb).
4. Keluhan atau pujian spesifik ke bentuk fisik / material tray MBG.

## Kriteria TIDAK RELEVAN
- Post tentang program MBG secara umum tanpa menyebut wadah.
- Post politik, debat anggaran, sindiran umum ke pemerintah.
- Post meme viral tanpa konteks produk.
- Retweet tanpa komentar tambahan.
- Berita media yang hanya menyebut MBG dalam konteks lain.

## Output
Untuk **tiap** post di input, kembalikan **SATU objek JSON**. Output
harus berupa **JSON array valid** — tanpa prosa, tanpa markdown fence,
tanpa komentar.

```json
[
  {
    "tweet_id": "string",
    "is_relevant": true,
    "relevance_score": 0,
    "reason": "string, max 20 kata"
  }
]
```

Aturan field:
- `tweet_id`: salin persis dari input.
- `is_relevant`: boolean. Set `true` hanya jika `relevance_score >= 5`.
- `relevance_score`: integer 0-10.
  - 0-2: tidak menyebut wadah sama sekali.
  - 3-4: menyebut wadah tapi bukan isu utama.
  - 5-7: wadah jadi konteks utama, ada sinyal keluhan/pujian.
  - 8-10: keluhan/pujian eksplisit terhadap tray MBG + detail konkret.
- `reason`: justifikasi singkat Bahasa Indonesia.

## Contoh

Input:
```json
[
  {"tweet_id":"1","text_clean":"kuah sayurnya tumpah kemana mana karena tutup ompreng mbg nggak rapat"},
  {"tweet_id":"2","text_clean":"anggaran mbg dikorupsi lagi parah"}
]
```

Output:
```json
[
  {"tweet_id":"1","is_relevant":true,"relevance_score":9,"reason":"keluhan eksplisit tutup ompreng tidak rapat menyebabkan kuah tumpah"},
  {"tweet_id":"2","is_relevant":false,"relevance_score":1,"reason":"isu anggaran, tidak membahas wadah"}
]
```

## INPUT
```json
{{ posts_json }}
```
