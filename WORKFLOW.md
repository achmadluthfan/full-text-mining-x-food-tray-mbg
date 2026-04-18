# Workflow: MBG Food Tray — X Text Mining via Xpoz MCP

> Playbook yang dieksekusi oleh AI agent (Cursor / Claude Code) untuk
> menggantikan notebook manual `mbg_x_text_mining_colab.ipynb`.
> Sumber data: **MCP server `user-xpoz`** (bukan X API v2 lagi).
> Semua langkah "judgemental" (relevansi, sentimen, tema, need statement)
> dikerjakan LLM; langkah deterministik (dedupe, regex, agregasi) tetap
> rule-based agar auditable.

---

## 0. Tujuan & Kontrak Output

Workflow ini HARUS menghasilkan 10 artefak dengan nama & kolom identik
dengan notebook, plus `report.md` naratif:

| # | File | Isi |
|---|------|-----|
| 01 | `outputs/01_raw.csv` | hasil mentah gabungan semua query pack |
| 02 | `outputs/02_cleaned.csv` | setelah dedupe + filter engagement |
| 03 | `outputs/03_relevant.csv` | lolos filter relevansi (LLM + fallback keyword) |
| 04 | `outputs/04_coded.csv` | setelah sentimen + theme coding |
| 05 | `outputs/05_theme_summary.csv` | frekuensi tiap tema |
| 06 | `outputs/06_top_words.csv` | top 50 kata dominan |
| 07 | `outputs/07_representative.csv` | 5 kutipan representatif per tema |
| 08 | `outputs/08_need_statements.csv` | 1 need statement per tema + justifikasi |
| 09 | `outputs/09_manual_review.csv` | sheet kosong untuk review manual |
| 10 | `outputs/report.md` | laporan naratif siap dipakai skripsi |
| meta | `outputs/_run_meta.json` | audit trail (run_id, timestamp, config hash) |

**Skema kolom tiap CSV wajib sesuai `schemas/*.schema.json`.**

---

## 1. Prasyarat

1. MCP server `user-xpoz` aktif. Verifikasi dengan memanggil
   `checkAccessKeyStatus` → harus return `hasAccessKey: true`.
2. File ini + `config/*.yaml` + `prompts/*.md` + `schemas/*.json` ada.
3. Direktori `outputs/` writable.
4. Agent mampu eksekusi Python ringan (pandas, pyyaml, openpyxl) untuk
   langkah deterministik. Tidak perlu X API bearer token.

---

## 2. Langkah Eksekusi

### Step 0 — Dry-run volume check (WAJIB kalau `auto_run_before_full: true`)

Sebelum full fetch, eksekusi playbook `DRYRUN.md` untuk memverifikasi
ketersediaan data & estimasi biaya.

**Aturan gate:**
- Jika `outputs/_dryrun_meta.json.decision == "abort"` → **STOP** full
  workflow, tampilkan `outputs/_dryrun_report.md` ke user, minta revisi
  query/window.
- Jika `decision == "proceed"` → lanjut Step 1, TAPI di Step 3 skip
  pack dengan status `empty` / `TIMEOUT` (baca dari
  `_dryrun_meta.json.volumes`).
- Jika user eksplisit bilang "**skip dry-run**" atau
  `config.dryrun.auto_run_before_full == false` → skip Step 0.

Dry-run hasil valid selama 24 jam — kalau `_dryrun_meta.json.timestamp`
< 24 jam dan config hash sama, boleh skip ulang dry-run.

### Step 1 — Load config

Baca dan simpan sebagai variabel kerja:
- `config/query_packs.yaml` → dict `{label: query_string}`
- `config/keywords.yaml` → dict `TRAY_TERMS, MBG_TERMS, ISSUE_TERMS, POSITIVE_WORDS, NEGATIVE_WORDS, STOPWORDS`
- `config/theme_rules.yaml` → dict `THEME_RULES, THEME_TO_NEED`
- `config/thresholds.yaml` → dict threshold & batch size

Hitung `config_hash = sha256(join_all_yaml)` → simpan untuk run_meta.

### Step 2 — Tentukan window waktu

**FIXED RANGE** — baca dari `config/thresholds.yaml`:
```
startDate = thresholds.date_window.start   # "2025-08-01"
endDate   = thresholds.date_window.end     # "2025-10-31"
```

**Wajib** pass `startDate` & `endDate` eksplisit ke setiap call
`getTwitterPostsByKeywords` dan `countTweets`. JANGAN pakai default
rolling 60-hari xpoz — data kita historis (Agustus–Oktober 2025) dan
kemungkinan besar di luar window rolling saat workflow dijalankan.

Override hanya jika user eksplisit minta range lain di prompt.

### Step 3 — Fetch per query pack

Untuk tiap `(label, query)` di query_packs:

1. **Sanity-check volume** (opsional tapi direkomendasikan):
   ```
   Call countTweets(
     phrase=<query>,
     startDate="2025-08-01",
     endDate="2025-10-31",
     userPrompt="Hitung volume post Bahasa Indonesia tentang food tray MBG untuk kategori <label> rentang Agustus-Oktober 2025"
   )
   ```
   Simpan hasil sebagai `estimated_count`.

2. **Pilih mode response**:
   - Jika `estimated_count <= 300` → `responseType="fast"`, `limit=300`
   - Jika `estimated_count > 300` → `responseType="csv"` (export penuh)

3. **Panggil fetcher**:
   ```
   Call getTwitterPostsByKeywords(
     query=<query>,
     startDate="2025-08-01",
     endDate="2025-10-31",
     language="id",
     filterOutRetweets=true,
     fields=[
       "id","text","authorUsername","authorId","createdAt","createdAtDate",
       "likeCount","replyCount","retweetCount","quoteCount","bookmarkCount",
       "impressionCount","lang","conversationId","hashtags","mentions"
     ],
     responseType=<fast|csv>,
     limit=300,                    // hanya untuk fast
     userPrompt="Ambil semua post Bahasa Indonesia yang membahas food tray MBG untuk kategori <label> rentang Agustus-Oktober 2025"
   )
   ```
   ⚠️ **Catatan integritas data:** setelah fetch selesai, validasi
   `createdAtDate` setiap row ada di dalam `["2025-08-01","2025-10-31"]`.
   Drop row di luar range (seharusnya tidak ada, tapi xpoz kadang
   mengembalikan buffer ±1 hari karena timezone).

4. **Handle async**:
   - Jika `responseType="csv"`: tool return `operationId`. Loop:
     ```
     while True:
       sleep(5)
       status = checkOperationStatus(operationId)
       if status in ("completed","failed","cancelled"): break
     ```
     Max 12 iterasi (60 detik). Saat `completed`, download CSV dari
     `downloadUrl` → muat ke dataframe.
   - Jika `responseType="fast"`: hasil ada di `results` langsung.

5. **Normalisasi kolom** ke skema internal:
   ```
   tweet_id        <- id
   created_at      <- createdAt
   author_username <- authorUsername
   author_id       <- authorId
   text_raw        <- text
   like_count      <- likeCount
   reply_count     <- replyCount
   repost_count    <- retweetCount
   quote_count     <- quoteCount
   bookmark_count  <- bookmarkCount
   lang            <- lang
   conversation_id <- conversationId
   query_used      <- query
   query_label     <- label
   tweet_url       = f"https://x.com/{author_username}/status/{tweet_id}"
   ```

6. Concat semua pack → `raw_df`. Tulis `outputs/01_raw.csv`.

### Step 4 — Dedupe + filter engagement

```python
df = raw_df.drop_duplicates(subset=["tweet_id"]).reset_index(drop=True)
df = df[
  (df.like_count   >= thresholds.min_likes)    &
  (df.reply_count  >= thresholds.min_replies)  &
  (df.repost_count >= thresholds.min_reposts)
]
```
Tulis `outputs/02_cleaned.csv`.

### Step 5 — Preprocessing teks (deterministik)

Regex `clean_text` identik notebook:
- lowercase
- hapus `http\S+|www\S+`
- hapus `@\w+`
- hapus simbol `#` (pertahankan kata)
- ganti `\n\r\t` dengan spasi
- hapus non-`[a-zA-Z0-9\s]`
- squeeze multi-space

Tambah kolom `text_clean`.

### Step 6 — Filter relevansi (LLM + fallback)

Bagi `df` jadi batch ukuran `thresholds.llm_batch_size` (default 20).
Untuk tiap batch:

1. Build prompt dari `prompts/01_relevance.md` dengan `{posts_json}`
   berisi list `{tweet_id, text_clean}`.
2. Minta LLM return JSON array:
   ```
   [{"tweet_id":"...","is_relevant":true,"relevance_score":0-10,"reason":"..."}]
   ```
3. Validasi JSON. Jika gagal parse 2x, **fallback** ke skor keyword notebook:
   ```
   score = 3*hit(TRAY_TERMS) + 3*hit(MBG_TERMS) + 1*hit(ISSUE_TERMS)
   is_relevant = score >= thresholds.relevance_score_min
   ```

Filter `is_relevant == true`. Tulis `outputs/03_relevant.csv`.

### Step 7 — Sentimen (LLM)

Batch 20, pakai `prompts/02_sentiment.md`. Output per post:
```
{"tweet_id":"...","sentiment_label":"sangat_positif|positif|netral|negatif|sangat_negatif",
 "sentiment_score":-2|-1|0|1|2, "rationale":"..."}
```
Validasi enum. Fallback lexicon jika LLM error (pos-neg dari
`keywords.yaml`).

### Step 8 — Theme coding (LLM)

Batch 20, pakai `prompts/03_theme_coding.md`. LLM HANYA boleh memetakan
ke tema yang didefinisikan di `theme_rules.yaml`. Return:
```
{"tweet_id":"...","themes":["retensi_suhu","kebocoran_tumpah"]}
```
Validasi: semua item `themes` harus ada di enum; drop unknown.
Post dengan `themes=[]` tidak masuk `coded_df`.

Merge hasil sentimen + theme ke `relevant_df` → `coded_df`.
Tulis `outputs/04_coded.csv`.

### Step 9 — Agregasi deterministik

1. **Theme summary**:
   ```python
   counter = Counter()
   for lst in coded_df.themes: counter.update(lst)
   theme_summary = DataFrame([{"theme":k,"count":v} for k,v in counter.items()])
                     .sort_values("count", ascending=False)
   ```
   → `outputs/05_theme_summary.csv`.

2. **Top words**:
   ```python
   def tokenize(t): return [w for w in t.split() if len(w)>2 and w not in STOPWORDS]
   tokens = [w for t in coded_df.text_clean for w in tokenize(t)]
   top_words = Counter(tokens).most_common(50)
   ```
   → `outputs/06_top_words.csv`.

3. **Representative posts per tema**:
   ```python
   rep_score = like_count + 2*reply_count + 2*repost_count + 3*relevance_score
   ```
   Untuk tiap tema ambil top 5 by `rep_score`. Concat.
   → `outputs/07_representative.csv`.

### Step 10 — Need statements (LLM)

Untuk tiap tema di `theme_summary`, kirim ke LLM dengan
`prompts/04_need_statement.md`:
- `theme_id`
- `theme_definition` (dari `theme_rules.yaml`)
- `frequency`
- `top_quotes` (5 kutipan representatif)

LLM return:
```
{
  "theme": "...",
  "frequency": 42,
  "need_statement": "Food tray harus ...",
  "justification": "Berdasarkan ... (2-3 kalimat)",
  "design_attributes": ["atribut 1", "atribut 2", "atribut 3"]
}
```
→ `outputs/08_need_statements.csv` (`design_attributes` di-serialize
JSON string agar compat CSV).

### Step 11 — Manual review sheet

```python
review_cols = ["tweet_id","created_at","author_username","text_raw",
  "text_clean","relevance_score","sentiment_label","themes","tweet_url"]
manual = coded_df[review_cols].copy()
for c in ["manual_keep","manual_sentiment","manual_theme_1",
          "manual_theme_2","manual_notes"]:
    manual[c] = ""
```
→ `outputs/09_manual_review.csv`.

### Step 12 — Report naratif `outputs/report.md`

Struktur wajib:
```markdown
# Laporan Text Mining X — Food Tray MBG
**Run ID:** <uuid>   **Periode:** 1 Agustus – 31 Oktober 2025   **Total relevant:** N

## 1. Ringkasan Eksekutif
<3-5 kalimat: temuan utama, 3 need statement prioritas>

## 2. Metodologi Singkat
- Sumber: Xpoz (Twitter/X), query packs: <list label>
- Dedupe, filter engagement (likes>=X, dst)
- Relevansi, sentimen, theme coding: LLM <model>
- Need statement: LLM sintesis dari 5 kutipan representatif

## 3. Distribusi Sentimen
<markdown table: label | count | pct>

## 4. Distribusi Tema
<markdown table: theme | count | pct>

## 5. Need Statements Prioritas
<per tema: statement + justifikasi + 2 kutipan bukti + atribut desain>

## 6. Limitasi
- Window 60 hari
- Bias platform X (tidak mewakili non-online SPPG)
- LLM dapat halusinasi; tetap review manual (lihat 09_manual_review.csv)

## 7. Next Step
<gabungkan dengan benchmarking, turunkan atribut → spesifikasi desain>
```

### Step 13 — Write `outputs/_run_meta.json`

```json
{
  "run_id": "<uuid4>",
  "timestamp_utc": "<ISO>",
  "window": {"start":"2025-08-01","end":"2025-10-31"},
  "query_packs": ["umum_tray_mbg","isu_suhu",...],
  "total_raw": N,
  "total_cleaned": N,
  "total_relevant": N,
  "total_coded": N,
  "llm_model": "<model name>",
  "config_hash": "<sha256>",
  "xpoz_calls": [{"tool":"getTwitterPostsByKeywords","label":"...","estimated_count":N,"response_type":"fast|csv"}]
}
```

---

## 3. Error Handling

| Situasi | Aksi |
|---|---|
| `countTweets` return 0 untuk semua pack | Abort, laporkan ke user — query terlalu sempit atau tidak ada data |
| `checkOperationStatus` timeout (>60s) | Batalkan pack tersebut, lanjut ke pack berikutnya, catat di run_meta |
| LLM return JSON invalid | Retry 1x dengan suffix "OUTPUT WAJIB JSON VALID TANPA MARKDOWN"; jika masih gagal → fallback lexicon |
| `total_relevant < 10` | Warn user: sample terlalu kecil untuk analisis tematik; sarankan perluas window / query |
| xpoz `Unauthorized` | Stop, instruksikan user re-auth via OAuth |

---

## 4. Batasan & Best Practice

- **Jangan** pakai `forceLatest=true` kecuali user eksplisit minta
  "real-time" — boros quota.
- **Jangan** pakai `from:` / `lang:` di dalam query string — xpoz strip
  operator itu. Pakai parameter dedikasi `authorUsername` / `language`.
- **Selalu** isi `userPrompt` di tool call — meningkatkan relevansi
  caching xpoz.
- **Selalu** simpan `operationId` di log untuk audit.
- **Batch LLM 20 post** sweet spot untuk bahasa Indonesia (context ~3-4k
  token, latency wajar).
- Untuk skripsi: **sertakan manual review** di bab hasil agar klaim
  akademik lebih kuat. LLM bukan oracle.

---

## 5. Quick-start prompt untuk agent

Kalau user bilang "jalankan workflow MBG", agent cukup eksekusi:

> Baca `WORKFLOW.md`. Load semua file di `config/`. Jalankan Step 1-13
> berurutan. Update todo list tiap step selesai. Di akhir, tampilkan
> ringkasan: total_relevant, 3 tema teratas, 3 need statement prioritas,
> dan link ke `outputs/report.md`.
