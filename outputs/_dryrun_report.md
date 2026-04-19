# Dry-run Report — WORKFLOW_bertopic.md

**Run timestamp:** 2026-04-19
**Window:** 2025-08-01 → 2025-10-31
**Source:** xpoz MCP (`countTweets`)
**Decision:** **PROCEED** (total volume jauh di atas threshold abort=30)

## Volume per Query Pack

### Corpus A — MBG Umum (3 pack)

| Pack | Volume | Mode Fetch | Status |
|---|---|---|---|
| `mbg_umum_phrase`  | 263   | `fast` (1 call, limit=263) | OK |
| `mbg_umum_short`   | 4,996 | `csv` async                | high volume — "MBG" standalone, perlu filter post-fetch |
| `mbg_umum_context` | 5,194 | `csv` async                | high volume, kaya konteks |

**Total Corpus A (gross, sebelum dedupe):** ~10,453

### Corpus B — Food Tray MBG (6 pack)

| Pack | Volume | Mode Fetch | Status |
|---|---|---|---|
| `tray_umum_objek`    | 227 | `fast` (limit=227) | OK |
| `tray_suhu_basi`     | 14  | `fast`             | **THIN** (<15) — subset dari umum_objek |
| `tray_tumpah_tutup`  | 8   | `fast`             | **THIN** (<15) — subset dari umum_objek |
| `tray_material`      | 82  | `fast`             | OK |
| `tray_distribusi`    | 7   | `fast`             | **THIN** (<15) — subset dari umum_objek |
| `tray_higienitas`    | 47  | `fast`             | OK |

**Total Corpus B (gross):** ~385  •  **Estimasi unique setelah dedupe:** ~230

## Analisis & Catatan

1. **Corpus A** sangat kaya (>10K post). Issue ranking 5 isu MBG akan
   sangat reliable. CSV async ~30-60 detik per pack.
2. **Corpus B** hanya ~230 unique (umum_objek dominan). Ini di atas
   threshold `min_docs_required=30` BERTopic, tapi:
   - `min_topic_size=8` cocok (akan kasih ~5-8 topic)
   - kemungkinan banyak post jadi outlier `-1`
   - sentimen lexicon tetap reliable
3. **Pack tray thin** (suhu_basi, tumpah_tutup, distribusi) — tetap
   fetch, akan jadi subset post yang sudah ada di umum_objek setelah
   dedupe; gunanya untuk memastikan coverage isu spesifik.
4. **Risk noise di mbg_umum_short** ("MBG" alone): bisa hit konteks
   non-program (nama orang, singkatan lain). Diatasi di Step 5
   preprocessing (stemming + stopword) dan Step 6 issue ranking
   (post tanpa hit ke 5 isu = tidak masuk count).

## Keputusan Eksekusi

- **PROCEED ke Step 3-4** (fetch semua 9 pack)
- mbg_umum_short & mbg_umum_context → `responseType=csv` (async polling)
- Sisanya → `responseType=fast`
- Lanjut Step 5-17 setelah raw data tersimpan
