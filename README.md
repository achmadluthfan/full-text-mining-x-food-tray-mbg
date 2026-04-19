# MBG Food Tray — X Text Mining (Xpoz MCP × BERTopic)

📊 **Manual Review Sheet (Google Sheets):** [11_tray_manual_review](https://docs.google.com/spreadsheets/d/1sYSsUQuixRdR9orTVQNXx9fQFQX-BHlyJSM-QIDXEL8/edit?usp=sharing)

Pipeline text mining **X/Twitter** untuk penelitian skripsi
"Redesign Food Tray MBG pada Sistem Distribusi SPPG".

Workflow ini **menggantikan** notebook manual
`mbg_x_full_text_mining_bertopic.ipynb` dengan pendekatan
**AI-executable playbook** yang memanfaatkan MCP server `user-xpoz`
untuk akuisisi data + analisis NLP/ML klasik (Sastrawi, lexicon,
BERTopic, n-gram, co-occurrence). **Tidak ada LLM** untuk klasifikasi
agar reproducible & defendable di sidang.

## Struktur

```
mbg/
├── WORKFLOW_bertopic.md       ← entry-point yang dibaca AI agent
├── DRYRUN.md                  ← playbook volume-check ringan (Step 0)
├── config/
│   ├── query_packs.yaml       general (3 pack) + tray (6 pack)
│   ├── keywords.yaml          STOPWORDS / POS-NEG WORDS / ISSUE_DICT / DESIGN_TERMS
│   ├── need_templates.yaml    rule-based mapping topic-keyword → need statement
│   └── thresholds.yaml        date window, BERTopic params, ngram, dst.
├── scripts/
│   ├── step1_consolidate.py   gabung CSV staging → 01/02_*_raw.csv
│   └── run_pipeline.py        Steps 5-17 (preprocess → BERTopic → report)
├── outputs/                   17 artefak (CSV, xlsx, report.md, _run_meta.json)
├── notebook_reference/        notebook asli (referensi metodologi)
└── outputs_old_llm_run/       backup hasil run lama (boleh dihapus)
```

## Cara pakai

Di Cursor / Claude Code, buka project lalu ketik:

> **"Jalankan dry-run MBG"** — cek volume per query pack (~2 menit, hemat quota).
> Lihat `outputs/_dryrun_report.md`.

> **"Jalankan workflow MBG"** — full pipeline (dry-run otomatis dulu,
> baru full fetch + analisis). Hasil akhir di `outputs/report.md` dan
> `outputs/mbg_x_foodtray_analysis.xlsx`.

Untuk menyesuaikan query / threshold / template need statement: edit
file yang relevan di `config/`, tidak perlu sentuh
`WORKFLOW_bertopic.md` maupun script.

## Prasyarat

1. MCP server `user-xpoz` aktif di Cursor. Verifikasi dengan memanggil
   tool `checkAccessKeyStatus` → `hasAccessKey: true`.
2. Python venv dengan dependencies: `pandas openpyxl pyyaml Sastrawi
   bertopic sentence-transformers umap-learn hdbscan scikit-learn
   tabulate` (lihat `WORKFLOW_bertopic.md` §1.4).

---

## ✅ Apa yang Perlu Dilakukan Setelah Pipeline Selesai

Pipeline menghasilkan 17 artefak otomatis di `outputs/`, tapi
**4 task riset masih perlu dikerjakan manual** untuk menjadikan ini
skripsi yang utuh dan dipertahankan di sidang.

### 1. 📝 Manual review (WAJIB) — `outputs/11_tray_manual_review.csv`

Anotasi minimal **30 baris** dari 121 yang tersedia. Kolom yang harus
diisi:

| Kolom | Isi |
|---|---|
| `manual_keep` | `ya` / `tidak` — apakah post valid dipakai |
| `manual_topic_label` | label topic versi peneliti (kalau berbeda dari BERTopic) |
| `manual_issue_category` | `material` / `suhu` / `distribusi` / `higienitas` / `kebocoran` |
| `manual_design_implication` | implikasi konkret untuk redesign tray |
| `manual_notes` | catatan bebas, alasan, kutipan menarik |

**Tip prioritas**: filter dulu yang `topic = 0` (88 tweets, topic
dominan); sisihkan ~10 dari topic 1 & 2 sebagai sampling minoritas.
Bisa di-upload ke Google Sheets untuk anotasi kolaboratif.

### 2. 🔧 Refine need statements — `outputs/10_tray_need_statements_draft.csv`

Topic 1 & 2 saat ini masih pakai `DEFAULT_NEED_STATEMENT` (terlalu
generik). Buka `outputs/09_tray_topic_representative_docs.csv`, baca 5
kutipan top per topic, lalu tulis ulang need statement spesifik di
kolom `manual_final_need_statement`.

### 3. 🔬 Turunkan need statement → spesifikasi teknis terukur

Terjemahkan tiap final need statement menjadi spec engineering:

| Need statement | Contoh spec teknis |
|---|---|
| "Memperlambat penurunan suhu" | Insulasi double-wall PP/SS, retensi suhu ≥60°C selama ≥2 jam |
| "Minimalkan kebocoran" | Tutup snap-fit silikon, leakproof rating IP-X4 |
| "Material aman pangan" | SS 304 / PP food-grade SNI 7322:2008 |
| "Mudah dibersihkan" | Permukaan halus tanpa sudut tajam, dishwasher-safe |

Biasanya jadi **Bab 4 / 5 skripsi** (analisis kebutuhan → spesifikasi
desain).

### 4. 🎨 Sintesis desain + expert validation

Buat **2 alternatif konsep tray** berbasis spec teknis di atas, lalu
validasi ke expert (dosen pembimbing, BGN/SPPG, ahli food packaging).
*Wajib untuk skripsi DKV / desain produk; opsional untuk skripsi riset
murni.*

---

## 🎓 Validasi Metodologi (untuk pertahanan sidang)

Sangat dianjurkan untuk memperkuat defendability:

- **Inter-rater reliability**: minta 1 reviewer lain anotasi ~30 baris
  yang sama, hitung Cohen's Kappa (κ ≥ 0.6 = substantial agreement).
- **Justifikasi pemilihan tools**: catat alasan pakai BERTopic vs LDA,
  Sastrawi vs IndoBERT, dst. (sering ditanya penguji).
- **Limitasi sample size**: 121 tweet preprocessed (Corpus B) di bawah
  ambang ideal BERTopic (~300+). Akui di Bab Limitasi + tambahkan
  triangulasi dengan literatur/benchmarking sebagai mitigasi.

---

## 📁 Housekeeping (opsional)

Jika repo akan di-publish atau di-share:

| Aksi | Manfaat |
|---|---|
| Hapus `outputs_old_llm_run/` | Hemat ruang, sudah di-backup git |
| Hapus / archive `WORKFLOW.md` lama (LLM-based) | Hindari kebingungan workflow mana yang dipakai |
| Hapus `prompts/01-04_*.md` | Sisa workflow LLM lama, tidak relevan |
| Hapus `outputs/_staging/` | Raw CSV download, sudah dikonsolidasi ke `01_general_raw.csv` & `02_tray_raw.csv` |

---

## Keunggulan vs notebook asli

| Aspek | Notebook manual | Workflow ini |
|---|---|---|
| Akuisisi data | X API v2 (bearer token, 7 hari rolling) | Xpoz MCP (OAuth, range historis eksplisit: Ags–Okt 2025) |
| Eksekusi | Manual per cell | Satu perintah ke AI agent |
| Reproducibility | Bergantung runtime Colab | `_run_meta.json` + `config_hash` + script versi |
| Konfigurasi | Hard-coded di cell | Terpisah di `config/*.yaml` |
| Output | Scattered di notebook | 17 artefak terstruktur + multi-sheet xlsx + report.md |
| Filosofi analisis | Sama (BERTopic, lexicon, n-gram) — full deterministik, no LLM |
