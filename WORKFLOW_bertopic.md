# Workflow: MBG Food Tray — X Text Mining via Xpoz MCP

> Playbook AI agent (Cursor / Claude Code) untuk mereplikasi notebook
> `mbg_x_full_archive_food_tray_colab (2).ipynb` dengan sumber data
> **MCP server `user-xpoz`** (bukan X API v2 full-archive bearer token).
>
> Filosofi analisis mengikuti notebook:
> **deduktif (issue ranking, lexicon sentiment) + induktif (BERTopic,
> n-gram, co-occurrence)**. LLM **tidak** dipakai untuk klasifikasi —
> semua tahap analisis tematik berbasis statistik / ML klasik agar
> reproducible dan defendable di sidang.

---

## 0. Tujuan & Kontrak Output

Workflow ini menghasilkan **2 corpus paralel**:

| Corpus | Cakupan | Pertanyaan yang Dijawab |
|---|---|---|
| **A — MBG Umum** | semua isu MBG (menu, dapur, regulasi, distribusi, food tray, dst.) | "Posisi/rank isu food tray di antara isu MBG lainnya?" |
| **B — Food Tray MBG** | hanya post tentang wadah/ompreng/tray MBG | "Voice of customer spesifik wadah → need statement untuk redesign" |

### Artefak wajib

| # | File | Isi |
|---|------|-----|
| 00 | `outputs/00_general_query_stats.csv` | volume per query pack Corpus A |
| 00 | `outputs/00_tray_query_stats.csv` | volume per query pack Corpus B |
| 01 | `outputs/01_general_raw.csv` | data mentah Corpus A (gabungan + dedupe) |
| 02 | `outputs/02_tray_raw.csv` | data mentah Corpus B (gabungan + dedupe) |
| 03 | `outputs/03_general_preprocessed.csv` | Corpus A setelah clean+stem |
| 04 | `outputs/04_tray_preprocessed.csv` | Corpus B setelah clean+stem |
| 05 | `outputs/05_issue_ranking_general.csv` | rank 5 isu MBG di Corpus A |
| 06 | `outputs/06_general_top_words.csv` | top 100 kata Corpus A |
| 07 | `outputs/07_tray_sentiment_summary.csv` | distribusi sentimen Corpus B |
| 08 | `outputs/08_tray_topic_info.csv` | hasil BERTopic Corpus B |
| 09 | `outputs/09_tray_topic_representative_docs.csv` | 5 kutipan top per topic |
| 10 | `outputs/10_tray_need_statements_draft.csv` | draft need statement per topic |
| 11 | `outputs/11_tray_manual_review.csv` | sheet review manual |
| 12 | `outputs/12_general_top_bigrams.csv` | top 30 bigram Corpus A |
| 13 | `outputs/13_tray_top_bigrams.csv` | top 30 bigram Corpus B |
| 14 | `outputs/14_tray_top_trigrams.csv` | top 30 trigram Corpus B |
| 15 | `outputs/15_tray_cooccurrence_pairs.csv` | top 30 pair co-occurrence (auto vocab) |
| 16 | `outputs/16_tray_design_cooccurrence_pairs.csv` | co-occurrence terbatas pada `DESIGN_TERMS` |
| xlsx | `outputs/mbg_x_foodtray_analysis.xlsx` | semua di atas dalam multi-sheet |
| md | `outputs/report.md` | laporan naratif siap-pakai untuk skripsi |
| meta | `outputs/_run_meta.json` | audit trail (run_id, config_hash, volume per pack) |

---

## 1. Prasyarat

1. **MCP server `user-xpoz` aktif.** Verifikasi via `checkAccessKeyStatus`
   → harus return `hasAccessKey: true`.
2. File konfigurasi tersedia:
   - `config/query_packs.yaml` (struktur `general:` dan `tray:` — lihat Step 1)
   - `config/keywords.yaml` (`STOPWORDS`, `POSITIVE_WORDS`, `NEGATIVE_WORDS`,
     `ISSUE_DICT`, `DESIGN_TERMS`)
   - `config/need_templates.yaml` (mapping topic-keyword → draft kalimat,
     mengganti `theme_rules.yaml` lama)
   - `config/thresholds.yaml` (date window, BERTopic params, dst.)
3. Direktori `outputs/` writable.
4. Dependensi Python (akan di-install agent sekali di awal):
   ```
   pandas openpyxl pyyaml matplotlib tqdm
   Sastrawi
   bertopic sentence-transformers umap-learn hdbscan scikit-learn
   ```
   Catatan: BERTopic + sentence-transformers butuh download model
   (~400MB, sekali saja). Pakai model multilingual default.

---

## 2. Langkah Eksekusi

### Step 0 — Dry-run volume check (WAJIB jika `auto_run_before_full: true`)

Sebelum full fetch, eksekusi `DRYRUN.md` untuk verifikasi ketersediaan
data + estimasi biaya call MCP.

**Aturan gate:**
- `decision == "abort"` → **STOP**, tampilkan `outputs/_dryrun_report.md`,
  minta user revisi query atau perluas window.
- `decision == "proceed"` → lanjut Step 1; pack dengan status `empty`
  atau `TIMEOUT` di-skip (catat di `run_meta.skipped_packs`).
- User eksplisit bilang "**skip dry-run**" atau
  `config.dryrun.auto_run_before_full == false` → langsung Step 1.

Hasil dry-run valid 24 jam selama `config_hash` tidak berubah.

### Step 1 — Load konfigurasi

Baca semua YAML di `config/`:

```yaml
# config/query_packs.yaml — struktur baru: 2 corpus
general:
  mbg_umum_phrase:  '"makan bergizi gratis"'
  mbg_umum_short:   'MBG'
  mbg_umum_context: '(MBG OR "makan bergizi gratis" OR SPPG OR "program makan bergizi gratis")'

tray:
  tray_umum_objek:    '<OBJECT_BASE>'
  tray_suhu_basi:     '<OBJECT_BASE> AND (dingin OR panas OR hangat OR suhu OR basi OR "cepat basi")'
  tray_tumpah_tutup:  '<OBJECT_BASE> AND (tumpah OR bocor OR tutup OR rapat OR kuah)'
  tray_material:      '<OBJECT_BASE> AND (stainless OR "ss 304" OR "food grade" OR karat OR "anti karat" OR bahan)'
  tray_distribusi:    '<OBJECT_BASE> AND (distribusi OR angkut OR ikat OR diikat OR rafia OR rapia OR tali OR tumpuk OR handling)'
  tray_higienitas:    '<OBJECT_BASE> AND (higienis OR sanitasi OR bersih OR kotor OR kontaminasi OR cuci OR kering)'

# OBJECT_BASE direkat di Python sebelum pemanggilan MCP:
# (("food tray MBG" OR "tray MBG" OR "wadah MBG" OR "tempat makan MBG" OR "ompreng MBG")
#  OR (ompreng AND (MBG OR "makan bergizi gratis"))
#  OR ("food tray" AND (MBG OR "makan bergizi gratis"))
#  OR (wadah AND (MBG OR "makan bergizi gratis"))
#  OR (tray AND (MBG OR "makan bergizi gratis")))
```

> ⚠️ **Sintaks xpoz ≠ X API v2.** Notebook X API memakai spasi sebagai
> implicit OR / AND tergantung konteks, plus operator `lang:id` dan
> `-is:retweet`. Untuk xpoz: hilangkan `lang:`/`-is:retweet` (pakai
> parameter `language`/`filterOutRetweets`), dan tulis `AND`/`OR`
> **eksplisit**.

Hitung `config_hash = sha256(join_all_yaml)` → simpan untuk run_meta.

### Step 2 — Tentukan window waktu

**FIXED RANGE** dari `config/thresholds.yaml`:

```
startDate = "2025-08-01"
endDate   = "2025-10-31"
```

Wajib pass eksplisit ke setiap call `getTwitterPostsByKeywords` dan
`countTweets`. Jangan pakai default rolling 60-hari xpoz.

### Step 3 — Fetch Corpus A (MBG umum)

Untuk tiap `(label, query)` di `query_packs.general`:

1. **Sanity-check volume** (opsional):
   ```
   countTweets(
     phrase=<query>,
     startDate="2025-08-01",
     endDate="2025-10-31",
     userPrompt="Hitung volume post Bahasa Indonesia tentang isu MBG umum kategori <label>"
   )
   ```
2. **Pilih response mode**:
   - `count <= 300` → `responseType="fast"`, `limit=300`
   - `count > 300` → `responseType="csv"` (async download)
3. **Fetch**:
   ```
   getTwitterPostsByKeywords(
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
     limit=300,
     userPrompt="Ambil post Bahasa Indonesia tentang isu MBG umum kategori <label> rentang Agustus-Oktober 2025"
   )
   ```
4. **Async polling** (kalau csv): loop `checkOperationStatus` setiap 5
   detik, max 12 iterasi, download `downloadUrl` saat `completed`.
5. **Validasi date in-range**: drop row dengan `createdAtDate` di luar
   `[2025-08-01, 2025-10-31]` (xpoz kadang buffer ±1 hari karena TZ).
6. **Normalisasi kolom** ke skema internal (`tweet_id`, `text_raw`,
   `like_count`, `repost_count`, …) + tambah `query_group="general"`,
   `query_label=<label>`, `query_used=<query>`,
   `tweet_url=https://x.com/{author_username}/status/{tweet_id}`.
7. Concat semua pack general → `general_df`. Dedupe by `tweet_id`.
8. Catat per pack: `{query_group, query_label, rows_retrieved}` →
   `general_stats_df`.
9. Simpan `outputs/00_general_query_stats.csv` dan
   `outputs/01_general_raw.csv`.

### Step 4 — Fetch Corpus B (Food Tray MBG)

Sama seperti Step 3, untuk `query_packs.tray` (6 pack). Hasilnya:
- `tray_df` → `outputs/02_tray_raw.csv`
- `tray_stats_df` → `outputs/00_tray_query_stats.csv`

`query_group="tray"` di kolom.

### Step 5 — Preprocessing teks (deterministik)

Mengikuti notebook **persis**, untuk kedua corpus:

```python
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
stemmer = StemmerFactory().create_stemmer()

CUSTOM_STOPWORDS = set(keywords["STOPWORDS"])
# wajib include: yang, dan, di, ke, dari, untuk, atau, pada, dengan,
# karena, jadi, itu, ini, aja, juga, udah, sudah, nya, ya, kok, nih,
# sih, mah, dong, rt, via, yg, utk, dr, krn, tp, tapi, dll, deh,
# mbg, makan, bergizi, gratis, program, sppg

def clean_text(text):
    text = text.lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", "", text)
    text = re.sub(r"&amp;", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def tokenize(t):
    return [w for w in t.split() if len(w) > 2 and w not in CUSTOM_STOPWORDS]

def stem_tokens(tokens):
    return [stemmer.stem(t) for t in tokens]

def prep_dataframe(df):
    out = df.copy()
    out["text_clean"]  = out["text_raw"].fillna("").apply(clean_text)
    out["tokens"]      = out["text_clean"].apply(tokenize)
    out["tokens_stem"] = out["tokens"].apply(stem_tokens)
    out["text_joined"] = out["tokens_stem"].apply(" ".join)
    out = out[out["text_joined"].str.len() > 0]
    out = out.drop_duplicates(subset=["text_joined"]).reset_index(drop=True)
    return out

general_pp = prep_dataframe(general_df)
tray_pp    = prep_dataframe(tray_df)
```

Tulis `outputs/03_general_preprocessed.csv` dan
`outputs/04_tray_preprocessed.csv`.

### Step 6 — Issue ranking pada Corpus A

Pakai `ISSUE_DICT` dari `config/keywords.yaml`:

```yaml
ISSUE_DICT:
  food_tray_ompreng: [food tray, tray, ompreng, wadah, tempat makan, alat makan, tutup, bocor, tumpah, rafia, stainless]
  menu_gizi:         [menu, rasa, lauk, sayur, nasi, buah, susu, gizi, protein, porsi, variasi menu]
  regulasi_kebijakan:[regulasi, aturan, kebijakan, perpres, juknis, sni, standar, pengawasan, bpom, bsn]
  kondisi_dapur_spgg:[dapur, spgg, kitchen, alat masak, kebersihan dapur, sanitasi dapur, fasilitas, pegawai dapur, juru masak]
  distribusi_logistik:[distribusi, logistik, angkut, kirim, telat, terlambat, jarak, handling, pengiriman, transportasi]
```

```python
def count_issue_hits(text, issue_dict):
    hits = []
    for issue, kws in issue_dict.items():
        if any(kw in text for kw in kws):
            hits.append(issue)
    return hits

general_pp["issue_hits"] = general_pp["text_clean"].apply(
    lambda x: count_issue_hits(x, ISSUE_DICT))

issue_counter = Counter()
for lst in general_pp["issue_hits"]:
    issue_counter.update(lst)

issue_rank_df = pd.DataFrame(
    [{"issue": k, "tweet_count": v} for k, v in issue_counter.items()]
).sort_values("tweet_count", ascending=False).reset_index(drop=True)

issue_rank_df["share_of_issue_coded_tweets_pct"] = (
    issue_rank_df["tweet_count"] /
    max(1, len(general_pp[general_pp["issue_hits"].apply(len) > 0])) * 100
).round(2)
issue_rank_df["rank"] = range(1, len(issue_rank_df) + 1)
issue_rank_df = issue_rank_df[["rank","issue","tweet_count","share_of_issue_coded_tweets_pct"]]
```

Tulis `outputs/05_issue_ranking_general.csv`. Hasilnya menjawab **"di
mana posisi food tray di antara isu MBG lainnya"**.

### Step 7 — Top words Corpus A

```python
general_tokens = []
for toks in general_pp["tokens_stem"]:
    general_tokens.extend(toks)
general_top_words = pd.DataFrame(
    Counter(general_tokens).most_common(100),
    columns=["word","count"]
)
```
Tulis `outputs/06_general_top_words.csv`.

### Step 8 — Sentimen lexicon Corpus B

```python
POSITIVE_WORDS = keywords["POSITIVE_WORDS"]
# bagus, baik, aman, rapi, kuat, bersih, higienis, sesuai, mantap, oke, layak

NEGATIVE_WORDS = keywords["NEGATIVE_WORDS"]
# dingin, basi, tumpah, bocor, kotor, kurang, buruk, karat, rusak, berat,
# susah, ribet, takut, bahaya, kontaminasi, jelek, tipis, kendala, masalah,
# tidak rapat, gak rapat, ga rapat, nggak rapat, ga rapet, ga bersih, gak bersih

def sentiment_score(text):
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    return pos - neg

def sentiment_label(score):
    if score > 0:  return "positif"
    if score < 0:  return "negatif"
    return "netral"

tray_pp["sentiment_score"] = tray_pp["text_clean"].apply(sentiment_score)
tray_pp["sentiment_label"] = tray_pp["sentiment_score"].apply(sentiment_label)

sent_summary = tray_pp["sentiment_label"].value_counts().reset_index()
sent_summary.columns = ["sentiment", "count"]
```
Tulis `outputs/07_tray_sentiment_summary.csv`.

### Step 9 — N-gram analysis (kedua corpus)

```python
from sklearn.feature_extraction.text import CountVectorizer

def get_top_ngrams(text_series, ngram_range=(2,2), top_n=30, min_df=2):
    texts = text_series.fillna("").astype(str).tolist()
    vec = CountVectorizer(ngram_range=ngram_range, min_df=min_df)
    X = vec.fit_transform(texts)
    terms = vec.get_feature_names_out()
    counts = np.asarray(X.sum(axis=0)).ravel()
    df = pd.DataFrame({"ngram": terms, "count": counts}) \
           .sort_values("count", ascending=False) \
           .reset_index(drop=True)
    return df.head(top_n)

general_top_bigrams = get_top_ngrams(general_pp["text_joined"], (2,2), 30, 2)
tray_top_bigrams    = get_top_ngrams(tray_pp["text_joined"],    (2,2), 30, 2)
tray_top_trigrams   = get_top_ngrams(tray_pp["text_joined"],    (3,3), 30, 2)
```

Tulis:
- `outputs/12_general_top_bigrams.csv`
- `outputs/13_tray_top_bigrams.csv`
- `outputs/14_tray_top_trigrams.csv`

### Step 10 — Co-occurrence Corpus B

**(a) Auto-vocab** (top 20 term by frequency):

```python
def build_cooccurrence_from_docs(text_series, min_df=3, max_features=20):
    vec = CountVectorizer(ngram_range=(1,1), min_df=min_df,
                          max_features=max_features, binary=True)
    X = vec.fit_transform(text_series.fillna("").astype(str))
    terms = vec.get_feature_names_out()
    co = (X.T @ X).toarray()
    np.fill_diagonal(co, 0)
    return pd.DataFrame(co, index=terms, columns=terms)

tray_co_df = build_cooccurrence_from_docs(tray_pp["text_joined"], min_df=3, max_features=20)

def extract_top_pairs(co_df, top_n=30):
    rows = []
    terms = list(co_df.index)
    for i in range(len(terms)):
        for j in range(i+1, len(terms)):
            c = int(co_df.iloc[i,j])
            if c > 0:
                rows.append({"term_1": terms[i], "term_2": terms[j],
                             "cooccurrence_count": c})
    return pd.DataFrame(rows).sort_values("cooccurrence_count", ascending=False)\
                             .reset_index(drop=True).head(top_n)

tray_top_pairs = extract_top_pairs(tray_co_df, top_n=30)
```
Tulis `outputs/15_tray_cooccurrence_pairs.csv`.

**(b) Design-term co-occurrence** (vocab terbatas):

```yaml
# config/keywords.yaml
DESIGN_TERMS:
  [tray, ompreng, wadah, tutup, bocor, tumpah, kuah, dingin, basi, suhu,
   stainless, karat, bahan, distribusi, rafia, ikat, higienis, sanitasi,
   kontaminasi, bersih]
```

```python
from itertools import combinations
def build_keyword_cooccurrence(df_in, terms):
    rows = []
    for text in df_in["text_clean"].fillna("").astype(str):
        present = sorted(set(t for t in terms if t in text))
        rows.extend(combinations(present, 2))
    pair_counter = Counter(rows)
    return pd.DataFrame([
        {"term_1": k[0], "term_2": k[1], "cooccurrence_count": v}
        for k, v in pair_counter.items()
    ]).sort_values("cooccurrence_count", ascending=False).reset_index(drop=True)

tray_design_pairs = build_keyword_cooccurrence(tray_pp, DESIGN_TERMS)
```
Tulis `outputs/16_tray_design_cooccurrence_pairs.csv`.

### Step 11 — BERTopic Corpus B

```python
from sklearn.feature_extraction.text import CountVectorizer
from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired

seed_topic_list = [
    ["food tray", "tray", "ompreng", "wadah"],
    ["dingin", "hangat", "suhu", "basi", "cepat basi"],
    ["tumpah", "bocor", "tutup", "rapat", "kuah"],
    ["stainless", "ss 304", "food grade", "karat", "bahan"],
    ["distribusi", "angkut", "rafia", "tali", "rapia", "ikat", "tumpuk", "handling"],
    ["higienis", "sanitasi", "bersih", "kotor", "kontaminasi", "cuci"],
]

docs_tray = tray_pp["text_clean"].fillna("").tolist()

if len(docs_tray) < 30:
    raise ValueError("Dokumen <30 — BERTopic tidak reliable. Perluas window/query.")

min_topic_size = 8 if len(docs_tray) < 300 else 10

topic_model = BERTopic(
    language="multilingual",
    seed_topic_list=seed_topic_list,
    min_topic_size=min_topic_size,
    calculate_probabilities=True,
    representation_model=KeyBERTInspired(),
    vectorizer_model=CountVectorizer(ngram_range=(1,2), min_df=2),
)
topics, probs = topic_model.fit_transform(docs_tray)
tray_pp["topic"] = topics
topic_info = topic_model.get_topic_info()
```

Tulis `outputs/08_tray_topic_info.csv`.

### Step 12 — Representative tweets per topic

```python
def representative_docs_per_topic(df_in, topic_col="topic", top_n=5):
    rows = []
    for tid in sorted(df_in[topic_col].dropna().unique()):
        if tid == -1:
            continue
        temp = df_in[df_in[topic_col] == tid].copy()
        temp["rep_score"] = (
            temp["like_count"]
            + 2 * temp["reply_count"]
            + 2 * temp["repost_count"]
        )
        for _, r in temp.sort_values("rep_score", ascending=False).head(top_n).iterrows():
            rows.append({
                "topic": tid,
                "text_raw": r["text_raw"],
                "tweet_url": r["tweet_url"],
                "rep_score": r["rep_score"],
            })
    return pd.DataFrame(rows)

topic_rep_df = representative_docs_per_topic(tray_pp)
```
Tulis `outputs/09_tray_topic_representative_docs.csv`.

### Step 13 — Draft need statement per topic

Mengganti `theme_rules.yaml` lama → `config/need_templates.yaml`:

```yaml
NEED_TEMPLATES:
  - keywords: [dingin, hangat, suhu, basi]
    statement: "Food tray harus mampu memperlambat penurunan suhu makanan selama distribusi."
  - keywords: [tumpah, bocor, tutup, rapat, kuah]
    statement: "Food tray harus mampu meminimalkan risiko kebocoran dan tumpahan selama pengangkutan dan distribusi."
  - keywords: [stainless, food, karat, bahan]
    statement: "Food tray harus menggunakan material yang aman pangan, tahan korosi, dan sesuai untuk distribusi MBG."
  - keywords: [higien, sanitasi, bersih, kotor, kontaminasi, cuci]
    statement: "Food tray harus mudah dibersihkan dan mendukung higienitas selama penanganan dan distribusi."
  - keywords: [distribusi, angkut, rafia, rapia, ikat, handling, tumpuk]
    statement: "Food tray harus stabil saat dibawa, mudah ditumpuk, dan mendukung handling distribusi yang aman."

DEFAULT_NEED_STATEMENT: "Food tray harus dirancang agar lebih sesuai dengan kebutuhan distribusi MBG di lapangan."
```

```python
def draft_need_statement(keywords, templates, default):
    text = " ".join(keywords)
    for tpl in templates:
        if any(k in text for k in tpl["keywords"]):
            return tpl["statement"]
    return default

topic_keywords_map = {
    tid: [w for w, _ in (topic_model.get_topic(tid) or [])[:10]]
    for tid in topic_info[topic_info["Topic"] != -1]["Topic"].tolist()
}

need_rows = []
for tid, kws in topic_keywords_map.items():
    need_rows.append({
        "topic": tid,
        "keywords": ", ".join(kws),
        "tweet_count": int((tray_pp["topic"] == tid).sum()),
        "draft_need_statement": draft_need_statement(kws, NEED_TEMPLATES, DEFAULT_NEED_STATEMENT),
        "manual_final_need_statement": "",
        "manual_notes": "",
    })

need_statement_df = pd.DataFrame(need_rows).sort_values("tweet_count", ascending=False).reset_index(drop=True)
```
Tulis `outputs/10_tray_need_statements_draft.csv`.

### Step 14 — Manual review template

Kolom mengikuti notebook (focus pada **anotasi design implication**,
bukan validasi LLM):

```python
manual_review_cols = [
    "tweet_id","created_at","author_username","text_raw","text_clean",
    "sentiment_label","topic","tweet_url"
]
manual_review_df = tray_pp[manual_review_cols].copy()
for c in ["manual_keep", "manual_topic_label", "manual_issue_category",
          "manual_design_implication", "manual_notes"]:
    manual_review_df[c] = ""
```
Tulis `outputs/11_tray_manual_review.csv`.

**Arti kolom (untuk pengisian manual oleh peneliti):**

| Kolom | Isi |
|---|---|
| `manual_keep` | `ya` / `tidak` — apakah post ini valid dipakai |
| `manual_topic_label` | label topic versi peneliti (kalau berbeda dari BERTopic, isi di sini) |
| `manual_issue_category` | kategori isu desain (mis. `material`, `suhu`, `distribusi`) |
| `manual_design_implication` | implikasi konkret untuk redesign tray |
| `manual_notes` | catatan bebas, alasan, kutipan menarik |

### Step 15 — Simpan outputs (CSV + Excel multi-sheet)

```python
# Sudah ditulis per step di atas; tambah Excel multi-sheet:
with pd.ExcelWriter("outputs/mbg_x_foodtray_analysis.xlsx", engine="openpyxl") as writer:
    general_stats_df.to_excel(writer, "query_stats_general", index=False)
    tray_stats_df.to_excel(writer, "query_stats_tray", index=False)
    general_df.to_excel(writer, "general_raw", index=False)
    tray_df.to_excel(writer, "tray_raw", index=False)
    general_pp.to_excel(writer, "general_preprocessed", index=False)
    tray_pp.to_excel(writer, "tray_preprocessed", index=False)
    issue_rank_df.to_excel(writer, "issue_ranking_general", index=False)
    general_top_words.to_excel(writer, "general_top_words", index=False)
    sent_summary.to_excel(writer, "tray_sentiment_summary", index=False)
    topic_info.to_excel(writer, "tray_topic_info", index=False)
    topic_rep_df.to_excel(writer, "tray_topic_rep_docs", index=False)
    need_statement_df.to_excel(writer, "draft_need_statement", index=False)
    manual_review_df.to_excel(writer, "manual_review_tray", index=False)
    general_top_bigrams.to_excel(writer, "general_top_bigrams", index=False)
    tray_top_bigrams.to_excel(writer, "tray_top_bigrams", index=False)
    tray_top_trigrams.to_excel(writer, "tray_top_trigrams", index=False)
    tray_top_pairs.to_excel(writer, "tray_cooccurrence_pairs", index=False)
    tray_design_pairs.to_excel(writer, "tray_design_cooccurrence", index=False)
```

### Step 16 — Report naratif `outputs/report.md`

Struktur wajib:

```markdown
# Laporan Text Mining X — MBG & Food Tray
**Run ID:** <uuid>   **Periode:** 1 Agustus – 31 Oktober 2025
**Total Corpus A:** N₁    **Total Corpus B:** N₂

## 1. Ringkasan Eksekutif
<3-5 kalimat: posisi rank food tray di Corpus A,
3 topic teratas BERTopic Corpus B, draft need statement prioritas>

## 2. Metodologi Singkat
- Sumber data: Xpoz MCP (Twitter/X), 2 corpus paralel
- Query packs general (3) + tray (6); rentang 2025-08-01 → 2025-10-31
- Preprocessing: regex + Sastrawi stemming + tokenize
- Issue ranking Corpus A: keyword dictionary 5 kategori
- Sentimen Corpus B: lexicon (positif/netral/negatif)
- Topic discovery Corpus B: BERTopic multilingual + KeyBERT representation
- N-gram & co-occurrence: scikit-learn CountVectorizer + Counter
- Need statement: rule-based mapping topic-keyword → template

## 3. Posisi Isu Food Tray di Corpus A (rank 5 isu MBG)
<tabel issue_rank_df + 1 paragraf interpretasi>

## 4. Sentimen Corpus B
<tabel sent_summary + interpretasi>

## 5. Topik BERTopic Corpus B
<tabel topic_info + 2 kutipan representatif per topic>

## 6. Co-occurrence Insight
<top 10 design pair + interpretasi semantik>

## 7. Draft Need Statement
<list dari need_statement_df, urutkan by tweet_count>

## 8. Limitasi
- Data terbatas pada X (bias platform, tidak mewakili guru/petugas SPPG offline)
- Lexicon sentiment: tidak menangkap sarkasme/negasi kompleks
- BERTopic: hasil sensitif terhadap min_topic_size + jumlah dokumen
- Window 3 bulan: kemungkinan over-representasi isu viral periode tersebut

## 9. Next Step
1. Manual review di `11_tray_manual_review.csv`
2. Triangulasi dengan benchmarking produk tray komersial
3. Turunkan draft need statement → spesifikasi teknis (tebal material, dimensi, mekanisme tutup)
4. Buat 2 alternatif desain → expert judgement SPPG
```

### Step 17 — Write `outputs/_run_meta.json`

```json
{
  "run_id": "<uuid4>",
  "timestamp_utc": "<ISO>",
  "window": {"start": "2025-08-01", "end": "2025-10-31"},
  "query_packs": {
    "general": ["mbg_umum_phrase", "mbg_umum_short", "mbg_umum_context"],
    "tray":    ["tray_umum_objek", "tray_suhu_basi", "tray_tumpah_tutup",
                "tray_material", "tray_distribusi", "tray_higienitas"]
  },
  "volumes": {
    "general_raw": N, "general_preprocessed": N,
    "tray_raw": N,    "tray_preprocessed": N
  },
  "skipped_packs": [],
  "bertopic_params": {
    "language": "multilingual",
    "min_topic_size": 8,
    "n_topics_discovered": K
  },
  "config_hash": "<sha256>",
  "xpoz_calls": [
    {"tool": "countTweets", "count": 9},
    {"tool": "getTwitterPostsByKeywords", "count": 9,
     "response_type": "fast|csv", "async_polling": true}
  ]
}
```

---

## 3. Error Handling

| Situasi | Aksi |
|---|---|
| `countTweets` return 0 untuk **semua** pack di salah satu corpus | Abort corpus tsb, lanjut corpus lain, catat di `run_meta.skipped_packs` |
| `checkOperationStatus` timeout (>60s) untuk pack | Skip pack, lanjut, catat di `run_meta` |
| Total dokumen tray <30 setelah preprocessing | **Abort BERTopic**, jalankan workflow tanpa Step 11-13, beri warning di report |
| `xpoz Unauthorized` | Stop, instruksikan user re-auth via OAuth |
| Sastrawi import error | Install `Sastrawi` lalu retry |
| BERTopic OOM (sentence-transformers heavy) | Fallback ke `min_topic_size=15` atau gunakan TF-IDF + KMeans clustering |

---

## 4. Batasan & Best Practice

- **Jangan** pakai operator `lang:` atau `-is:retweet` di dalam `query`
  string xpoz — pakai parameter `language` / `filterOutRetweets`.
- **Selalu** isi `userPrompt` di tool call (membantu cache xpoz).
- **Selalu** simpan `operationId` di log untuk audit async csv.
- **Stemming Sastrawi konservatif** — kata seperti "bergizi" tidak
  sepenuhnya hilang sebagai stem; tetap include "bergizi" di
  `STOPWORDS` agar tidak mendominasi token domain.
- **BERTopic bersifat stokastik** — set `random_state` di UMAP via
  `umap_model=UMAP(random_state=42)` kalau butuh reproducibility ketat
  (default tidak reproducible).
- **Manual review WAJIB** — Step 14 menghasilkan sheet kosong; peneliti
  isi minimal 30 baris untuk validasi akademik.
- **LLM tidak digunakan** di workflow ini. Jika di masa depan ingin
  augmentasi LLM (mis. interpretasi topic), buat workflow alternatif
  terpisah `WORKFLOW_LLM.md` agar pipeline utama tetap deterministik.

---

## 5. Quick-start prompt untuk agent

Kalau user bilang "jalankan workflow MBG", agent eksekusi:

> Baca `WORKFLOW.md`. Load semua YAML di `config/`. Verifikasi xpoz
> auth. Jalankan Step 0 (dry-run jika `auto_run_before_full=true`)
> lalu Step 1-17 berurutan. Update todo list tiap step selesai.
> Di akhir, tampilkan ringkasan: rank isu food tray di Corpus A,
> jumlah topic BERTopic Corpus B, 3 draft need statement teratas,
> dan link ke `outputs/report.md` + `outputs/mbg_x_foodtray_analysis.xlsx`.

---

## 6. Migrasi dari Workflow Sebelumnya

Workflow lama (LLM-based, 1 corpus) menggunakan file-file berikut yang
**tidak lagi dipakai** di workflow baru:

- `prompts/01_relevance.md` … `04_need_statement.md` — boleh
  dihapus / dipindah ke `archive/prompts/`
- `config/theme_rules.yaml` — diganti `config/need_templates.yaml`
- `schemas/coded_post.schema.json`, `schemas/theme_summary.schema.json`
  — boleh dihapus (tidak ada LLM yang divalidasi)
- `outputs/04_coded.csv`, `outputs/05_theme_summary.csv`,
  `outputs/08_need_statements.csv`, `outputs/09_manual_review.csv`
  (kolom lama) — generate ulang dengan workflow baru

`config/query_packs.yaml` perlu **direstruktur** dari flat dict menjadi
nested `general:` / `tray:`. `config/keywords.yaml` perlu **ditambah**
`ISSUE_DICT` dan `DESIGN_TERMS`.
