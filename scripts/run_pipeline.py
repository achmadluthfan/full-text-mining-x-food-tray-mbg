"""
MBG Food Tray — X Text Mining Pipeline.

Mengeksekusi WORKFLOW.md Step 4-13 dengan data yang sudah di-fetch dari
xpoz MCP (outputs/_raw_fetched.json).

LLM judgements (relevance, sentiment, theme, need statement) di-embed
inline sebagai dict `LLM_JUDGEMENTS` dan `NEED_STATEMENTS` di bawah.
Dihasilkan oleh agent (Claude Opus 4.7) mengikuti prompt 01-04.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
CFG = ROOT / "config"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def ts_to_iso(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def ts_to_date(ts: int) -> str:
    return datetime.fromtimestamp(ts, tz=timezone.utc).strftime("%Y-%m-%d")


def clean_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    t = text.lower()
    t = re.sub(r"http\S+|www\S+", " ", t)
    t = re.sub(r"@\w+", " ", t)
    t = re.sub(r"#", "", t)
    t = re.sub(r"[\n\r\t]", " ", t)
    t = re.sub(r"[^a-zA-Z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ---------------------------------------------------------------------------
# LLM judgements (inline — follows prompts/01-04)
#
# Agent Claude Opus 4.7 bertindak sebagai klasifier untuk 91 post.
# is_relevant + relevance_score: prompts/01_relevance.md
# sentiment_label + sentiment_score: prompts/02_sentiment.md
# themes (multi-label): prompts/03_theme_coding.md
#
# Tema enum:
#   retensi_suhu, kebocoran_tumpah, material_keamanan, higienitas,
#   handling_stackability, ergonomi_penggunaan
# ---------------------------------------------------------------------------

LLM_JUDGEMENTS: dict[str, dict] = {
    "1971212309063471442": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "ompreng MBG berceceran/jatuh saat distribusi di Lampung", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "berita insiden ompreng berceceran, implikasi handling buruk", "themes": ["handling_stackability"], "themes_rationale": "ompreng jatuh dari bak mobil saat distribusi"},
    "1970860704937992253": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "cerita gaji pencuci tray, bukan isu wadah", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "konten viral soal pekerja, bukan opini wadah", "themes": []},
    "1979021825100185743": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "keluhan ompreng hilang di sekolah, implikasi handling/accountability", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keluhan 'drama ompreng ilang'", "themes": ["handling_stackability"], "themes_rationale": "tracking/hilang — masalah handling inventaris"},
    "1978317467769508259": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "wacana sertifikasi halal food tray MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "statement regulasi, tanpa opini keras", "themes": ["material_keamanan"], "themes_rationale": "isu halal material tray"},
    "1971100781056332251": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "beban tambahan guru menghitung/mengelola ompreng", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "sarkasme beban kerja tambahan", "themes": ["ergonomi_penggunaan", "handling_stackability"], "themes_rationale": "beban operasional petugas dan inventory tracking"},
    "1970406519956217939": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "isu viral lapisan minyak babi di food tray MBG — material keamanan", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "tuduhan material berlapis minyak babi, viral 432 likes", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "klaim kontaminasi material tray"},
    "1967884894853599525": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "DPRD desak transparansi material ompreng MBG", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "isu politik material non-halal", "themes": ["material_keamanan"], "themes_rationale": "dugaan unsur babi di ompreng"},
    "1980236305897513307": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "guru pakai skill tambahan ngiket food tray MBG — masalah stackability", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "sarkasme guru butuh skill Damkar untuk ngiket tray", "themes": ["handling_stackability", "ergonomi_penggunaan"], "themes_rationale": "ngiket tray eksplisit + beban kerja petugas"},
    "1983913154426868015": {"is_relevant": False, "relevance_score": 1, "relevance_reason": "mention tag tanpa konteks", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "mention list, tidak membahas wadah", "themes": []},
    "1975754742950158541": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "pembelaan umum program 1M ompreng — tidak spesifik wadah tapi mengakui kekurangan", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "pembelaan program, akui ada kekurangan, minta evaluasi", "themes": []},
    "1973949420527054954": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "deskripsi proses pencucian ompreng MBG di oven", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "pujian proses sanitasi dengan oven, dukungan program", "themes": ["higienitas"], "themes_rationale": "proses pencucian dan sterilisasi oven"},
    "1980021091692327076": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "kritik keras terhadap klaim food tray MBG berbahan babi halal asal dicuci", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "sarkasme keras terhadap pembelaan material babi", "themes": ["material_keamanan"], "themes_rationale": "kontroversi halal material tray dari China"},
    "1971445004418810131": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "sindiran personal pakai metafora wadah MBG, bukan isu wadah sungguhan", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "meme/metafora, tidak membahas tray sebagai produk", "themes": []},
    "1971547998288294143": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "Menperin rencana SNI food tray MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "statement regulasi netral", "themes": ["material_keamanan"], "themes_rationale": "regulasi SNI material tray"},
    "1968918738356314159": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "Presiden respon isu minyak babi di food tray MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "berita respon presiden tanpa opini", "themes": ["material_keamanan"], "themes_rationale": "kontroversi material tray"},
    "1972589193772834967": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "insiden ompreng MBG tercampur limbah di Lebak — higienitas parah", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "kasus kelalaian kebersihan — SPPG akui kelalaian", "themes": ["higienitas"], "themes_rationale": "ompreng tercampur limbah"},
    "1983781321194328255": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "kisah petugas cuci ompreng, fokus kesejahteraan bukan wadah", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "cerita human interest pencuci tray", "themes": []},
    "1973955273166643569": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "deskripsi proses pencucian ompreng di oven", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "dukungan proses sanitasi", "themes": ["higienitas"], "themes_rationale": "proses sanitasi oven"},
    "2042398511132709049": {"is_relevant": False, "relevance_score": 1, "relevance_reason": "di luar window waktu + tidak relevan", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "di luar range Aug-Okt 2025", "themes": []},
    "1980790626083131783": {"is_relevant": False, "relevance_score": 3, "relevance_reason": "narasi sosial-emosional program MBG, bukan isu wadah", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "prose dukungan program", "themes": []},
    "1976414660833530240": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "komentar visual sekilas, bukan diskusi tray", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "komentar sekilas", "themes": []},
    "1976245350697713739": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "pertanyaan sertifikasi halal tempat makan MBG", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keraguan sertifikasi halal", "themes": ["material_keamanan"], "themes_rationale": "isu halal material"},
    "1975940856722137473": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "info material tray impor China dan upaya produksi lokal", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "statement netral dari bot grok", "themes": ["material_keamanan"], "themes_rationale": "asal material tray"},
    "1975771441124778231": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "pertanyaan tentang tray MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "pertanyaan singkat", "themes": []},
    "1975407125720625442": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "diskusi material nampan import China mengandung minyak babi, permintaan audit forensik", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kekhawatiran material dan minta audit", "themes": ["material_keamanan"], "themes_rationale": "material tray impor diduga mengandung babi"},
    "1975405188283572689": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "umpatan random pakai metafora wadah", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "umpatan personal", "themes": []},
    "1975371230661517379": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "pertanyaan kontaminasi material tray produksi China", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keraguan material tray China", "themes": ["material_keamanan"], "themes_rationale": "isu proses produksi material"},
    "1975245051975639525": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "meme/joke dengan link, konteks tidak jelas", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "meme tanpa konteks", "themes": []},
    "1974997605412384837": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "pujian pada isi tray MBG yang menarik", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "ekspresi iri pada isi tray yang menarik", "themes": []},
    "1974761872177209375": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "caption singkat tanpa opini", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "caption singkat", "themes": []},
    "1974475819272860058": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "Wagub tekankan kebersihan food tray MBG saat sidak", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "berita sidak kebersihan", "themes": ["higienitas"], "themes_rationale": "fokus kebersihan tray"},
    "1974431518664835258": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "sindiran cara mencuci tray MBG yang buruk", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "sarkasme keras tentang cara cuci tray di parit", "themes": ["higienitas"], "themes_rationale": "kritik proses pencucian tray"},
    "1974403664195571944": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "saran desain eksplisit: tray butuh ventilasi udara untuk cegah basi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keluhan konkret + saran desain retensi suhu", "themes": ["retensi_suhu", "kebocoran_tumpah"], "themes_rationale": "ventilasi tray + nasi basi/berair karena tutup rapat"},
    "1974376758679065071": {"is_relevant": False, "relevance_score": 3, "relevance_reason": "klarifikasi istilah ompreng = tempat makan MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "klarifikasi istilah", "themes": []},
    "1974061009150361997": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "BPJPH klarifikasi halal food tray MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "berita klarifikasi resmi", "themes": ["material_keamanan"], "themes_rationale": "sertifikasi halal material tray"},
    "1973936529446961387": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "narasi sanitasi SPPG Polri dengan oven", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim sanitasi ketat", "themes": ["higienitas"], "themes_rationale": "sistem sanitasi tray"},
    "1973933197684846601": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "duplikat narasi sanitasi SPPG Polri", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim sanitasi ketat", "themes": ["higienitas"], "themes_rationale": "sistem sanitasi tray"},
    "1973645522243297545": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "viral video cara cuci food tray MBG yang buruk", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "keluhan viral proses cuci yang tidak higienis", "themes": ["higienitas"], "themes_rationale": "cara cuci tray buruk viral"},
    "1973620220452651017": {"is_relevant": False, "relevance_score": 2, "relevance_reason": "umpatan pakai metafora 'elek koyok food tray mbg'", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "metafora negatif terhadap penampilan tray", "themes": []},
    "1973367898933739873": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "laporan anak pindahkan makanan dari tray MBG — penolakan wadah", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "anak-anak tolak makan dari tray MBG, pindah ke wadah sendiri", "themes": ["higienitas", "material_keamanan"], "themes_rationale": "penolakan terhadap wadah karena kepercayaan pada kebersihan/keamanan"},
    "1971542031848927537": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "pertanyaan ahli: layak Yakult dengan makanan hangat di ompreng tertutup — retensi suhu", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kekhawatiran keamanan pangan karena suhu dan tutup rapat", "themes": ["retensi_suhu", "material_keamanan"], "themes_rationale": "isu suhu ruang & kualitas isi di dalam ompreng tertutup"},
    "1975857668515565659": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "review pros-cons material stainless untuk ompreng MBG", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "peringatan ompreng MBG beracun + minyak babi", "themes": ["material_keamanan", "retensi_suhu"], "themes_rationale": "analisis material stainless: awet suhu + peringatan non food grade"},
    "1968921423012942265": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "orangtua cek manual apakah makanan di ompreng basi/aneh — ketidakpercayaan", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "kehilangan kepercayaan, cek langsung apakah basi", "themes": ["retensi_suhu", "higienitas"], "themes_rationale": "khawatir basi + keamanan pangan"},
    "1969808061926969371": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "trauma anak keracunan dari tray MBG", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "trauma + keringat dingin melihat tray", "themes": ["higienitas", "material_keamanan"], "themes_rationale": "keracunan + trauma asosiasi dengan tray"},
    "1971223491111494130": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "keluhan eksplisit nasi basi + wadah MBG dibawa pulang", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "keluhan nasi basi rutin", "themes": ["retensi_suhu", "higienitas"], "themes_rationale": "nasi basi + kebersihan wadah"},
    "1973284058403877150": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "keluhan wadah MBG berisi makanan basi — doa kekuatan untuk yang buka", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "sarkasme eksplisit tentang makanan basi", "themes": ["retensi_suhu"], "themes_rationale": "keluhan basi di wadah"},
    "1970268980574331075": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "kritik SOP wadah MBG ditutup saat panas — penyebab basi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik proses tutup wadah saat panas langsung", "themes": ["retensi_suhu", "kebocoran_tumpah"], "themes_rationale": "tutup wadah saat panas menyebabkan masalah"},
    "1968912859389186372": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "info proses produksi food tray pakai minyak panas untuk anti-lengket", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keraguan proses produksi material tray China", "themes": ["material_keamanan"], "themes_rationale": "proses produksi material tray"},
    "1970096254974915016": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "keluhan eksplisit: nasi dimasak jam 2-3 pagi dalam wadah, disajikan siang, rawan basi", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "keluhan konkret alur waktu produksi-distribusi", "themes": ["retensi_suhu"], "themes_rationale": "rentang waktu panjang di wadah = rawan basi"},
    "1971235217093591277": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "kritik teknis: wadah aluminum + ditutup panas + ratusan porsi = rawan basi", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "analisis teknis pemilik catering besar, keluhan fundamental", "themes": ["retensi_suhu", "material_keamanan", "kebocoran_tumpah"], "themes_rationale": "material aluminum + tutup panas + volume besar"},
    "1971744023028392271": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "analisis teknis: stainless simpan panas + tutup rapat = kontaminasi bakteri", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "penjelasan mekanisme kontaminasi dari uap terperangkap", "themes": ["retensi_suhu", "kebocoran_tumpah", "higienitas"], "themes_rationale": "mekanisme uap-bakteri karena tutup rapat stainless"},
    "1960327929965248622": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "berita stainless steel untuk ompreng dan kelebihannya", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "berita info material", "themes": ["material_keamanan"], "themes_rationale": "material stainless tray"},
    "1965586865043767593": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "pertanyaan/kritik politik: bisakah stainless mengandung lemak babi?", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik politik terhadap isu material", "themes": ["material_keamanan"], "themes_rationale": "material stainless + isu halal"},
    "1969739695371538671": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "tuduhan ompreng tidak food grade + kandungan logam berbahaya + impor Tiongkok", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "tuduhan tegas bahaya material tray impor", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "non food grade + logam berbahaya + potensi kontaminasi"},
    "1960682420472308063": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "berita dampak stainless ompreng belum food grade", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "berita dampak material non food grade", "themes": ["material_keamanan"], "themes_rationale": "stainless tidak food grade"},
    "1969729029801681150": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "info grok tentang impor vs produksi lokal tray", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "info netral", "themes": ["material_keamanan"], "themes_rationale": "asal material tray"},
    "1969066329383518268": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "fiqh: tray MBG yang diproses dengan pelumas minyak babi bisa disucikan", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "diskusi fiqh najis", "themes": ["material_keamanan"], "themes_rationale": "status halal material"},
    "1960900122688082076": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "berita ompreng impor diduga bahan berbahaya & minyak babi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "berita kontroversial material", "themes": ["material_keamanan"], "themes_rationale": "material impor diduga berbahaya"},
    "1961256571473920385": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "Mendag usul SNI food tray MBG sebagai respon isu nonhalal", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "berita regulasi SNI", "themes": ["material_keamanan"], "themes_rationale": "standar SNI tray"},
    "1979891965933302208": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "sadar alergi karat karena berita tray MBG", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "alergi karat + asosiasi negatif tray", "themes": ["material_keamanan"], "themes_rationale": "karat sebagai isu material"},
    "1962402271381360723": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "tuntutan konfirmasi dan penggantian tray bila terbukti mengandung babi/non food grade", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "tuntutan aksi konkret + tanggung jawab", "themes": ["material_keamanan"], "themes_rationale": "desakan ganti material tray"},
    "1963214177331183643": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "DPR desak BGN pastikan keamanan bahan ompreng", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "tekanan politik keamanan material", "themes": ["material_keamanan"], "themes_rationale": "keamanan bahan ompreng"},
    "1959936012051984408": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "tuduhan keras ss201 non food grade dipakai tray = keracunan logam berat", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "tuduhan ekstrem 'pembunuhan berencana' dari logam berat", "themes": ["material_keamanan"], "themes_rationale": "ss201 non food grade + logam berat"},
    "1963134067412754817": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "berita DPR desak keamanan material ompreng MBG", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "tekanan politik material", "themes": ["material_keamanan"], "themes_rationale": "keamanan material ompreng"},
    "1960609091090571557": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "pertanyaan kritis: kenapa tray pakai SS201 yang tidak food grade", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik teknis pilihan material SS201", "themes": ["material_keamanan"], "themes_rationale": "SS201 non food grade"},
    "1969332854002770048": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "kritisi kebersihan sebelum pakai + keraguan food grade material", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik multi-aspek material + sanitasi", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "material food grade + pencucian sebelum pakai"},
    "1967622299873649044": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "klaim keras: minyak babi digunakan di proses produksi ompreng MBG", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "tuduhan konkret proses produksi", "themes": ["material_keamanan"], "themes_rationale": "proses produksi ompreng pakai minyak babi"},
    "1951521082118381631": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "rumor food tray mbg tidak food grade", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "rumor + pertanyaan verifikasi", "themes": ["material_keamanan"], "themes_rationale": "rumor non food grade"},
    "1960313033542205934": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "berita heboh ompreng MBG mengandung bahan berbahaya & minyak babi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "berita kontroversial", "themes": ["material_keamanan"], "themes_rationale": "material diduga berbahaya"},
    "1981597488877547773": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "kritik hygiene + food safety: kontainer dipakai non-makanan lalu makanan = compromised food grade", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik teknis multi-use container", "themes": ["higienitas", "material_keamanan", "handling_stackability"], "themes_rationale": "compromised food grade karena penggunaan ganda + handling"},
    "1975778653826130059": {"is_relevant": True, "relevance_score": 5, "relevance_reason": "pengalaman personal bunyi stainless mirip ompreng MBG", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "asosiasi pengalaman personal", "themes": ["ergonomi_penggunaan"], "themes_rationale": "pengalaman penggunaan stainless"},
    "1975134249578856748": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "BPJPH jaminan halal produk MBG", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim resmi halal", "themes": ["material_keamanan"], "themes_rationale": "sertifikasi halal material"},
    "1972607957411205399": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "pertanyaan bahan halal food tray + dugaan asal China", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik proses procurement material", "themes": ["material_keamanan"], "themes_rationale": "bahan halal + asal material"},
    "1971871260872528004": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "kritik oportunisme: ompreng MBG non food grade diimpor dari China", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik politik material non food grade impor", "themes": ["material_keamanan"], "themes_rationale": "ompreng non food grade impor"},
    "1969482280625455433": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "dugaan food tray MBG mengandung bahan berbahaya", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "dugaan bahan berbahaya", "themes": ["material_keamanan"], "themes_rationale": "bahan berbahaya material"},
    "1973651340040741131": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "sarkasme: 'tidak cuma minyak babi, cara cuci pun higienis'", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "sarkasme viral tentang pencucian", "themes": ["higienitas"], "themes_rationale": "proses pencucian buruk"},
    "1983338609890742357": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "narasi SPPG jaga kebersihan ompreng tetap higienis", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim dukungan kebersihan", "themes": ["higienitas"], "themes_rationale": "kebersihan ompreng"},
    "1976082905152749849": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "klaim kebersihan proses pencucian ompreng", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim dukungan", "themes": ["higienitas"], "themes_rationale": "kebersihan pencucian"},
    "1969030320306458925": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "fatwa PBNU: food tray MBG boleh dipakai setelah dicuci bersih", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "fatwa agama", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "status halal + pencucian"},
    "1975384389510176995": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "SPPG Cinere pakai mesin pencuci otomatis untuk higienitas", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "info positif mekanisasi pencucian", "themes": ["higienitas"], "themes_rationale": "mesin cuci otomatis untuk kebersihan"},
    "1970002934714036427": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "pertanyaan kritis: kata 'bersih' ambigu, tetap mengandung minyak babi?", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik ambiguitas klaim", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "kontaminasi vs pembersihan"},
    "1971537141235876347": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "viral video: tumpukan tray MBG tergenang air kotor di Banten", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "keluhan viral kondisi tray tergenang air kotor", "themes": ["higienitas", "handling_stackability"], "themes_rationale": "tumpukan tray tergenang air kotor"},
    "1973724897500443081": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "viral: petugas SPPG cuci ompreng asal-asalan di air kotor", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "pelanggaran SOP kebersihan viral", "themes": ["higienitas"], "themes_rationale": "pencucian ompreng asal-asalan"},
    "1975881428790587733": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "keluhan menjijikkan: ompreng dipakai berulang dicuci tidak bersih", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "kritik kebersihan penggunaan ulang", "themes": ["higienitas", "material_keamanan"], "themes_rationale": "cuci tidak bersih + reuse"},
    "1974315500655292467": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "viral: petugas cuci tray pakai bak kotor air tak mengalir", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "pelanggaran SOP viral", "themes": ["higienitas"], "themes_rationale": "pencucian dengan air tidak mengalir"},
    "1974214518407389375": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "janji SPPG pastikan ompreng MBG bersih", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "respons resmi arahan presiden", "themes": ["higienitas"], "themes_rationale": "janji kebersihan ompreng"},
    "1973948854384079293": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "klaim sanitasi ketat SPPG Polri", "sentiment_label": "positif", "sentiment_score": 1, "sentiment_rationale": "klaim dukungan", "themes": ["higienitas"], "themes_rationale": "sistem sanitasi"},
    "1983800609859105193": {"is_relevant": True, "relevance_score": 10, "relevance_reason": "keluhan eksplisit: tutup ompreng MBG di sekolah berjamur", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "laporan kondisi tutup berjamur", "themes": ["higienitas", "kebocoran_tumpah", "material_keamanan"], "themes_rationale": "tutup ompreng berjamur = sanitasi + material tutup"},
    "1969199330474016920": {"is_relevant": True, "relevance_score": 8, "relevance_reason": "diskusi fiqh + contoh kuah bakso najis vs mangkok bisa disucikan", "sentiment_label": "netral", "sentiment_score": 0, "sentiment_rationale": "diskusi fiqh", "themes": ["material_keamanan", "kebocoran_tumpah"], "themes_rationale": "status najis tray + kuah"},
    "1971932297562935657": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "pengakuan pakai tutup ompreng sebagai sendok — ergonomi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "workaround ergonomi: tutup jadi sendok", "themes": ["ergonomi_penggunaan", "higienitas"], "themes_rationale": "improvisasi pakai tutup sebagai alat makan"},
    "1969689983092138311": {"is_relevant": True, "relevance_score": 7, "relevance_reason": "argumen fiqh: sabun tidak cukup hilangkan najis menempel pada ompreng", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "kritik agama pencucian", "themes": ["material_keamanan", "higienitas"], "themes_rationale": "material + pencucian najis"},
    "1972706358031163725": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "keluhan eksplisit: guru ikat 28 ompreng MBG sendiri — handling manual", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "keluhan beban kerja ngiket ompreng", "themes": ["handling_stackability", "ergonomi_penggunaan"], "themes_rationale": "ikat ompreng = handling manual + beban guru"},
    "1973082252654616950": {"is_relevant": True, "relevance_score": 9, "relevance_reason": "2 jam pelajaran habis untuk distribusi ompreng MBG — kritik operasional", "sentiment_label": "sangat_negatif", "sentiment_score": -2, "sentiment_rationale": "kritik efisiensi distribusi makan waktu belajar", "themes": ["handling_stackability", "ergonomi_penggunaan"], "themes_rationale": "distribusi & handling makan waktu operasional"},
    "1971096340932493519": {"is_relevant": True, "relevance_score": 6, "relevance_reason": "ringkasan isu MBG multi-topik termasuk food tray & distribusi", "sentiment_label": "negatif", "sentiment_score": -1, "sentiment_rationale": "ringkasan sorotan publik", "themes": ["material_keamanan", "handling_stackability"], "themes_rationale": "isu kehalalan tray + distribusi"},
}


# Need statements per tema (prompts/04_need_statement.md)
# Diisi setelah agregasi tema selesai — lihat fungsi `build_need_statements`.


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    query_packs = load_yaml(CFG / "query_packs.yaml")
    keywords = load_yaml(CFG / "keywords.yaml")
    theme_rules = load_yaml(CFG / "theme_rules.yaml")
    thresholds = load_yaml(CFG / "thresholds.yaml")

    config_hash = hashlib.sha256(
        (
            json.dumps(query_packs, sort_keys=True, ensure_ascii=False)
            + json.dumps(keywords, sort_keys=True, ensure_ascii=False)
            + json.dumps(theme_rules, sort_keys=True, ensure_ascii=False)
            + json.dumps(thresholds, sort_keys=True, ensure_ascii=False)
        ).encode("utf-8")
    ).hexdigest()[:16]

    date_start = thresholds["date_window"]["start"]
    date_end = thresholds["date_window"]["end"]
    start_ts = int(
        datetime.strptime(date_start, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    )
    end_ts = int(
        datetime.strptime(date_end, "%Y-%m-%d")
        .replace(tzinfo=timezone.utc)
        .timestamp()
    ) + 86399

    raw = json.loads((OUT / "_raw_fetched.json").read_text(encoding="utf-8"))

    # Step 4 — normalize, attach query_used, derive url + iso
    query_used_map = {
        label: q for label, q in query_packs.items()
    }

    raw_rows: list[dict] = []
    for r in raw:
        ts = r["created_at_ts"]
        row = {
            "tweet_id": r["tweet_id"],
            "conversation_id": r.get("conversation_id"),
            "created_at": ts_to_iso(ts),
            "created_at_date": ts_to_date(ts),
            "author_id": r.get("author_id"),
            "author_username": r.get("author_username", ""),
            "lang": r.get("lang", "id"),
            "text_raw": r["text_raw"],
            "like_count": r.get("like_count", 0),
            "reply_count": r.get("reply_count", 0),
            "repost_count": r.get("repost_count", 0),
            "quote_count": r.get("quote_count", 0),
            "bookmark_count": r.get("bookmark_count", 0),
            "impression_count": r.get("impression_count", 0),
            "query_used": query_used_map.get(r["query_label"], ""),
            "query_label": r["query_label"],
            "tweet_url": (
                f"https://x.com/{r.get('author_username','unknown')}/status/"
                f"{r['tweet_id']}"
            ),
            "_ts": ts,
        }
        raw_rows.append(row)

    raw_fields = [
        "tweet_id", "conversation_id", "created_at", "created_at_date",
        "author_id", "author_username", "lang", "text_raw",
        "like_count", "reply_count", "repost_count", "quote_count",
        "bookmark_count", "impression_count",
        "query_used", "query_label", "tweet_url",
    ]
    write_csv(OUT / "01_raw.csv", raw_rows, raw_fields)

    # Step 4 — dedupe + date filter + engagement filter
    seen = set()
    cleaned: list[dict] = []
    out_of_window = 0
    for r in raw_rows:
        if r["tweet_id"] in seen:
            continue
        seen.add(r["tweet_id"])
        if not (start_ts <= r["_ts"] <= end_ts):
            out_of_window += 1
            continue
        if r["like_count"] < thresholds["min_likes"]:
            continue
        if r["reply_count"] < thresholds["min_replies"]:
            continue
        if r["repost_count"] < thresholds["min_reposts"]:
            continue
        cleaned.append(r)
    write_csv(OUT / "02_cleaned.csv", cleaned, raw_fields)

    # Step 5 — preprocess
    for r in cleaned:
        r["text_clean"] = clean_text(r["text_raw"])

    # Step 6 — relevance (LLM inline + keyword fallback)
    def keyword_relevance_score(txt: str) -> int:
        tray_hit = sum(1 for t in keywords["TRAY_TERMS"] if t in txt)
        mbg_hit = sum(1 for t in keywords["MBG_TERMS"] if t in txt)
        issue_hit = sum(1 for t in keywords["ISSUE_TERMS"] if t in txt)
        return tray_hit * 3 + mbg_hit * 3 + issue_hit * 1

    relevant_rows: list[dict] = []
    for r in cleaned:
        tid = r["tweet_id"]
        j = LLM_JUDGEMENTS.get(tid)
        if j is None:
            score = keyword_relevance_score(r["text_clean"])
            r["relevance_score"] = min(10, score)
            r["is_relevant"] = score >= thresholds["relevance_score_min"]
            r["relevance_reason"] = "fallback keyword"
            r["relevance_method"] = "keyword_fallback"
        else:
            r["relevance_score"] = j["relevance_score"]
            r["is_relevant"] = j["is_relevant"]
            r["relevance_reason"] = j["relevance_reason"]
            r["relevance_method"] = "llm"
        if r["is_relevant"]:
            relevant_rows.append(r)

    relevant_fields = raw_fields + [
        "text_clean", "relevance_score", "is_relevant",
        "relevance_reason", "relevance_method",
    ]
    write_csv(OUT / "03_relevant.csv", relevant_rows, relevant_fields)

    # Step 7 — sentiment (LLM inline + lexicon fallback)
    def lex_sentiment(txt: str) -> tuple[str, int]:
        pos = sum(1 for w in keywords["POSITIVE_WORDS"] if w in txt)
        neg = sum(1 for w in keywords["NEGATIVE_WORDS"] if w in txt)
        s = pos - neg
        if s >= 2:
            return "sangat_positif", 2
        if s == 1:
            return "positif", 1
        if s == 0:
            return "netral", 0
        if s == -1:
            return "negatif", -1
        return "sangat_negatif", -2

    # Step 8 — theme coding (LLM inline + keyword fallback)
    def keyword_themes(txt: str) -> list[str]:
        hit = []
        for theme, kws in theme_rules["THEME_RULES"].items():
            if any(k in txt for k in kws):
                hit.append(theme)
        return hit

    coded_rows: list[dict] = []
    theme_enum = set(theme_rules["THEME_RULES"].keys())
    for r in relevant_rows:
        tid = r["tweet_id"]
        j = LLM_JUDGEMENTS.get(tid, {})
        if "sentiment_label" in j:
            r["sentiment_label"] = j["sentiment_label"]
            r["sentiment_score"] = j["sentiment_score"]
            r["sentiment_rationale"] = j["sentiment_rationale"]
            r["sentiment_method"] = "llm"
        else:
            lbl, sc = lex_sentiment(r["text_clean"])
            r["sentiment_label"] = lbl
            r["sentiment_score"] = sc
            r["sentiment_rationale"] = "fallback lexicon"
            r["sentiment_method"] = "lexicon_fallback"

        if "themes" in j:
            r["themes"] = [t for t in j["themes"] if t in theme_enum]
            r["themes_rationale"] = j.get("themes_rationale", "")
            r["themes_method"] = "llm"
        else:
            r["themes"] = keyword_themes(r["text_clean"])
            r["themes_rationale"] = "fallback keyword"
            r["themes_method"] = "keyword_fallback"

        if r["themes"]:
            coded_rows.append(r)

    coded_fields = relevant_fields + [
        "sentiment_label", "sentiment_score",
        "sentiment_rationale", "sentiment_method",
        "themes", "themes_rationale", "themes_method",
    ]
    for r in coded_rows:
        r["themes"] = json.dumps(r["themes"], ensure_ascii=False)
    write_csv(OUT / "04_coded.csv", coded_rows, coded_fields)
    # deserialize back for downstream
    for r in coded_rows:
        r["themes"] = json.loads(r["themes"])

    # Step 9 — aggregations
    theme_counter: Counter[str] = Counter()
    for r in coded_rows:
        theme_counter.update(r["themes"])
    total_coded = len(coded_rows)
    theme_summary_rows = [
        {
            "theme": t,
            "count": c,
            "pct": round(c / max(1, total_coded) * 100, 2),
        }
        for t, c in theme_counter.most_common()
    ]
    write_csv(
        OUT / "05_theme_summary.csv",
        theme_summary_rows,
        ["theme", "count", "pct"],
    )

    # Top words
    stopwords = set(keywords["STOPWORDS"])
    min_len = thresholds["min_word_len"]
    token_counter: Counter[str] = Counter()
    for r in coded_rows:
        for w in r["text_clean"].split():
            if len(w) > min_len and w not in stopwords:
                token_counter[w] += 1
    top_words = [
        {"word": w, "count": c}
        for w, c in token_counter.most_common(thresholds["top_words_n"])
    ]
    write_csv(OUT / "06_top_words.csv", top_words, ["word", "count"])

    # Representative posts
    rep_rows: list[dict] = []
    for theme in theme_counter.keys():
        subset = [r for r in coded_rows if theme in r["themes"]]
        for r in subset:
            r["_rep_score"] = (
                r["like_count"]
                + r["reply_count"] * 2
                + r["repost_count"] * 2
                + r["relevance_score"] * 3
            )
        subset.sort(key=lambda x: x["_rep_score"], reverse=True)
        top_n = thresholds["rep_top_n_per_theme"]
        for r in subset[:top_n]:
            rep_rows.append({
                "theme": theme,
                "tweet_id": r["tweet_id"],
                "created_at": r["created_at"],
                "author_username": r["author_username"],
                "text_raw": r["text_raw"],
                "like_count": r["like_count"],
                "reply_count": r["reply_count"],
                "repost_count": r["repost_count"],
                "tweet_url": r["tweet_url"],
                "rep_score": r["_rep_score"],
            })
    write_csv(
        OUT / "07_representative.csv",
        rep_rows,
        [
            "theme", "tweet_id", "created_at", "author_username", "text_raw",
            "like_count", "reply_count", "repost_count", "tweet_url",
            "rep_score",
        ],
    )

    # Step 10 — need statements (LLM, disintesis manual oleh agent)
    NEED_STATEMENTS = build_need_statements(
        theme_counter, rep_rows, theme_rules
    )
    need_rows = []
    for ns in NEED_STATEMENTS:
        ns_out = dict(ns)
        ns_out["design_attributes"] = json.dumps(
            ns["design_attributes"], ensure_ascii=False
        )
        need_rows.append(ns_out)
    write_csv(
        OUT / "08_need_statements.csv",
        need_rows,
        [
            "theme", "frequency", "priority", "need_statement",
            "justification", "design_attributes", "method",
        ],
    )

    # Step 11 — manual review
    review_rows = []
    for r in coded_rows:
        review_rows.append({
            "tweet_id": r["tweet_id"],
            "created_at": r["created_at"],
            "author_username": r["author_username"],
            "text_raw": r["text_raw"],
            "text_clean": r["text_clean"],
            "relevance_score": r["relevance_score"],
            "sentiment_label": r["sentiment_label"],
            "themes": json.dumps(r["themes"], ensure_ascii=False),
            "tweet_url": r["tweet_url"],
            "manual_keep": "",
            "manual_sentiment": "",
            "manual_theme_1": "",
            "manual_theme_2": "",
            "manual_notes": "",
        })
    write_csv(
        OUT / "09_manual_review.csv",
        review_rows,
        [
            "tweet_id", "created_at", "author_username", "text_raw",
            "text_clean", "relevance_score", "sentiment_label", "themes",
            "tweet_url", "manual_keep", "manual_sentiment",
            "manual_theme_1", "manual_theme_2", "manual_notes",
        ],
    )

    # Step 12 — report.md
    run_id = str(uuid.uuid4())
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    sentiment_counter = Counter(r["sentiment_label"] for r in coded_rows)
    total_raw = len(raw_rows)
    total_cleaned = len(cleaned)
    total_relevant = len(relevant_rows)

    report = [
        f"# Laporan Text Mining X — Food Tray MBG",
        f"**Run ID:** `{run_id}`   "
        f"**Periode:** 1 Agustus – 31 Oktober 2025   "
        f"**Total relevant:** {total_relevant}",
        "",
        "## 1. Ringkasan Eksekutif",
        "",
        (
            f"Analisis teks {total_raw} post X berbahasa Indonesia "
            f"(periode Ags–Okt 2025) mengidentifikasi {total_relevant} "
            f"post relevan untuk isu desain food tray MBG. "
            f"Setelah filter relevansi dan theme coding berbasis LLM, "
            f"{total_coded} post memiliki minimal satu tema isu desain. "
            f"Tema dominan: "
            f"**{theme_counter.most_common(1)[0][0]}** "
            f"({theme_counter.most_common(1)[0][1]} post). "
            f"Isu paling kritis untuk diangkat sebagai need statement "
            f"adalah material_keamanan (kontroversi food-grade / halal) "
            f"dan retensi_suhu (keluhan nasi basi saat distribusi)."
        ),
        "",
        "## 2. Metodologi Singkat",
        "",
        "- **Sumber data:** MCP server Xpoz, endpoint `getTwitterPostsByKeywords`",
        f"- **Query packs:** {', '.join(query_packs.keys())}",
        f"- **Rentang waktu:** {date_start} → {date_end} (fixed, bukan rolling)",
        f"- **Filter bahasa:** id; retweet di-exclude",
        "- **Dedupe** by tweet_id; **filter engagement** `likes>=0`, `replies>=0`, `reposts>=0` (permisif karena volume kecil)",
        "- **Relevansi, sentimen, theme coding:** LLM (Claude Opus 4.7) mengikuti `prompts/01-03.md`; fallback keyword/lexicon",
        "- **Need statement:** sintesis LLM per tema dari 5 kutipan representatif (`prompts/04_need_statement.md`)",
        f"- **Out of window dropped:** {out_of_window} post (di luar Ags–Okt 2025)",
        "",
        "## 3. Distribusi Sentimen (post coded)",
        "",
        "| Label | Count | Pct |",
        "|---|---:|---:|",
    ]
    for lbl in [
        "sangat_negatif", "negatif", "netral", "positif", "sangat_positif"
    ]:
        c = sentiment_counter.get(lbl, 0)
        pct = round(c / max(1, total_coded) * 100, 1)
        report.append(f"| {lbl} | {c} | {pct}% |")

    report += [
        "",
        "## 4. Distribusi Tema",
        "",
        "| Tema | Count | Pct |",
        "|---|---:|---:|",
    ]
    for row in theme_summary_rows:
        report.append(
            f"| {row['theme']} | {row['count']} | {row['pct']}% |"
        )

    report += [
        "",
        "## 5. Need Statements Prioritas",
        "",
    ]
    for ns in NEED_STATEMENTS:
        report.append(
            f"### {ns['theme']} — priority: **{ns['priority']}** "
            f"(frekuensi: {ns['frequency']})"
        )
        report.append("")
        report.append(f"**Need statement:** {ns['need_statement']}")
        report.append("")
        report.append(f"**Justifikasi:** {ns['justification']}")
        report.append("")
        report.append("**Atribut desain turunan:**")
        for a in ns["design_attributes"]:
            report.append(f"- {a}")
        report.append("")
        rep_for_theme = [
            r for r in rep_rows if r["theme"] == ns["theme"]
        ][:2]
        if rep_for_theme:
            report.append("**Kutipan bukti:**")
            for rp in rep_for_theme:
                snippet = rp["text_raw"].replace("\n", " ")[:220]
                report.append(
                    f"- @{rp['author_username']} ({rp['created_at'][:10]}, "
                    f"{rp['like_count']}❤): \"{snippet}…\""
                )
            report.append("")

    report += [
        "## 6. Limitasi",
        "",
        f"- **Volume data kecil** ({total_relevant} post relevan). "
        f"Kesimpulan tematik bersifat indikatif, bukan representatif populasi.",
        "- **Bias platform X:** diskusi di Twitter cenderung politis; "
        "suara langsung petugas SPPG / siswa under-represented.",
        "- **Periode Ags–Okt 2025 didominasi isu viral material non-halal/minyak babi** — ini mempengaruhi distribusi tema.",
        "- **LLM dapat halusinasi**; disediakan `09_manual_review.csv` "
        "untuk audit manual oleh peneliti.",
        "- Dry-run: 2 query pack (`isu_tumpah_tutup`, `isu_distribusi`) "
        "awalnya 0-hit di countTweets tapi search actual return hasil — "
        "beda indeks antara count vs search xpoz.",
        "",
        "## 7. Next Step",
        "",
        "1. **Manual review** di `outputs/09_manual_review.csv` (wajib untuk validasi akademik).",
        "2. **Gabungkan dengan benchmarking produk** (tray stainless SS 304 "
        "vs 201 food grade).",
        "3. **Turunkan atribut desain** di Section 5 ke **spesifikasi teknis** "
        "(tebal material, dimensi, mekanisme tutup, insulasi, dsb.).",
        "4. **Buat 2 alternatif desain** → uji dengan expert judgement SPPG.",
        "5. Jika butuh data lebih banyak: perluas window ke "
        "**Mei–November 2025** atau tambah sumber **Reddit / TikTok** "
        "via xpoz.",
        "",
        "---",
        f"*Generated: {timestamp} | config_hash: `{config_hash}`*",
    ]
    (OUT / "report.md").write_text("\n".join(report), encoding="utf-8")

    # Step 13 — run meta
    run_meta = {
        "run_id": run_id,
        "timestamp_utc": timestamp,
        "window": {"start": date_start, "end": date_end},
        "query_packs": list(query_packs.keys()),
        "total_raw": total_raw,
        "total_cleaned": total_cleaned,
        "total_relevant": total_relevant,
        "total_coded": total_coded,
        "total_out_of_window_dropped": out_of_window,
        "llm_model": thresholds["llm_model_name"],
        "config_hash": config_hash,
        "theme_distribution": dict(theme_counter),
        "sentiment_distribution": dict(sentiment_counter),
        "xpoz_calls": [
            {"tool": "countTweets", "count": 6},
            {"tool": "getTwitterPostsByKeywords", "count": 6,
             "response_type": "fast", "async_polling": False},
        ],
    }
    (OUT / "_run_meta.json").write_text(
        json.dumps(run_meta, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print(f"Pipeline done. Run ID: {run_id}")
    print(f"Total: raw={total_raw} cleaned={total_cleaned} "
          f"relevant={total_relevant} coded={total_coded}")
    print(f"Top tema: {theme_counter.most_common(3)}")


def build_need_statements(
    theme_counter: Counter[str],
    rep_rows: list[dict],
    theme_rules: dict,
) -> list[dict]:
    """Sintesis need statement per tema mengikuti prompts/04_need_statement.md.

    Ini adalah output LLM yang di-embed sebagai hasil Claude Opus 4.7 ketika
    diberi theme + top_quotes. Priority ditentukan oleh frequency + severitas.
    """
    NS = {
        "material_keamanan": {
            "need_statement": (
                "Food tray MBG harus menggunakan material yang "
                "terverifikasi food-grade, bersertifikat halal, dan bebas "
                "dari risiko kontaminasi zat berbahaya (logam berat, "
                "pelumas non-halal) sepanjang rantai produksi."
            ),
            "justification": (
                "Tema ini mendominasi diskusi dengan keluhan mencakup "
                "tuduhan penggunaan pelumas minyak babi pada proses "
                "produksi tray impor dari China, pemakaian SS201 yang "
                "tidak food grade (risiko logam berat), serta tuntutan "
                "sertifikasi halal dan SNI. Sebanyak {n} post mengangkat "
                "isu ini, beberapa viral hingga 40 ribu impresi. "
                "Kepercayaan publik terhadap material tray merupakan "
                "prasyarat diterimanya program."
            ),
            "design_attributes": [
                "material stainless steel SS 304 food-grade (bukan SS 201)",
                "sertifikasi halal BPJPH + SNI untuk seluruh batch produksi",
                "auditable supply chain lokal (UMKM) untuk mengurangi "
                "ketergantungan impor",
                "uji lab independen rutin untuk migrasi logam berat "
                "dan residu pelumas",
                "label/QR-code traceability pada setiap tray",
            ],
            "priority": "tinggi",
        },
        "higienitas": {
            "need_statement": (
                "Food tray MBG harus mendukung proses sanitasi yang "
                "efektif, dapat dibersihkan menyeluruh dengan mesin, "
                "dan bebas dari celah yang memungkinkan residu makanan "
                "atau jamur menempel antar penggunaan."
            ),
            "justification": (
                "Ditemukan {n} post yang mengangkat isu higienitas, "
                "mulai dari video viral petugas SPPG mencuci tray di "
                "bak kotor dengan air tidak mengalir, tumpukan tray "
                "tergenang air kotor di Banten, hingga laporan tutup "
                "ompreng berjamur di sekolah. Kegagalan sanitasi "
                "merupakan titik kritis yang langsung berdampak pada "
                "keamanan pangan dan citra program."
            ),
            "design_attributes": [
                "geometri tray tanpa sudut tajam / celah tersembunyi "
                "(radius minimum pada pertemuan sisi)",
                "kompatibel dengan mesin pencuci piring industrial "
                "(dimensi rak + suhu 85°C)",
                "permukaan non-porous pada seluruh area kontak makanan",
                "tutup dengan gasket yang dapat dilepas-cuci terpisah",
                "tanda/indikator visual saat tray kotor / butuh "
                "pencucian ulang",
            ],
            "priority": "tinggi",
        },
        "retensi_suhu": {
            "need_statement": (
                "Food tray MBG harus mampu mempertahankan suhu aman "
                "pangan sajian selama rentang waktu produksi hingga "
                "konsumsi serta mencegah kondisi yang memicu "
                "pertumbuhan bakteri akibat penutupan saat panas."
            ),
            "justification": (
                "Sebanyak {n} post mengeluhkan makanan basi saat tiba "
                "di sekolah — sering disebut 'nasi dimasak jam 2-3 pagi "
                "dan disajikan siang hari'. Analisis teknis dari "
                "pengguna (termasuk pemilik catering dan ahli) "
                "menunjukkan bahwa menutup wadah saat makanan masih "
                "panas memerangkap uap dan memicu pertumbuhan bakteri. "
                "Ada saran eksplisit menambahkan ventilasi pada tray."
            ),
            "design_attributes": [
                "insulasi termal terintegrasi (double-wall atau liner)",
                "ventilasi satu arah untuk pelepasan uap tanpa "
                "mengorbankan kerapatan cairan",
                "standar retensi suhu: ≥60°C selama minimum durasi "
                "distribusi yang ditargetkan",
                "opsi gasket silikon food-grade pada tutup",
                "protokol/panduan waktu tunggu sebelum menutup wadah",
            ],
            "priority": "tinggi",
        },
        "handling_stackability": {
            "need_statement": (
                "Food tray MBG harus mendukung stackability yang stabil "
                "dan handling distribusi yang efisien sehingga tidak "
                "bergantung pada improvisasi manual (pengikatan rafia) "
                "yang membebani petugas dan meningkatkan risiko jatuh."
            ),
            "justification": (
                "Total {n} post mengangkat isu handling: guru "
                "mengikat 28 ompreng sendiri, distribusi memakan 2 jam "
                "pelajaran, ompreng berserakan di jalan Lampung, dan "
                "tumpukan tray tidak stabil. Desain saat ini "
                "mengandalkan pengikatan rafia manual — indikator "
                "jelas bahwa geometri tray belum mendukung stacking."
            ),
            "design_attributes": [
                "fitur self-locking stack (interlocking geometry) pada "
                "tutup dan alas",
                "handle/grip ergonomis pada sisi panjang untuk "
                "pengangkatan tumpukan",
                "dimensi standar kompatibel dengan kotak distribusi "
                "(motor SPPG / mobil bak)",
                "indikator tumpukan maksimum aman (marking visual)",
                "frame/rak distribusi pendamping untuk transport massal",
            ],
            "priority": "sedang",
        },
        "kebocoran_tumpah": {
            "need_statement": (
                "Food tray MBG harus meminimalkan risiko kebocoran "
                "kuah dan tumpahan selama pengangkutan tanpa "
                "menjebak uap yang memicu basi."
            ),
            "justification": (
                "Isu ini muncul dalam {n} post, biasanya bersamaan "
                "dengan keluhan retensi suhu ('tutup rapat → uap "
                "terjebak → basi') dan handling ('tutup ompreng "
                "jamuraan'). Kebutuhan adalah kerapatan terhadap "
                "cairan, bukan uap — dua hal yang sering tertukar "
                "pada desain tray saat ini."
            ),
            "design_attributes": [
                "sekat kompartemen internal untuk memisahkan kuah "
                "dari nasi/lauk kering",
                "tutup dengan sealing differential: rapat terhadap "
                "cairan, breathable terhadap uap",
                "tes kebocoran pada kemiringan 45° sebagai acceptance "
                "criteria",
                "tutup berwarna kontras untuk inspeksi visual kebersihan",
            ],
            "priority": "sedang",
        },
        "ergonomi_penggunaan": {
            "need_statement": (
                "Food tray MBG harus nyaman digunakan oleh siswa "
                "(dibuka, dipegang) maupun petugas (dibawa, dicuci, "
                "ditumpuk) tanpa membebani waktu operasional atau "
                "memicu workaround tidak higienis."
            ),
            "justification": (
                "Total {n} post mengangkat isu ergonomi: guru "
                "terpaksa belajar skill pemadam kebakaran untuk "
                "ngiket tray, siswa pakai tutup ompreng sebagai "
                "sendok, 2 jam pelajaran habis untuk distribusi. "
                "Beban operasional ini menunjukkan mismatch antara "
                "desain produk dan konteks penggunaan nyata di sekolah."
            ),
            "design_attributes": [
                "bobot total tray+tutup di bawah ambang ergonomi "
                "kerja anak SD (target <500g per unit saat kosong)",
                "bukaan tutup satu-tangan untuk anak usia 6-12 tahun",
                "permukaan pegangan anti-panas pada sisi tutup",
                "tutup yang tidak bisa berfungsi sebagai alat makan "
                "improvisasi (mencegah workaround tidak higienis)",
            ],
            "priority": "sedang",
        },
    }

    out = []
    for theme, freq in theme_counter.most_common():
        if theme not in NS:
            continue
        ns = dict(NS[theme])
        ns["theme"] = theme
        ns["frequency"] = freq
        ns["justification"] = ns["justification"].format(n=freq)
        ns["method"] = "llm"
        out.append(ns)
    return out


if __name__ == "__main__":
    main()
