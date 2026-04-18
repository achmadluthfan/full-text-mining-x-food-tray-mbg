# MBG Food Tray — X Text Mining (Xpoz MCP Workflow)

Pipeline text mining **X/Twitter** untuk penelitian skripsi
"Redesign Food Tray MBG pada Sistem Distribusi SPPG".

Workflow ini **menggantikan** notebook manual
`mbg_x_text_mining_colab.ipynb` dengan pendekatan **AI-executable
playbook** yang memanfaatkan MCP server `user-xpoz` untuk akuisisi data
dan LLM untuk langkah judgemental (relevansi, sentimen, tema, need
statement).

## Struktur

```
mbg/
├── WORKFLOW.md                ← entry-point yang dibaca AI agent
├── DRYRUN.md                  ← playbook volume-check ringan (Step 0)
├── config/                    ← parameter terstruktur
│   ├── query_packs.yaml       6 query cluster untuk xpoz
│   ├── keywords.yaml          kamus TRAY/MBG/ISSUE/STOPWORDS
│   ├── theme_rules.yaml       definisi 6 tema + anchor keyword
│   └── thresholds.yaml        threshold numerik & batch size
├── prompts/                   ← prompt LLM terversi
│   ├── 01_relevance.md
│   ├── 02_sentiment.md
│   ├── 03_theme_coding.md
│   └── 04_need_statement.md
├── schemas/                   ← kontrak output
│   ├── coded_post.schema.json
│   └── theme_summary.schema.json
├── outputs/                   ← hasil run (CSV, report.md, run_meta.json)
├── mbg_x_text_mining_colab.ipynb   ← versi lama (referensi)
└── execute-script/            ← versi lama (referensi)
```

## Cara pakai

Di Cursor / Claude Code, cukup buka project dan ketik:

> **"Jalankan dry-run MBG"** — cek volume dulu (~2 menit, hemat quota).
> Lihat `outputs/_dryrun_report.md`.

> **"Jalankan workflow MBG"** — full pipeline (dry-run otomatis dulu,
> baru full fetch). Hasil akhir ada di `outputs/report.md`.

Untuk menyesuaikan query / threshold / definisi tema: edit file yang
relevan di `config/`, tidak perlu sentuh `WORKFLOW.md` maupun prompt.

## Prasyarat

1. MCP server `user-xpoz` aktif di Cursor. Verifikasi dengan memanggil
   tool `checkAccessKeyStatus` → `hasAccessKey: true`.
2. Tidak perlu bearer token X lagi (data dari xpoz).

## Keunggulan vs notebook

| Aspek | Notebook | Workflow ini |
|---|---|---|
| Akuisisi data | X API v2 (butuh bearer, 7 hari rolling) | Xpoz MCP (OAuth, range historis eksplisit: Ags–Okt 2025, multi-platform ready) |
| Relevansi | Keyword score | LLM + keyword fallback |
| Sentimen | Lexicon kata pos/neg | LLM 5-level Indonesia-aware (paham sarkasme & negasi) |
| Theme coding | Keyword substring | LLM multi-label berdasarkan definisi naratif |
| Need statement | Template statis | LLM sintesis dari kutipan nyata + design attributes |
| Eksekusi | Manual per cell | Satu perintah ke agent |
| Reproducibility | Bergantung runtime Colab | `run_meta.json` + `config_hash` + JSON schema |
