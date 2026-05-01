# Workflow: MBG — Scrape X & Preprocess Only

> Versi ringkas dari `WORKFLOW.md`. Hanya fokus pada:
> 1. **Scraping** post X via MCP `user-xpoz` untuk keyword:
>    `mbg`, `makan bergizi gratis`, `program mbg`.
> 2. **Window**: 1 Agustus 2025 – 26 Maret 2026.
> 3. **Preprocessing** ringan (dedupe + clean text).
> 4. **Output tunggal CSV** dengan skema identik
>    `outputs/11_tray_manual_review.csv`.
>
> Tidak ada theme coding, tidak ada need statement, tidak ada report.md.

---

## 0. Kontrak Output

Hanya **1 file** wajib:

| File | Isi |
|------|-----|
| `outputs/scrape_mbg_manual_review.csv` | hasil scraping + preprocessing siap manual review |

Skema kolom (urut, identik `11_tray_manual_review.csv`):

```
tweet_id,
created_at,
author_username,
text_raw,
text_clean,
sentiment_label,
topic,
tweet_url,
manual_keep,
manual_topic_label,
manual_issue_category,
manual_design_implication,
manual_notes
```

Kolom `manual_*` ditulis kosong (string `""`) — diisi reviewer manual nanti.
Kolom `sentiment_label` juga ditulis kosong (`""`) — tidak dilakukan
analisis sentimen di workflow ini.
Kolom `topic` ditulis `0` (placeholder, sesuai contoh existing).

Opsional audit trail:

| File | Isi |
|------|-----|
| `outputs/_run_meta_just_get_data.json` | run_id, timestamp, total_raw, total_cleaned, xpoz_calls |

---

## 1. Prasyarat

1. MCP `user-xpoz` aktif → cek `checkAccessKeyStatus` harus
   `hasAccessKey: true`.
2. Direktori `outputs/` writable.
3. Python ringan (pandas, re) untuk dedupe + clean text.

---

## 2. Konfigurasi Inline (tidak perlu YAML)

```yaml
keywords:
  - "mbg"
  - "makan bergizi gratis"
  - "program mbg"

date_window:
  start: "2025-08-01"
  end:   "2026-03-26"

language: "id"
filter_out_retweets: true

# Engagement filter — longgarkan agar tidak buang post terlalu agresif.
# Set 0/0/0 kalau mau betul-betul "just get data" mentah.
min_likes:   0
min_replies: 0
min_reposts: 0
```

---

## 3. Langkah Eksekusi

### Step 1 — Verifikasi akses Xpoz

```
Call mcp__xpoz-mcp__checkAccessKeyStatus()
```
Pastikan `hasAccessKey == true`. Jika `Unauthorized` → stop, minta user
re-auth.

### Step 2 — Volume check per keyword (rekomendasi)

Untuk tiap `kw` di `keywords`:

```
Call mcp__xpoz-mcp__countTweets(
  phrase    = kw,
  startDate = "2025-08-01",
  endDate   = "2026-03-26",
  userPrompt= "Hitung volume post Bahasa Indonesia tentang MBG (Makan Bergizi Gratis) untuk keyword '<kw>' rentang Agustus 2025 - Maret 2026"
)
```
Simpan `estimated_count` per keyword → dipakai untuk pilih response mode.

### Step 3 — Fetch data per keyword

Untuk tiap `kw`:

1. **Pilih mode**:
   - `estimated_count <= 300` → `responseType="fast"`, `limit=300`
   - `estimated_count > 300`  → `responseType="csv"` (export penuh, async)

2. **Panggil fetcher**:
   ```
   Call mcp__xpoz-mcp__getTwitterPostsByKeywords(
     query              = kw,
     startDate          = "2025-08-01",
     endDate            = "2026-03-26",
     language           = "id",
     filterOutRetweets  = true,
     fields = [
       "id","text","authorUsername","authorId",
       "createdAt","createdAtDate",
       "likeCount","replyCount","retweetCount",
       "quoteCount","bookmarkCount","impressionCount",
       "lang","conversationId","hashtags","mentions"
     ],
     responseType = <fast|csv>,
     limit        = 300,   // hanya untuk fast
     userPrompt   = "Ambil semua post Bahasa Indonesia tentang MBG (Makan Bergizi Gratis) keyword '<kw>' Agustus 2025 - Maret 2026"
   )
   ```

3. **Handle async (csv mode)**:
   ```
   loop max 12x (sleep 5s):
     status = checkOperationStatus(operationId)
     if status in ("completed","failed","cancelled"): break
   ```
   Saat `completed` → download CSV dari `downloadUrl` → load ke df.

4. **Validasi tanggal**: drop row yang `createdAtDate` di luar
   `["2025-08-01","2026-03-26"]` (xpoz kadang buffer ±1 hari).

5. **Normalisasi kolom** ke skema internal:
   ```
   tweet_id        <- id
   created_at      <- createdAt
   author_username <- authorUsername
   text_raw        <- text
   like_count      <- likeCount
   reply_count     <- replyCount
   repost_count    <- retweetCount
   query_used      <- kw
   tweet_url       = f"https://x.com/{author_username}/status/{tweet_id}"
   ```

6. Tag `query_used = kw`. Concat semua keyword → `raw_df`.

### Step 4 — Dedupe + filter engagement

```python
df = raw_df.drop_duplicates(subset=["tweet_id"]).reset_index(drop=True)
df = df[
    (df.like_count   >= 0) &
    (df.reply_count  >= 0) &
    (df.repost_count >= 0)
]
```

(Threshold default 0 — longgar. Naikkan jika perlu.)

### Step 5 — Clean text

Regex identik notebook:
- lowercase
- hapus `http\S+|www\S+`
- hapus `@\w+`
- hapus simbol `#` (pertahankan kata)
- ganti `\n\r\t` → spasi
- hapus non-`[a-zA-Z0-9\s]`
- squeeze multi-space

Tambah kolom `text_clean`.

### Step 6 — Susun final CSV

```python
out = pd.DataFrame({
    "tweet_id":                df["tweet_id"].astype(str),
    "created_at":              df["created_at"],
    "author_username":         df["author_username"],
    "text_raw":                df["text_raw"],
    "text_clean":              df["text_clean"],
    "sentiment_label":         "",
    "topic":                   0,
    "tweet_url":               df["tweet_url"],
    "manual_keep":             "",
    "manual_topic_label":      "",
    "manual_issue_category":   "",
    "manual_design_implication":"",
    "manual_notes":            "",
})
out.to_csv("outputs/scrape_mbg_manual_review.csv", index=False)
```

### Step 7 — Tulis run meta (opsional)

```json
{
  "run_id": "<uuid4>",
  "timestamp_utc": "<ISO>",
  "window": {"start":"2025-08-01","end":"2026-03-26"},
  "keywords": ["mbg","makan bergizi gratis","program mbg"],
  "total_raw": N,
  "total_cleaned": N,
  "xpoz_calls": [
    {"tool":"getTwitterPostsByKeywords","keyword":"mbg","estimated_count":N,"response_type":"fast|csv"},
    ...
  ]
}
```
→ `outputs/_run_meta_just_get_data.json`.

---

## 4. Error Handling

| Situasi | Aksi |
|---|---|
| `countTweets` return 0 untuk semua keyword | Stop, lapor user |
| `checkOperationStatus` timeout >60s | Skip keyword tsb, catat di run_meta |
| xpoz `Unauthorized` | Stop, minta user re-auth OAuth |

---

## 5. Catatan

- **Jangan** pakai operator `from:` / `lang:` di dalam query string —
  xpoz strip; pakai parameter `language="id"`.
- **Jangan** pakai `forceLatest=true` (boros quota).
- **Selalu** isi `userPrompt` di tool call (membantu caching xpoz).
- Window 8 bulan (Agt 2025 – Mar 2026) cukup besar; siap-siap volume
  tinggi → kemungkinan besar semua keyword pakai `responseType="csv"`.

---

## 6. Quick-start prompt untuk agent

> Baca `WORKFLOW-just-get-data.md`. Jalankan Step 1–7. Keyword:
> `mbg`, `makan bergizi gratis`, `program mbg`. Window
> 2025-08-01 sampai 2026-03-26. Output tunggal:
> `outputs/scrape_mbg_manual_review.csv` dengan skema 13 kolom
> identik `11_tray_manual_review.csv` (kolom `sentiment_label` kosong).
> Di akhir tampilkan ringkasan: total_raw, total_cleaned, dan path
> file output.