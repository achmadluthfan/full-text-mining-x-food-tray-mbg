# Metodologi Pengambilan Data

> **Konteks skripsi:** Bab III — Metodologi Penelitian, sub-bab Pengumpulan Data.
> Dokumen ini menjelaskan metode akuisisi data primer dari platform X (Twitter)
> untuk kebutuhan analisis kebutuhan (need analysis) redesign **food tray**
> Program Makan Bergizi Gratis (MBG) pada sistem distribusi SPPG.

---

## 3.1 Pendekatan dan Jenis Data

Penelitian ini menggunakan pendekatan **netnografi terstruktur** (Kozinets, 2015) dengan
data sekunder berupa percakapan publik di media sosial X (sebelumnya Twitter).
Jenis data yang dikumpulkan adalah **data tekstual unstructured** dalam Bahasa
Indonesia berisi opini, pengalaman, dan kritik masyarakat terhadap aspek
pewadahan (food tray / ompreng) program MBG.

Pemilihan media sosial X sebagai sumber didasarkan pada tiga pertimbangan:

1. **Ketersediaan suara publik tanpa perantara**: X memungkinkan pengguna
   menyuarakan keluhan / kepuasan secara spontan tanpa mediasi institusional,
   sehingga merepresentasikan *voice of customer* (VoC) yang relatif murni
   untuk analisis kebutuhan (Kotler & Keller, 2016).
2. **Volume data signifikan terkait isu MBG**: pelaksanaan MBG memicu diskusi
   masif di X selama periode penelitian, mencakup keluhan keracunan, masalah
   distribusi, dan secara spesifik isu wadah makanan (basi, tumpah, material).
3. **Kemudahan akses pemrograman**: X menyediakan API publik dan ekosistem
   layanan pihak ketiga yang memungkinkan pengumpulan data berskala besar
   secara reproducible.

---

## 3.2 Sumber dan Instrumen Pengumpulan Data

Pengumpulan data **tidak menggunakan** X API v2 langsung melainkan melalui
**Xpoz Twitter Data API** yang diakses sebagai *Model Context Protocol*
(MCP) server dalam lingkungan AI Agent (Cursor / Claude Code). Justifikasi
pemilihan Xpoz dibanding X API v2 native:

| Aspek | X API v2 (native) | Xpoz MCP (digunakan) |
|---|---|---|
| Akses historis | Hanya 7 hari (Essential tier) | Full historis dengan range eksplisit |
| Otentikasi | Bearer token (Academic Research access dibatasi) | OAuth standar (gratis untuk volume riset) |
| Format response | JSON streaming | JSON `fast` mode atau CSV `bulk` mode |
| Operator query | Standar Twitter (`from:`, `lang:`, `-is:retweet`) | Boolean eksplisit (AND/OR/NOT) + parameter terpisah |
| Integrasi pipeline | Manual | Native MCP — terintegrasi dengan AI agent untuk orkestrasi |

**Tools utama yang digunakan dari Xpoz MCP:**

| Tool | Fungsi | Penggunaan |
|---|---|---|
| `checkAccessKeyStatus` | Verifikasi otentikasi OAuth | Sebelum sesi fetching dimulai |
| `countTweets` | Estimasi volume per query (dry-run) | Step 0 — penentuan strategi response mode |
| `getTwitterPostsByKeywords` | Fetching post dengan filter waktu & bahasa | Step utama pengumpulan data |
| `checkOperationStatus` | Polling status async (mode CSV) | Saat estimasi volume > 300 post |

---

## 3.3 Populasi dan Teknik Sampling

**Populasi penelitian** adalah seluruh post (tweet) berbahasa Indonesia di X
yang membahas program MBG, khususnya aspek pewadahan, dalam periode
**1 Agustus – 31 Oktober 2025**.

**Teknik sampling** yang digunakan adalah **purposive keyword sampling**
melalui *query pack design*: peneliti merancang serangkaian kombinasi kata
kunci (query string boolean) yang secara spesifik menargetkan diskusi
food tray MBG dari berbagai sub-isu (suhu makanan, kebocoran, material,
distribusi, higienitas).

Sampling **tidak probabilistik** karena tidak mungkin menghitung sampling
frame yang utuh dari populasi tweet harian X. Implikasi: hasil penelitian
**tidak digeneralisasikan** secara statistik ke seluruh populasi pengguna
X, melainkan diinterpretasikan sebagai **eksplorasi insight kualitatif
yang didukung volume kuantitatif**.

---

## 3.4 Penentuan Window Waktu

Window pengumpulan data **ditetapkan secara eksplisit (fixed range)**
1 Agustus – 31 Oktober 2025 (3 bulan), dengan justifikasi:

1. **Awal periode (Agustus 2025)**: bertepatan dengan ekspansi nasional
   program MBG ke jenjang TK–SMA, yang memicu peningkatan volume diskusi
   publik signifikan di X.
2. **Akhir periode (Oktober 2025)**: mencakup beberapa kasus keracunan
   massal yang memicu sorotan terhadap aspek dapur, distribusi, dan
   pewadahan, sehingga insight terkait food tray menjadi rich.
3. **Durasi 3 bulan**: dianggap memadai untuk menangkap variasi musiman
   isu (back-to-school, awal tahun ajaran), tanpa menjadi terlalu lebar
   sehingga menghasilkan noise yang sulit di-handle.

Window dipassing eksplisit pada parameter `startDate="2025-08-01"` dan
`endDate="2025-10-31"` di setiap pemanggilan `getTwitterPostsByKeywords`
dan `countTweets` untuk menghindari default *rolling 60-day window* dari
Xpoz yang akan menghasilkan data berbeda bila workflow dieksekusi ulang.

---

## 3.5 Desain Query Pack

Untuk meminimalkan *miss rate* (post relevan yang tidak tertangkap karena
varian kata) sekaligus menghindari *over-fetching* yang membebani quota
API, peneliti merancang **6 query pack** terstruktur per sub-isu:

| ID Pack | Fokus | Pola Query (ringkas) |
|---|---|---|
| `umum_tray_mbg` | Coverage umum food tray + sinonim | `"food tray MBG" OR "tray MBG" OR "wadah MBG" OR "ompreng MBG"` |
| `isu_suhu` | Suhu makanan, basi | `<umum> AND (dingin OR panas OR suhu OR basi OR "cepat basi")` |
| `isu_kebocoran` | Tumpah, bocor, tutup tidak rapat | `<umum> AND (tumpah OR bocor OR tutup OR rapat OR kuah)` |
| `isu_material` | Material wadah | `<umum> AND (stainless OR "food grade" OR karat OR bahan)` |
| `isu_distribusi` | Penanganan distribusi | `<umum> AND (distribusi OR angkut OR ikat OR rafia OR tumpuk)` |
| `isu_higienitas` | Sanitasi, kebersihan | `<umum> AND (higienis OR sanitasi OR bersih OR kotor OR kontaminasi)` |

**Prinsip desain query pack:**

1. **Sinonim wajib dimasukkan** (food tray, tray, wadah, ompreng) — istilah
   "ompreng" sangat sering muncul di percakapan informal Indonesia dan akan
   missed jika hanya pakai "food tray".
2. **Operator boolean eksplisit** — Xpoz tidak meng-infer AND/OR seperti
   X API native, harus ditulis manual.
3. **Parameter `language="id"` dan `filterOutRetweets=true`** dipassing di
   level tool call (bukan dalam string query), karena Xpoz tidak mendukung
   operator `lang:id` atau `-is:retweet` dalam query.
4. **Tidak menggunakan `forceLatest=true`** untuk menghindari pemborosan
   quota API; data historis stabil sehingga cache layer Xpoz dapat
   dimanfaatkan.

Seluruh query pack didokumentasikan di file `config/query_packs.yaml`
sehingga reproducible (dapat dijalankan ulang dengan hasil yang sama
selama periode caching Xpoz).

---

## 3.6 Prosedur Pengumpulan Data (Step-by-step)

Pengumpulan data dijalankan dengan **alur dua tahap**: dry-run estimasi
volume → full fetching. Diagram alur ringkas:

```
[Dry-run countTweets per pack] → [Decision gate: proceed/abort]
        ↓                                    ↓
    estimasi volume                  abort jika volume terlalu rendah
        ↓
[Pilih response mode: fast (≤300) atau csv (>300)]
        ↓
[getTwitterPostsByKeywords per pack]
        ↓
[Async polling jika mode csv (max 60 detik)]
        ↓
[Validasi range tanggal → drop out-of-range]
        ↓
[Normalisasi kolom ke skema internal]
        ↓
[Concat semua pack → outputs/01_raw.csv]
```

### 3.6.1 Step 0 — Dry-run Estimasi Volume

Untuk setiap query pack, dilakukan pemanggilan `countTweets` dengan
parameter:

- `phrase` = query string pack
- `startDate` = "2025-08-01"
- `endDate` = "2025-10-31"

Output adalah perkiraan volume post yang akan didapat. Hasil disimpan ke
`outputs/_dryrun_meta.json` dan `outputs/_dryrun_report.md`.

**Aturan keputusan (decision gate):**

| Kondisi | Aksi |
|---|---|
| Total volume seluruh pack < 30 | **Abort** — sample terlalu kecil untuk analisis |
| Volume per pack 0 (semua pack) | **Abort** — query terlalu sempit, revisi keyword |
| Volume satu pack > 5000 | Wajib pakai `responseType="csv"` (tidak boleh fast) |
| Volume normal | **Proceed** ke Step 1 |

### 3.6.2 Step 1 — Fetching per Query Pack

Pemanggilan `getTwitterPostsByKeywords` dengan parameter standar:

```
query             = <query string pack>
startDate         = "2025-08-01"
endDate           = "2025-10-31"
language          = "id"
filterOutRetweets = true
responseType      = "fast" (≤300 post) | "csv" (>300 post)
limit             = 300 (untuk mode fast)
fields            = [id, text, authorUsername, authorId, createdAt,
                     likeCount, replyCount, retweetCount, quoteCount,
                     bookmarkCount, impressionCount, lang,
                     conversationId, hashtags, mentions]
```

**Mode response:**

- **`fast`**: hasil dikembalikan langsung sinkron, maksimal 300 post per call.
  Cocok untuk pack dengan volume kecil-menengah.
- **`csv`**: hasil di-export asynchronous; tool mengembalikan `operationId`
  yang harus di-poll via `checkOperationStatus` setiap 5 detik (max 12
  iterasi = 60 detik). Saat status `completed`, file CSV diunduh dari
  `downloadUrl` yang disediakan.

### 3.6.3 Step 2 — Validasi Tanggal & Normalisasi Kolom

**Validasi tanggal**: setiap post divalidasi `createdAtDate` ∈ [`2025-08-01`,
`2025-10-31`]. Post di luar range (kadang muncul ±1 hari karena perbedaan
zona waktu) di-drop.

**Normalisasi kolom** ke skema internal yang konsisten lintas pack:

| Kolom Xpoz | Kolom internal |
|---|---|
| `id` | `tweet_id` |
| `text` | `text_raw` |
| `authorUsername` | `author_username` |
| `createdAt` | `created_at` |
| `likeCount` | `like_count` |
| `retweetCount` | `repost_count` |
| `replyCount` | `reply_count` |
| `lang` | `lang` |
| (derived) | `tweet_url` = `https://x.com/{author_username}/status/{tweet_id}` |
| (added) | `query_label` = nama pack asal |
| (added) | `query_used` = query string yang dipakai |

Hasil seluruh pack di-concatenate menjadi satu DataFrame dan disimpan ke
`outputs/01_raw.csv`.

---

## 3.7 Pembersihan dan Filtering Awal

### 3.7.1 Deduplikasi

Karena query pack saling tumpang tindih (1 post bisa match >1 pack),
dilakukan deduplikasi global berdasarkan kolom `tweet_id`:

```python
df = raw_df.drop_duplicates(subset=["tweet_id"]).reset_index(drop=True)
```

Pack yang men-claim tweet pertama yang dipertahankan (`keep="first"`).

### 3.7.2 Filter Engagement (Optional Quality Gate)

Untuk menyaring noise berupa post tanpa interaksi sama sekali (kemungkinan
spam/bot), diterapkan threshold engagement minimum:

```python
df = df[
    (df.like_count   >= min_likes)    &
    (df.reply_count  >= min_replies)  &
    (df.repost_count >= min_reposts)
]
```

Threshold disimpan di `config/thresholds.yaml`. Untuk penelitian ini,
threshold di-set rendah (`min_likes=0`, `min_replies=0`, `min_reposts=0`)
**sehingga tidak ada post yang dibuang pada tahap ini** — pertimbangan:
post engagement rendah masih bisa berisi insight valid (misalnya keluhan
spesifik dari individu bukan opinion leader). Filtering content quality
dilakukan di Step 6 (filter relevansi).

Hasil disimpan ke `outputs/02_cleaned.csv`.

---

## 3.8 Validitas dan Reliabilitas Pengumpulan Data

### 3.8.1 Validitas Konstruk

Validitas dijamin dengan:

1. **Triangulasi keyword**: tiap sub-isu di-cover oleh ≥3 sinonim, divalidasi
   secara linguistik dengan referensi *kamus slang Twitter Bahasa Indonesia*
   (Tala, 2003) dan inspeksi manual sample post.
2. **Filter bahasa eksplisit** (`language="id"`) dan filter retweet
   (`filterOutRetweets=true`) untuk memastikan data adalah opini original
   berbahasa Indonesia, bukan amplifikasi (RT) atau diaspora berbahasa asing.
3. **Window waktu fixed range** (bukan rolling) menjamin reproducibility:
   workflow dapat dijalankan ulang kapan pun dan menghasilkan dataset
   identik (selama Xpoz mempertahankan caching).

### 3.8.2 Reliabilitas

Reliabilitas pengumpulan dijamin dengan:

1. **Versioning konfigurasi** via `config_hash` SHA-256 dari seluruh file
   YAML konfigurasi. Hash disimpan di `outputs/_run_meta.json` setiap run.
2. **Audit trail per call MCP**: setiap pemanggilan tool dicatat (timestamp,
   parameter, operation_id, jumlah hasil) di `_run_meta.json`.
3. **Backup raw data**: file `01_raw.csv` adalah snapshot mentah hasil
   fetching, di-versi-kan dan dapat di-replay tanpa perlu fetching ulang
   (penting untuk debugging tahap analisis tanpa boros quota API).

---

## 3.9 Etika Penelitian

Pengumpulan data tunduk pada prinsip etika riset media sosial (Townsend &
Wallace, 2016; AoIR, 2019):

1. **Hanya post publik** yang dikumpulkan; akun terkunci (private) tidak
   diakses (sudah di-handle Xpoz secara default).
2. **Anonimisasi pada pelaporan**: dalam laporan akhir (`outputs/report.md`
   dan dokumen skripsi), kutipan post tidak menyertakan `author_username`
   secara eksplisit kecuali untuk akun verified institusional (mis. media,
   pejabat). Jika kutipan akun individu dipakai, dilakukan parafrase atau
   penghapusan handle.
3. **Tidak ada interaksi dengan subjek**: data dikumpulkan secara observasi
   pasif (lurking), tidak ada balasan/DM/follow yang dilakukan oleh peneliti.
4. **Penyimpanan data terbatas waktu**: data raw disimpan hanya selama
   periode penelitian dan akan dihapus setelah skripsi disahkan, kecuali
   ada permintaan eksplisit dari komite etik untuk disimpan sebagai
   bukti audit.
5. **Tidak komersial**: data digunakan eksklusif untuk kepentingan
   akademik (skripsi), tidak diperjualbelikan atau diberikan ke pihak
   ketiga.

---

## 3.10 Limitasi Pengumpulan Data

Peneliti mengakui beberapa limitasi yang melekat pada metode ini:

1. **Bias platform**: pengguna X tidak merepresentasikan populasi umum
   Indonesia. Demografi X cenderung urban, terdidik, dan usia 18–35.
   Suara guru, petugas SPPG di daerah, atau orang tua siswa di area
   non-urban sangat mungkin under-represented.
2. **Bias kata kunci**: post yang membahas isu food tray tetapi tidak
   menggunakan keyword di query pack (misalnya pakai dialek lokal atau
   kiasan) tidak akan tertangkap.
3. **Bias temporal**: window 3 bulan kemungkinan over-representasi isu
   viral periode tersebut (kasus keracunan Lebong, Cipongkor, dll)
   dibanding isu chronic yang telah lama berjalan.
4. **Quota dan rate limit**: Xpoz API memiliki quota harian; pack dengan
   estimasi volume sangat besar (>10K) berpotensi terpotong di sample.
5. **Kontaminasi cross-issue**: post tentang MBG bisa mengandung diskusi
   campur (bukan murni food tray), sehingga butuh tahap filter relevansi
   lanjutan (LLM-based) sebelum analisis tematik.
6. **Tidak ada akses ke konten media** (gambar/video) yang sering
   menyertai post X — analisis hanya berbasis teks. Padahal foto food
   tray rusak/basi sangat informatif untuk redesign.

Limitasi ini dimitigasi dengan triangulasi pada bab pembahasan
(benchmarking produk komersial, expert judgement SPPG) dan dijabarkan
secara eksplisit di bab Limitasi Penelitian.

---

## 3.11 Ringkasan Output Tahap Pengumpulan Data

Output dari tahap pengumpulan data (sebelum tahap analisis):

| File | Deskripsi | Jumlah baris (estimasi) |
|---|---|---:|
| `outputs/_dryrun_report.md` | Laporan estimasi volume per pack | — |
| `outputs/_dryrun_meta.json` | Metadata dry-run terstruktur | — |
| `outputs/01_raw.csv` | Hasil mentah gabungan semua pack (sebelum dedupe) | sesuai volume |
| `outputs/02_cleaned.csv` | Setelah dedupe + filter engagement | ≤ 01_raw |
| `outputs/_run_meta.json` | Audit trail run (config_hash, timestamps, calls) | — |

Data hasil tahap ini menjadi **input untuk tahap analisis** (preprocessing
teks, filter relevansi, sentiment coding, theme coding, sintesis need
statement) yang dijelaskan pada sub-bab berikutnya (3.12 Metodologi
Analisis Data).

---

## Daftar Pustaka (referensi sub-bab pengumpulan data)

- Association of Internet Researchers (AoIR). (2019). *Internet Research:
  Ethical Guidelines 3.0*. Retrieved from https://aoir.org/ethics/
- Kotler, P., & Keller, K. L. (2016). *Marketing Management* (15th ed.).
  Pearson.
- Kozinets, R. V. (2015). *Netnography: Redefined* (2nd ed.). SAGE
  Publications.
- Tala, F. Z. (2003). *A study of stemming effects on information
  retrieval in Bahasa Indonesia*. M.Sc. Thesis, Universiteit van
  Amsterdam.
- Townsend, L., & Wallace, C. (2016). *Social Media Research: A Guide
  to Ethics*. University of Aberdeen.

---

## Lampiran A — Pseudocode Pipeline Pengumpulan Data

```python
# Step 0: Dry-run
for pack_label, query in query_packs.items():
    estimated[pack_label] = countTweets(
        phrase=query,
        startDate="2025-08-01",
        endDate="2025-10-31"
    )
if sum(estimated.values()) < MIN_TOTAL:
    abort("Volume terlalu kecil")

# Step 1: Fetching
raw_frames = []
for pack_label, query in query_packs.items():
    if estimated[pack_label] == 0:
        skip(pack_label)
    mode = "fast" if estimated[pack_label] <= 300 else "csv"
    response = getTwitterPostsByKeywords(
        query=query,
        startDate="2025-08-01",
        endDate="2025-10-31",
        language="id",
        filterOutRetweets=True,
        responseType=mode,
        limit=300 if mode == "fast" else None,
        fields=STANDARD_FIELDS,
    )
    if mode == "csv":
        operation_id = response["operationId"]
        for _ in range(12):
            sleep(5)
            status = checkOperationStatus(operation_id)
            if status.state == "completed":
                df = download_csv(status.downloadUrl)
                break
    else:
        df = parse_results(response.results)

    df = validate_date_range(df, "2025-08-01", "2025-10-31")
    df = normalize_columns(df, query_label=pack_label, query_used=query)
    raw_frames.append(df)

raw_df = concat(raw_frames)
raw_df.to_csv("outputs/01_raw.csv")

# Step 2: Dedupe + filter engagement
cleaned_df = (raw_df
              .drop_duplicates(subset=["tweet_id"])
              .query("like_count >= @min_likes")
              .query("reply_count >= @min_replies")
              .query("repost_count >= @min_reposts"))
cleaned_df.to_csv("outputs/02_cleaned.csv")
```

---

*Dokumen ini dibuat berdasarkan implementasi pipeline yang
terdokumentasi di `WORKFLOW.md` (root repository) dan dapat dijadikan
referensi langsung untuk Bab III Metodologi Penelitian skripsi.*
