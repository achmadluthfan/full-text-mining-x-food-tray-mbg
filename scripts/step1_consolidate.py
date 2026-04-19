"""
Step 1 — Consolidate raw data dari CSV staging + YAML fast-mode responses.

Output:
    outputs/01_general_raw.csv        (Corpus A — MBG umum)
    outputs/02_tray_raw.csv           (Corpus B — Food Tray)
    outputs/00_general_query_stats.csv
    outputs/00_tray_query_stats.csv
"""

from __future__ import annotations

import csv
import re
from pathlib import Path
from typing import Any

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
STAGING = OUT / "_staging"
AGENT_TOOLS = Path("/Users/mymac/.cursor/projects/Users-mymac-Code-scrapping-mbg/agent-tools")

# ---------------------------------------------------------------------------
# Mapping: pack_name -> list of source files
# ---------------------------------------------------------------------------
GENERAL_PACKS = {
    "mbg_umum_phrase":   {
        "csv": STAGING / "gen_mbg_umum_phrase.csv",
        "yaml": [],
    },
    "mbg_umum_short":    {
        "csv": STAGING / "gen_mbg_umum_short.csv",
        "yaml": [],
    },
    "mbg_umum_context":  {
        "csv": STAGING / "gen_mbg_umum_context.csv",
        "yaml": [],
    },
}

TRAY_PACKS = {
    "tray_umum_objek":    {
        "csv": STAGING / "tray_umum_objek.csv",
        "yaml": [AGENT_TOOLS / "efbf12c5-891a-4863-bd8f-3b5e3aa66d38.txt"],
    },
    "tray_suhu_basi":     {
        "csv": STAGING / "tray_suhu_basi.csv",
        "yaml": [AGENT_TOOLS / "56f8029b-71c5-42a7-9258-c88d4fc869ce.txt"],
    },
    "tray_tumpah_tutup":  {
        "csv": STAGING / "tray_tumpah_tutup.csv",
        "yaml": [],
    },
    "tray_material":      {
        "csv": STAGING / "tray_material.csv",
        "yaml": [AGENT_TOOLS / "70e26532-f258-4b6b-ab87-ae2f7c727748.txt"],
    },
    "tray_distribusi":    {
        "csv": STAGING / "tray_distribusi.csv",
        "yaml": [],
    },
    "tray_higienitas":    {
        "csv": STAGING / "tray_higienitas.csv",
        "yaml": [],
    },
}

# Bahasa Indonesia (Twitter API mengembalikan 'in' atau 'id')
ID_LANGS = {"id", "in", "ind", "Indonesian"}

# Kolom standar untuk raw output
STD_COLS = [
    "id", "text", "author_username", "author_id",
    "created_at", "like_count", "reply_count", "retweet_count",
    "quote_count", "bookmark_count", "impression_count",
    "lang", "conversation_id", "hashtags", "mentions",
    "x_fetched_at", "source_pack", "source_type",
]


def _read_csv(path: Path, pack: str) -> pd.DataFrame:
    if not path.exists() or path.stat().st_size < 50:
        return pd.DataFrame(columns=STD_COLS)
    with open(path, encoding="utf-8", errors="replace") as f:
        df = pd.read_csv(f, dtype=str, keep_default_na=False)
    if df.empty:
        return pd.DataFrame(columns=STD_COLS)
    df["source_pack"] = pack
    df["source_type"] = "csv"
    for c in STD_COLS:
        if c not in df.columns:
            df[c] = ""
    return df[STD_COLS]


FIELD_MAP = {
    "id": "id",
    "text": "text",
    "authorUsername": "author_username",
    "authorId": "author_id",
    "createdAt": "created_at",
    "likeCount": "like_count",
    "replyCount": "reply_count",
    "retweetCount": "retweet_count",
    "quoteCount": "quote_count",
    "bookmarkCount": "bookmark_count",
    "impressionCount": "impression_count",
    "lang": "lang",
    "conversationId": "conversation_id",
}

_KV_RE = re.compile(r'^\s{6}([A-Za-z]+):\s*(.*?)\s*$')
_REC_START_RE = re.compile(r'^\s{4}-\s+id:\s*"?([^"\n]+?)"?\s*$')


def _strip_yaml_val(raw: str) -> str:
    """Strip quotes; unescape sederhana untuk YAML scalar."""
    s = raw.strip()
    if not s:
        return ""
    if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
        s = s[1:-1]
    return s.replace('\\n', '\n').replace('\\"', '"').replace("\\'", "'")


def _yaml_to_df(path: Path, pack: str) -> pd.DataFrame:
    """
    Custom parser untuk format YAML-ish dari xpoz MCP.
    Records dimulai dengan `    - id: "..."` dan field anak indented 6 spasi.
    Field array (hashtags[N], mentions[N]) di-skip karena tidak relevan untuk text mining.
    """
    if not path.exists():
        return pd.DataFrame(columns=STD_COLS)
    rows: list[dict[str, Any]] = []
    cur: dict[str, Any] | None = None

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            m_start = _REC_START_RE.match(line)
            if m_start:
                if cur is not None:
                    rows.append(cur)
                cur = {col: "" for col in STD_COLS}
                cur["id"] = m_start.group(1)
                cur["source_pack"] = pack
                cur["source_type"] = "yaml_fast"
                continue
            if cur is None:
                continue
            m_kv = _KV_RE.match(line)
            if not m_kv:
                continue
            key = m_kv.group(1)
            if key not in FIELD_MAP:
                continue
            col = FIELD_MAP[key]
            cur[col] = _strip_yaml_val(m_kv.group(2))
    if cur is not None:
        rows.append(cur)

    return pd.DataFrame(rows, columns=STD_COLS) if rows else pd.DataFrame(columns=STD_COLS)


def _load_corpus(packs: dict) -> tuple[pd.DataFrame, list[dict]]:
    frames: list[pd.DataFrame] = []
    stats: list[dict] = []
    for pack_name, sources in packs.items():
        pack_frames = [_read_csv(sources["csv"], pack_name)]
        for yp in sources["yaml"]:
            pack_frames.append(_yaml_to_df(yp, pack_name))
        df_pack = pd.concat(pack_frames, ignore_index=True)
        n_total = len(df_pack)
        n_id = (df_pack["lang"].isin(ID_LANGS)).sum() if n_total else 0
        df_id = df_pack[df_pack["lang"].isin(ID_LANGS)].copy()
        df_id_uniq = df_id.drop_duplicates(subset=["id"]).copy()
        n_uniq = len(df_id_uniq)
        stats.append({
            "pack": pack_name,
            "total_rows_fetched": n_total,
            "rows_lang_id": int(n_id),
            "rows_lang_id_unique": n_uniq,
        })
        frames.append(df_id_uniq)
    if not frames:
        return pd.DataFrame(columns=STD_COLS), stats
    df_all = pd.concat(frames, ignore_index=True)
    # Dedupe global by id (1 tweet bisa muncul di > 1 pack -> ambil pack pertama)
    df_all = df_all.drop_duplicates(subset=["id"], keep="first").reset_index(drop=True)
    return df_all, stats


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    print("[Step 1] Consolidating Corpus A (general / MBG umum)...")
    df_general, stats_general = _load_corpus(GENERAL_PACKS)
    df_general.to_csv(OUT / "01_general_raw.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(stats_general).to_csv(OUT / "00_general_query_stats.csv", index=False)
    print(f"  -> {len(df_general)} unique Indonesian rows -> outputs/01_general_raw.csv")

    print("[Step 1] Consolidating Corpus B (tray / food tray)...")
    df_tray, stats_tray = _load_corpus(TRAY_PACKS)
    df_tray.to_csv(OUT / "02_tray_raw.csv", index=False, quoting=csv.QUOTE_MINIMAL)
    pd.DataFrame(stats_tray).to_csv(OUT / "00_tray_query_stats.csv", index=False)
    print(f"  -> {len(df_tray)} unique Indonesian rows -> outputs/02_tray_raw.csv")

    # Cek overlap antar corpus (informational)
    overlap = set(df_general["id"]) & set(df_tray["id"])
    print(f"\n[Step 1] Overlap antara general & tray: {len(overlap)} tweets")
    print("[Step 1] Per-pack stats:")
    for s in stats_general + stats_tray:
        print(f"  {s['pack']:30s} fetched={s['total_rows_fetched']:5d} "
              f"lang_id={s['rows_lang_id']:5d} unique={s['rows_lang_id_unique']:5d}")


if __name__ == "__main__":
    main()
