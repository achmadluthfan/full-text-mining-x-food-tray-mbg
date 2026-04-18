# Prompt: Sentiment Classification (Bahasa Indonesia)

**Tujuan:** Mengklasifikasikan sentimen tiap post **terhadap food tray /
wadah MBG** — bukan terhadap program MBG secara umum, bukan terhadap
pemerintah.

## Konteks
Input adalah post Twitter/X berbahasa Indonesia yang sudah lolos filter
relevansi (membahas wadah/tray MBG). Banyak di antaranya menggunakan
slang, negasi ("ga rapat", "nggak rapat"), dan sarkasme ("bagus lah
trayna, isinya numpah semua"). Model harus memahami nuansa ini.

## Skala 5 Level

| Label | Score | Indikator |
|---|---|---|
| `sangat_positif` |  2 | Pujian eksplisit + detail konkret ("stainlessnya tebal, kokoh, rapat banget") |
| `positif` |  1 | Pujian ringan / kesan baik tanpa detail kuat |
| `netral` |  0 | Pernyataan faktual, pertanyaan, info berita tanpa opini |
| `negatif` | -1 | Keluhan ringan, kekhawatiran, kritik terukur |
| `sangat_negatif` | -2 | Keluhan eksplisit + detail konkret / ungkapan keras ("amburadul", "bahaya", "nggak layak") |

## Aturan Penilaian
1. **Sarkasme dihitung sebagai makna yang dimaksud**, bukan literal.
   Contoh: "bagus banget trayna, kuah ke mana-mana" → `sangat_negatif`.
2. **Target sentimen = wadah/tray/ompreng**. Jika post mengeluhkan
   **program MBG secara umum** tapi wadahnya netral → `netral`.
3. **Negasi ganda / slang** harus diparsing: "ga rapat" = tidak rapat =
   negatif; "gak jelek lah" = agak positif.
4. **Pertanyaan murni** ("ompreng mbg bahan apa ya?") → `netral`.
5. **Retweet tanpa komentar tambahan** → `netral`.

## Output

**JSON array valid. Tanpa markdown fence, tanpa prosa.**

```json
[
  {
    "tweet_id": "string",
    "sentiment_label": "sangat_positif|positif|netral|negatif|sangat_negatif",
    "sentiment_score": 2,
    "rationale": "max 15 kata, Bahasa Indonesia"
  }
]
```

Validasi: `sentiment_label` HARUS salah satu dari 5 nilai enum di atas.
`sentiment_score` HARUS integer di {-2, -1, 0, 1, 2} dan **konsisten**
dengan label.

## Contoh

Input:
```json
[
  {"tweet_id":"101","text_clean":"ompreng mbg nya bagus banget isinya numpah semua di jalan mantap"},
  {"tweet_id":"102","text_clean":"tray stainless nya kokoh dan tutupnya rapat salut"},
  {"tweet_id":"103","text_clean":"food tray mbg itu stainless 304 atau 201 ya"}
]
```

Output:
```json
[
  {"tweet_id":"101","sentiment_label":"sangat_negatif","sentiment_score":-2,"rationale":"sarkasme keluhan tumpah saat distribusi"},
  {"tweet_id":"102","sentiment_label":"sangat_positif","sentiment_score":2,"rationale":"pujian eksplisit kokoh dan tutup rapat"},
  {"tweet_id":"103","sentiment_label":"netral","sentiment_score":0,"rationale":"pertanyaan spesifikasi material tanpa opini"}
]
```

## INPUT
```json
{{ posts_json }}
```
