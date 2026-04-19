# Dry-Run Report — 2026-04-17T16:00:00Z
**Range:** 2025-08-01 → 2025-10-31  
**Total volume (sum, dengan overlap):** 80 post  
**Status:** ⚠️ **PROCEED WITH CAUTION**

## Volume per Query Pack

| Pack | Count | Status | Catatan |
|---|---:|:---:|---|
| `umum_tray_mbg` | 49 | 🟢 ok | Base pack sehat, dominan di dataset. |
| `isu_suhu` | 2 | 🟡 thin | Data sangat tipis; isu suhu kemungkinan terwakili di `umum_tray_mbg` tapi tanpa label eksplisit. |
| `isu_tumpah_tutup` | 0 | 🔴 empty | Tidak ada post yang match — query kemungkinan terlalu sempit (AND tray + AND tumpah/bocor/tutup/rapat/kuah). |
| `isu_material` | 27 | 🟢 ok | Pack ke-2 terbesar. Diskusi material stainless/food-grade cukup terdokumentasi. |
| `isu_distribusi` | 0 | 🔴 empty | Tidak ada post match — istilah "distribusi/angkut/ikat/rafia/tumpuk/handling" jarang muncul bersamaan dengan istilah tray. |
| `isu_higiene` | 2 | 🟡 thin | Data sangat tipis. |

**Distribusi pack:** 2 🟢 ok · 2 🟡 thin · 2 🔴 empty · 0 🔵 large

⚠️ **Overlap besar:** pack `isu_*` adalah subset dari `umum_tray_mbg`
(semua mensyaratkan frasa tray + filter tambahan). Unik post setelah
dedupe kemungkinan ~**50 ± 5** (bukan 80).

## Estimasi Beban Full Run

| Item | Estimasi |
|---|---:|
| MCP fetch calls (`getTwitterPostsByKeywords`) | 4 (pack non-empty) |
| Mode fetch | semua `fast` (limit=300) — tidak perlu async polling |
| Total post ter-fetch (dengan overlap) | ~80 |
| Total post unik setelah dedupe | ~50 |
| Batch LLM (relevance + sentiment + theme_coding) | ~6 call total (~2-3 per tahap, batch 20) |
| Batch LLM need_statement | 6 (1 per tema, tapi banyak yang akan skip karena tema kosong) |

Biaya total workflow penuh: **rendah** (< $0.50 LLM + sekitar 10 xpoz calls).

## Gate Keputusan

| Kriteria | Nilai | Threshold | Status |
|---|---:|---:|:---:|
| `total_volume >= abort_if_total_below` | 80 | 30 | ✅ lolos |
| `min_relevant_rows_for_report` (estimasi) | ~50 × 60% relevance ≈ 30 | 10 | ✅ lolos |

**Keputusan:** **PROCEED** — cukup data untuk analisis tematik, tapi
expect hasil yang didominasi 2 tema (`material_keamanan` + tema-tema
yang muncul di `umum_tray_mbg`).

## Rekomendasi (sebelum full run)

### 🔴 Wajib: tangani 2 pack empty

Karena `isu_tumpah_tutup` dan `isu_distribusi` menghasilkan 0 post,
query mereka terlalu restriktif (AND dengan base tray yang sama).
Opsi:

1. **Skip** kedua pack di full run — biarkan LLM theme-coding yang
   mengangkat isu tumpah/distribusi dari pack `umum_tray_mbg`.
   Ini paling aman dan direkomendasikan.
2. **Loosen** query — hapus AND dengan base tray, pakai frasa MBG
   langsung (mis. `"MBG" AND (tumpah OR bocor OR kuah)`) — tapi akan
   banyak false positive yang tidak membahas wadah.
3. **Perluas synonym**: tambah "nampan", "container makanan", "bungkus
   MBG" di base tray.

### 🟡 Pertimbangan: pack thin (`isu_suhu`, `isu_higiene`)

Dengan hanya 2 post masing-masing, mereka **tidak meaningful** sebagai
pack terpisah. Rekomendasi: **skip**, biarkan isu ini di-capture via
`umum_tray_mbg` + theme coding LLM. Kalau LLM tidak menemukan
retensi_suhu / higienitas di `umum_tray_mbg`, berarti memang tidak ada
diskusi signifikan di window ini.

### 🟢 Optimisasi full run

Dengan rekomendasi di atas, full run efektif cuma 2 pack:

- `umum_tray_mbg` (49 post)
- `isu_material` (27 post)

Estimasi setelah dedupe: ~50 unik post. Lebih cepat & hemat quota.

### 📊 Opsional: perluas window

Kalau Anda ingin lebih banyak data untuk tema suhu/tumpah/higiene:

- Perluas ke **Juli 2025 – November 2025** (tambahan 2 bulan)
- Atau gabungkan dengan **Reddit** via `getRedditPostsByKeywords` —
  komunitas r/indonesia / r/indonesian kadang bahas MBG dengan lebih
  detail

## Query yang Perlu Revisi

### `isu_tumpah_tutup` (0 hit)
```
(("food tray MBG" OR "tray MBG" OR "ompreng MBG" OR "wadah MBG") AND (tumpah OR bocor OR tutup OR rapat OR kuah))
```
**Saran revisi:**
```
("ompreng MBG" OR "tray MBG" OR "wadah MBG" OR "makanan MBG") AND (tumpah OR bocor OR kuah OR "tutup kebuka")
```

### `isu_distribusi` (0 hit)
```
(("food tray MBG" OR "tray MBG" OR "ompreng MBG") AND (distribusi OR angkut OR ikat OR rafia OR tumpuk OR handling))
```
**Saran revisi:**
```
("MBG" OR "makan bergizi gratis") AND (ikat OR rafia OR tumpuk OR angkut) AND (tray OR ompreng OR wadah OR makanan OR ransum)
```

## Meta

- Semua call `countTweets` sukses, 0 error/timeout
- Dry-run cache valid sampai: 2026-04-18T16:00:00Z (24 jam)
- File meta: `outputs/_dryrun_meta.json`
