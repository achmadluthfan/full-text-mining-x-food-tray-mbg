# Laporan Text Mining X — Food Tray MBG
**Run ID:** `883a71c5-d986-4477-a222-7c588d2d16eb`   **Periode:** 1 Agustus – 31 Oktober 2025   **Total relevant:** 82

## 1. Ringkasan Eksekutif

Analisis teks 94 post X berbahasa Indonesia (periode Ags–Okt 2025) mengidentifikasi 82 post relevan untuk isu desain food tray MBG. Setelah filter relevansi dan theme coding berbasis LLM, 79 post memiliki minimal satu tema isu desain. Tema dominan: **material_keamanan** (47 post). Isu paling kritis untuk diangkat sebagai need statement adalah material_keamanan (kontroversi food-grade / halal) dan retensi_suhu (keluhan nasi basi saat distribusi).

## 2. Metodologi Singkat

- **Sumber data:** MCP server Xpoz, endpoint `getTwitterPostsByKeywords`
- **Query packs:** umum_tray_mbg, isu_suhu, isu_tumpah_tutup, isu_material, isu_distribusi, isu_higiene
- **Rentang waktu:** 2025-08-01 → 2025-10-31 (fixed, bukan rolling)
- **Filter bahasa:** id; retweet di-exclude
- **Dedupe** by tweet_id; **filter engagement** `likes>=0`, `replies>=0`, `reposts>=0` (permisif karena volume kecil)
- **Relevansi, sentimen, theme coding:** LLM (Claude Opus 4.7) mengikuti `prompts/01-03.md`; fallback keyword/lexicon
- **Need statement:** sintesis LLM per tema dari 5 kutipan representatif (`prompts/04_need_statement.md`)
- **Out of window dropped:** 1 post (di luar Ags–Okt 2025)

## 3. Distribusi Sentimen (post coded)

| Label | Count | Pct |
|---|---:|---:|
| sangat_negatif | 23 | 29.1% |
| negatif | 33 | 41.8% |
| netral | 13 | 16.5% |
| positif | 10 | 12.7% |
| sangat_positif | 0 | 0.0% |

## 4. Distribusi Tema

| Tema | Count | Pct |
|---|---:|---:|
| material_keamanan | 47 | 59.49% |
| higienitas | 32 | 40.51% |
| retensi_suhu | 10 | 12.66% |
| handling_stackability | 9 | 11.39% |
| ergonomi_penggunaan | 6 | 7.59% |
| kebocoran_tumpah | 6 | 7.59% |

## 5. Need Statements Prioritas

### material_keamanan — priority: **tinggi** (frekuensi: 47)

**Need statement:** Food tray MBG harus menggunakan material yang terverifikasi food-grade, bersertifikat halal, dan bebas dari risiko kontaminasi zat berbahaya (logam berat, pelumas non-halal) sepanjang rantai produksi.

**Justifikasi:** Tema ini mendominasi diskusi dengan keluhan mencakup tuduhan penggunaan pelumas minyak babi pada proses produksi tray impor dari China, pemakaian SS201 yang tidak food grade (risiko logam berat), serta tuntutan sertifikasi halal dan SNI. Sebanyak 47 post mengangkat isu ini, beberapa viral hingga 40 ribu impresi. Kepercayaan publik terhadap material tray merupakan prasyarat diterimanya program.

**Atribut desain turunan:**
- material stainless steel SS 304 food-grade (bukan SS 201)
- sertifikasi halal BPJPH + SNI untuk seluruh batch produksi
- auditable supply chain lokal (UMKM) untuk mengurangi ketergantungan impor
- uji lab independen rutin untuk migrasi logam berat dan residu pelumas
- label/QR-code traceability pada setiap tray

**Kutipan bukti:**
- @adarwis (2025-09-23, 432❤): "Hasil uji coba lab di China, Food tray MBG terbukti berlapis minyak babi https://t.co/X107dUEZIg…"
- @NovalAssegaf (2025-09-15, 349❤): "Bahan baku minyak babi memang digunakan dalam proses pembuatan ompreng MBG.…"

### higienitas — priority: **tinggi** (frekuensi: 32)

**Need statement:** Food tray MBG harus mendukung proses sanitasi yang efektif, dapat dibersihkan menyeluruh dengan mesin, dan bebas dari celah yang memungkinkan residu makanan atau jamur menempel antar penggunaan.

**Justifikasi:** Ditemukan 32 post yang mengangkat isu higienitas, mulai dari video viral petugas SPPG mencuci tray di bak kotor dengan air tidak mengalir, tumpukan tray tergenang air kotor di Banten, hingga laporan tutup ompreng berjamur di sekolah. Kegagalan sanitasi merupakan titik kritis yang langsung berdampak pada keamanan pangan dan citra program.

**Atribut desain turunan:**
- geometri tray tanpa sudut tajam / celah tersembunyi (radius minimum pada pertemuan sisi)
- kompatibel dengan mesin pencuci piring industrial (dimensi rak + suhu 85°C)
- permukaan non-porous pada seluruh area kontak makanan
- tutup dengan gasket yang dapat dilepas-cuci terpisah
- tanda/indikator visual saat tray kotor / butuh pencucian ulang

**Kutipan bukti:**
- @adarwis (2025-09-23, 432❤): "Hasil uji coba lab di China, Food tray MBG terbukti berlapis minyak babi https://t.co/X107dUEZIg…"
- @salam4jari (2025-10-02, 336❤): "Gak cuma menggunakan minyak babi, ompreng MBG ternyata dicuci dengan cara yang higienis.…"

### retensi_suhu — priority: **tinggi** (frekuensi: 10)

**Need statement:** Food tray MBG harus mampu mempertahankan suhu aman pangan sajian selama rentang waktu produksi hingga konsumsi serta mencegah kondisi yang memicu pertumbuhan bakteri akibat penutupan saat panas.

**Justifikasi:** Sebanyak 10 post mengeluhkan makanan basi saat tiba di sekolah — sering disebut 'nasi dimasak jam 2-3 pagi dan disajikan siang hari'. Analisis teknis dari pengguna (termasuk pemilik catering dan ahli) menunjukkan bahwa menutup wadah saat makanan masih panas memerangkap uap dan memicu pertumbuhan bakteri. Ada saran eksplisit menambahkan ventilasi pada tray.

**Atribut desain turunan:**
- insulasi termal terintegrasi (double-wall atau liner)
- ventilasi satu arah untuk pelepasan uap tanpa mengorbankan kerapatan cairan
- standar retensi suhu: ≥60°C selama minimum durasi distribusi yang ditargetkan
- opsi gasket silikon food-grade pada tutup
- protokol/panduan waktu tunggu sebelum menutup wadah

**Kutipan bukti:**
- @akhyar_22 (2025-10-08, 117❤): "Stainless Steel:  +:  Mudah dibersihkan,  Suhu makanan awet (lebih awet lagi kalau pake lunch bag) -: Harus dicuci abis makan entar jadi berbekas,  Sebelum beli, cek dlu bahannya food grade ga (ingat, Ompreng MBG beracun…"
- @SagitaP_ (2025-09-25, 3❤): "@ceritasisikanan @gebethcalled @ARSIPAJA nyokap gw punya catering besar di jakarta, menurut beliau wadah MBG itu kan aluminum, kalo makanan panas langsung ditutup, pasti potensi basi lebih gede. mengingat sekali jalan bi…"

### handling_stackability — priority: **sedang** (frekuensi: 9)

**Need statement:** Food tray MBG harus mendukung stackability yang stabil dan handling distribusi yang efisien sehingga tidak bergantung pada improvisasi manual (pengikatan rafia) yang membebani petugas dan meningkatkan risiko jatuh.

**Justifikasi:** Total 9 post mengangkat isu handling: guru mengikat 28 ompreng sendiri, distribusi memakan 2 jam pelajaran, ompreng berserakan di jalan Lampung, dan tumpukan tray tidak stabil. Desain saat ini mengandalkan pengikatan rafia manual — indikator jelas bahwa geometri tray belum mendukung stacking.

**Atribut desain turunan:**
- fitur self-locking stack (interlocking geometry) pada tutup dan alas
- handle/grip ergonomis pada sisi panjang untuk pengangkatan tumpukan
- dimensi standar kompatibel dengan kotak distribusi (motor SPPG / mobil bak)
- indikator tumpukan maksimum aman (marking visual)
- frame/rak distribusi pendamping untuk transport massal

**Kutipan bukti:**
- @AiraNtiePuspa (2025-10-20, 49❤): "Guru skrg, selain hrs jago ngiket food tray MBG jg wajib punya skill Damkar😂😂😂 Kok bisa sii bocil ciwi ini nyangkut, mana permen nya ga dilepas pulaakk😂 https://t.co/Mn0LW9wqYy…"
- @giuseppinamnd (2025-10-17, 11❤): "drama ompreng MBG ilang 🙂…"

### ergonomi_penggunaan — priority: **sedang** (frekuensi: 6)

**Need statement:** Food tray MBG harus nyaman digunakan oleh siswa (dibuka, dipegang) maupun petugas (dibawa, dicuci, ditumpuk) tanpa membebani waktu operasional atau memicu workaround tidak higienis.

**Justifikasi:** Total 6 post mengangkat isu ergonomi: guru terpaksa belajar skill pemadam kebakaran untuk ngiket tray, siswa pakai tutup ompreng sebagai sendok, 2 jam pelajaran habis untuk distribusi. Beban operasional ini menunjukkan mismatch antara desain produk dan konteks penggunaan nyata di sekolah.

**Atribut desain turunan:**
- bobot total tray+tutup di bawah ambang ergonomi kerja anak SD (target <500g per unit saat kosong)
- bukaan tutup satu-tangan untuk anak usia 6-12 tahun
- permukaan pegangan anti-panas pada sisi tutup
- tutup yang tidak bisa berfungsi sebagai alat makan improvisasi (mencegah workaround tidak higienis)

**Kutipan bukti:**
- @AiraNtiePuspa (2025-10-20, 49❤): "Guru skrg, selain hrs jago ngiket food tray MBG jg wajib punya skill Damkar😂😂😂 Kok bisa sii bocil ciwi ini nyangkut, mana permen nya ga dilepas pulaakk😂 https://t.co/Mn0LW9wqYy…"
- @JjanIsTweeting (2025-09-29, 0❤): "@zanatul_91 Saya dari mulai ikat 10 ompreng MBG dibantu anak-anak, sampai ngikat 28 sendiri. Lulus ya, S.Pd., Gr.,…"

### kebocoran_tumpah — priority: **sedang** (frekuensi: 6)

**Need statement:** Food tray MBG harus meminimalkan risiko kebocoran kuah dan tumpahan selama pengangkutan tanpa menjebak uap yang memicu basi.

**Justifikasi:** Isu ini muncul dalam 6 post, biasanya bersamaan dengan keluhan retensi suhu ('tutup rapat → uap terjebak → basi') dan handling ('tutup ompreng jamuraan'). Kebutuhan adalah kerapatan terhadap cairan, bukan uap — dua hal yang sering tertukar pada desain tray saat ini.

**Atribut desain turunan:**
- sekat kompartemen internal untuk memisahkan kuah dari nasi/lauk kering
- tutup dengan sealing differential: rapat terhadap cairan, breathable terhadap uap
- tes kebocoran pada kemiringan 45° sebagai acceptance criteria
- tutup berwarna kontras untuk inspeksi visual kebersihan

**Kutipan bukti:**
- @SagitaP_ (2025-09-25, 3❤): "@ceritasisikanan @gebethcalled @ARSIPAJA nyokap gw punya catering besar di jakarta, menurut beliau wadah MBG itu kan aluminum, kalo makanan panas langsung ditutup, pasti potensi basi lebih gede. mengingat sekali jalan bi…"
- @Indonesiaguyub (2025-10-04, 2❤): "@DivHumas_Polri Satu lagi yang sangat penting di evaluasi. Tray tempat makan MBG itu harusnya ada ventilasi udara nya. Sehingga nasi dimasak jam 2 pagi, disajikan jam 12 siang, tidak basi dan berair (berlendir). Mau sani…"

## 6. Limitasi

- **Volume data kecil** (82 post relevan). Kesimpulan tematik bersifat indikatif, bukan representatif populasi.
- **Bias platform X:** diskusi di Twitter cenderung politis; suara langsung petugas SPPG / siswa under-represented.
- **Periode Ags–Okt 2025 didominasi isu viral material non-halal/minyak babi** — ini mempengaruhi distribusi tema.
- **LLM dapat halusinasi**; disediakan `09_manual_review.csv` untuk audit manual oleh peneliti.
- Dry-run: 2 query pack (`isu_tumpah_tutup`, `isu_distribusi`) awalnya 0-hit di countTweets tapi search actual return hasil — beda indeks antara count vs search xpoz.

## 7. Next Step

1. **Manual review** di `outputs/09_manual_review.csv` (wajib untuk validasi akademik).
2. **Gabungkan dengan benchmarking produk** (tray stainless SS 304 vs 201 food grade).
3. **Turunkan atribut desain** di Section 5 ke **spesifikasi teknis** (tebal material, dimensi, mekanisme tutup, insulasi, dsb.).
4. **Buat 2 alternatif desain** → uji dengan expert judgement SPPG.
5. Jika butuh data lebih banyak: perluas window ke **Mei–November 2025** atau tambah sumber **Reddit / TikTok** via xpoz.

---
*Generated: 2026-04-17T16:25:56Z | config_hash: `144c95931fe3e84a`*