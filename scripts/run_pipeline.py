"""
MBG Food Tray — X Text Mining Pipeline (BERTopic edition).

Mengeksekusi WORKFLOW_bertopic.md Step 5-17 dengan data hasil
`step1_consolidate.py` (outputs/01_general_raw.csv + 02_tray_raw.csv).

Tidak ada LLM. Semua deterministik:
- Preprocessing  : regex + Sastrawi stem
- Issue ranking  : keyword dictionary
- Sentiment      : lexicon (pos/neg)
- N-gram         : sklearn CountVectorizer
- Co-occurrence  : auto-vocab + design terms
- Topic modeling : BERTopic multilingual + KeyBERT representation
- Need statement : rule-based template (config/need_templates.yaml)
"""

from __future__ import annotations

import hashlib
import json
import re
import uuid
import warnings
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import yaml

warnings.filterwarnings("ignore")

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "outputs"
CFG = ROOT / "config"

# ---------------------------------------------------------------------------
# Step 1 — Load konfigurasi + config_hash
# ---------------------------------------------------------------------------

def _read_yaml(name: str) -> dict[str, Any]:
    return yaml.safe_load((CFG / name).read_text(encoding="utf-8"))


def _config_hash() -> str:
    h = hashlib.sha256()
    for fn in sorted([
        "query_packs.yaml", "keywords.yaml", "thresholds.yaml",
        "need_templates.yaml",
    ]):
        h.update((CFG / fn).read_bytes())
    return h.hexdigest()[:16]


print("[Cfg] Loading config files...")
QUERY_PACKS  = _read_yaml("query_packs.yaml")
KEYWORDS     = _read_yaml("keywords.yaml")
THRESHOLDS   = _read_yaml("thresholds.yaml")
NEED_TPL_CFG = _read_yaml("need_templates.yaml")

STOPWORDS       = set(KEYWORDS.get("STOPWORDS", []))
POSITIVE_WORDS  = list(KEYWORDS.get("POSITIVE_WORDS", []))
NEGATIVE_WORDS  = list(KEYWORDS.get("NEGATIVE_WORDS", []))
ISSUE_DICT      = KEYWORDS.get("ISSUE_DICT", {})
DESIGN_TERMS    = list(KEYWORDS.get("DESIGN_TERMS", []))
NEED_TEMPLATES  = NEED_TPL_CFG.get("NEED_TEMPLATES", [])
DEFAULT_NEED    = NEED_TPL_CFG.get(
    "DEFAULT_NEED_STATEMENT",
    "Food tray harus dirancang agar lebih sesuai dengan kebutuhan distribusi MBG.",
)
CONFIG_HASH     = _config_hash()
RUN_ID          = str(uuid.uuid4())
TIMESTAMP_UTC   = datetime.now(timezone.utc).isoformat()
print(f"[Cfg] config_hash={CONFIG_HASH} run_id={RUN_ID}")


# ---------------------------------------------------------------------------
# Helpers — normalisasi kolom raw → skema internal
# ---------------------------------------------------------------------------

def _to_int(s: Any) -> int:
    try:
        return int(float(str(s).strip()))
    except Exception:
        return 0


def normalize_raw(df_raw: pd.DataFrame, query_group: str) -> pd.DataFrame:
    """Map kolom xpoz → skema internal yang dipakai oleh notebook reference."""
    out = pd.DataFrame()
    out["tweet_id"]        = df_raw["id"].astype(str)
    out["text_raw"]        = df_raw["text"].fillna("").astype(str)
    out["author_username"] = df_raw["author_username"].fillna("").astype(str)
    out["author_id"]       = df_raw["author_id"].fillna("").astype(str)
    out["created_at"]      = df_raw["created_at"].fillna("").astype(str)
    out["like_count"]      = df_raw["like_count"].apply(_to_int)
    out["reply_count"]     = df_raw["reply_count"].apply(_to_int)
    out["repost_count"]    = df_raw["retweet_count"].apply(_to_int)
    out["quote_count"]     = df_raw["quote_count"].apply(_to_int)
    out["bookmark_count"]  = df_raw["bookmark_count"].apply(_to_int)
    out["impression_count"] = df_raw["impression_count"].apply(_to_int)
    out["lang"]            = df_raw["lang"].fillna("").astype(str)
    out["query_group"]     = query_group
    out["query_label"]     = df_raw.get("source_pack", "").fillna("").astype(str)
    out["tweet_url"]       = (
        "https://x.com/" + out["author_username"].astype(str)
        + "/status/" + out["tweet_id"]
    )
    return out


# ---------------------------------------------------------------------------
# Step 5 — Preprocessing (regex + Sastrawi)
# ---------------------------------------------------------------------------

print("[Step 5] Initializing Sastrawi stemmer...")
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory  # noqa: E402

_STEMMER = StemmerFactory().create_stemmer()
_MIN_TOK = THRESHOLDS["preprocess"]["min_token_len"]


def clean_text(text: str) -> str:
    text = (text or "").lower()
    text = re.sub(r"http\S+|www\S+", " ", text)
    text = re.sub(r"@\w+", " ", text)
    text = re.sub(r"#", "", text)
    text = re.sub(r"&amp;", " ", text)
    text = re.sub(r"[^a-zA-Z\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(t: str) -> list[str]:
    return [w for w in t.split() if len(w) >= _MIN_TOK and w not in STOPWORDS]


def stem_tokens(tokens: list[str]) -> list[str]:
    return [_STEMMER.stem(t) for t in tokens]


def prep_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["text_clean"]  = out["text_raw"].apply(clean_text)
    out["tokens"]      = out["text_clean"].apply(tokenize)
    out["tokens_stem"] = out["tokens"].apply(stem_tokens)
    out["text_joined"] = out["tokens_stem"].apply(lambda toks: " ".join(toks))
    out = out[out["text_joined"].str.len() > 0]
    if THRESHOLDS["preprocess"].get("dedupe_by_text_joined", True):
        out = out.drop_duplicates(subset=["text_joined"])
    return out.reset_index(drop=True)


# ---------------------------------------------------------------------------
# Step 6 — Issue ranking Corpus A
# ---------------------------------------------------------------------------

def count_issue_hits(text: str, issue_dict: dict[str, list[str]]) -> list[str]:
    return [issue for issue, kws in issue_dict.items() if any(kw in text for kw in kws)]


def issue_ranking(general_pp: pd.DataFrame) -> pd.DataFrame:
    general_pp["issue_hits"] = general_pp["text_clean"].apply(
        lambda x: count_issue_hits(x, ISSUE_DICT)
    )
    counter: Counter = Counter()
    for lst in general_pp["issue_hits"]:
        counter.update(lst)
    coded_n = (general_pp["issue_hits"].apply(len) > 0).sum()
    df = pd.DataFrame(
        [{"issue": k, "tweet_count": v} for k, v in counter.items()]
    ).sort_values("tweet_count", ascending=False).reset_index(drop=True)
    df["share_of_issue_coded_tweets_pct"] = (
        df["tweet_count"] / max(1, coded_n) * 100
    ).round(2)
    df["rank"] = range(1, len(df) + 1)
    return df[["rank", "issue", "tweet_count", "share_of_issue_coded_tweets_pct"]]


# ---------------------------------------------------------------------------
# Step 8 — Sentimen lexicon
# ---------------------------------------------------------------------------

def sentiment_score(text: str) -> int:
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    return pos - neg


def sentiment_label(score: int) -> str:
    if score > 0:
        return "positif"
    if score < 0:
        return "negatif"
    return "netral"


# ---------------------------------------------------------------------------
# Step 9 — N-gram analysis
# ---------------------------------------------------------------------------

def get_top_ngrams(text_series: pd.Series, ngram_range=(2, 2),
                   top_n: int = 30, min_df: int = 2) -> pd.DataFrame:
    from sklearn.feature_extraction.text import CountVectorizer
    texts = text_series.fillna("").astype(str).tolist()
    if not texts or all(not t.strip() for t in texts):
        return pd.DataFrame(columns=["ngram", "count"])
    try:
        vec = CountVectorizer(ngram_range=ngram_range, min_df=min_df)
        X = vec.fit_transform(texts)
    except ValueError:
        return pd.DataFrame(columns=["ngram", "count"])
    terms = vec.get_feature_names_out()
    counts = np.asarray(X.sum(axis=0)).ravel()
    df = pd.DataFrame({"ngram": terms, "count": counts.astype(int)})
    return df.sort_values("count", ascending=False).reset_index(drop=True).head(top_n)


# ---------------------------------------------------------------------------
# Step 10 — Co-occurrence
# ---------------------------------------------------------------------------

def build_cooccurrence_from_docs(text_series: pd.Series,
                                  min_df: int = 3,
                                  max_features: int = 20) -> pd.DataFrame:
    from sklearn.feature_extraction.text import CountVectorizer
    texts = text_series.fillna("").astype(str).tolist()
    try:
        vec = CountVectorizer(ngram_range=(1, 1), min_df=min_df,
                              max_features=max_features, binary=True)
        X = vec.fit_transform(texts)
    except ValueError:
        return pd.DataFrame()
    terms = vec.get_feature_names_out()
    co = (X.T @ X).toarray()
    np.fill_diagonal(co, 0)
    return pd.DataFrame(co, index=terms, columns=terms)


def extract_top_pairs(co_df: pd.DataFrame, top_n: int = 30) -> pd.DataFrame:
    if co_df.empty:
        return pd.DataFrame(columns=["term_1", "term_2", "cooccurrence_count"])
    rows = []
    terms = list(co_df.index)
    for i in range(len(terms)):
        for j in range(i + 1, len(terms)):
            c = int(co_df.iloc[i, j])
            if c > 0:
                rows.append({"term_1": terms[i], "term_2": terms[j],
                             "cooccurrence_count": c})
    if not rows:
        return pd.DataFrame(columns=["term_1", "term_2", "cooccurrence_count"])
    return (pd.DataFrame(rows)
            .sort_values("cooccurrence_count", ascending=False)
            .reset_index(drop=True)
            .head(top_n))


def build_keyword_cooccurrence(df_in: pd.DataFrame,
                                terms: list[str]) -> pd.DataFrame:
    pair_rows: list[tuple[str, str]] = []
    for text in df_in["text_clean"].fillna("").astype(str):
        present = sorted({t for t in terms if t in text})
        pair_rows.extend(combinations(present, 2))
    if not pair_rows:
        return pd.DataFrame(columns=["term_1", "term_2", "cooccurrence_count"])
    pair_counter = Counter(pair_rows)
    return (pd.DataFrame([
        {"term_1": k[0], "term_2": k[1], "cooccurrence_count": v}
        for k, v in pair_counter.items()
    ]).sort_values("cooccurrence_count", ascending=False)
        .reset_index(drop=True))


# ---------------------------------------------------------------------------
# Step 11-13 — BERTopic + need statements
# ---------------------------------------------------------------------------

SEED_TOPIC_LIST = [
    ["food tray", "tray", "ompreng", "wadah"],
    ["dingin", "hangat", "suhu", "basi", "cepat basi"],
    ["tumpah", "bocor", "tutup", "rapat", "kuah"],
    ["stainless", "ss 304", "food grade", "karat", "bahan"],
    ["distribusi", "angkut", "rafia", "tali", "rapia", "ikat", "tumpuk", "handling"],
    ["higienis", "sanitasi", "bersih", "kotor", "kontaminasi", "cuci"],
]


def run_bertopic(tray_pp: pd.DataFrame):
    from sklearn.feature_extraction.text import CountVectorizer
    from bertopic import BERTopic
    from bertopic.representation import KeyBERTInspired
    from umap import UMAP

    docs = tray_pp["text_clean"].fillna("").tolist()
    n = len(docs)
    bcfg = THRESHOLDS["bertopic"]
    if n < bcfg["min_docs_required"]:
        raise ValueError(f"Dokumen tray ({n}) < {bcfg['min_docs_required']}")

    min_topic_size = (bcfg["min_topic_size_small_corpus"]
                      if n < bcfg["small_corpus_threshold"]
                      else bcfg["min_topic_size_large_corpus"])

    # Adjust UMAP n_neighbors: default 15 fails on small corpus
    n_neighbors = max(2, min(15, n - 1))
    umap_model = UMAP(
        n_neighbors=n_neighbors,
        n_components=min(5, max(2, n - 2)),
        metric="cosine",
        random_state=bcfg["random_state"],
    )

    topic_model = BERTopic(
        language=bcfg["language"],
        seed_topic_list=SEED_TOPIC_LIST,
        min_topic_size=min_topic_size,
        calculate_probabilities=False,
        representation_model=KeyBERTInspired(),
        vectorizer_model=CountVectorizer(
            ngram_range=tuple(bcfg["ngram_range"]),
            min_df=bcfg["vectorizer_min_df"],
        ),
        umap_model=umap_model,
        verbose=False,
    )
    topics, _ = topic_model.fit_transform(docs)
    return topic_model, topics, min_topic_size


def representative_docs_per_topic(df_in: pd.DataFrame,
                                   topic_col: str = "topic",
                                   top_n: int = 5) -> pd.DataFrame:
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
                "topic": int(tid),
                "text_raw": r["text_raw"],
                "tweet_url": r["tweet_url"],
                "rep_score": int(r["rep_score"]),
            })
    return pd.DataFrame(rows)


def draft_need_statement(keywords: list[str]) -> str:
    text = " ".join(keywords).lower()
    for tpl in NEED_TEMPLATES:
        if any(k.lower() in text for k in tpl["keywords"]):
            return tpl["statement"]
    return DEFAULT_NEED


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------
    # Load raw -> normalize
    # -----------------------------------------------------------------
    print("\n[Step 5] Loading raw CSVs...")
    g_raw = pd.read_csv(OUT / "01_general_raw.csv", dtype=str, keep_default_na=False)
    t_raw = pd.read_csv(OUT / "02_tray_raw.csv", dtype=str, keep_default_na=False)
    print(f"  general_raw : {len(g_raw)} rows")
    print(f"  tray_raw    : {len(t_raw)} rows")

    general_df = normalize_raw(g_raw, "general")
    tray_df    = normalize_raw(t_raw, "tray")

    # -----------------------------------------------------------------
    # Step 5: preprocessing
    # -----------------------------------------------------------------
    print("\n[Step 5] Preprocessing (Sastrawi)...")
    general_pp = prep_dataframe(general_df)
    print(f"  general_pp  : {len(general_pp)} rows after clean+stem+dedupe")
    tray_pp    = prep_dataframe(tray_df)
    print(f"  tray_pp     : {len(tray_pp)} rows after clean+stem+dedupe")

    general_pp.drop(columns=["tokens", "tokens_stem"], errors="ignore").to_csv(
        OUT / "03_general_preprocessed.csv", index=False)
    tray_pp.drop(columns=["tokens", "tokens_stem"], errors="ignore").to_csv(
        OUT / "04_tray_preprocessed.csv", index=False)

    # -----------------------------------------------------------------
    # Step 6: issue ranking Corpus A
    # -----------------------------------------------------------------
    print("\n[Step 6] Issue ranking Corpus A...")
    issue_rank_df = issue_ranking(general_pp)
    issue_rank_df.to_csv(OUT / "05_issue_ranking_general.csv", index=False)
    print(issue_rank_df.to_string(index=False))

    # -----------------------------------------------------------------
    # Step 7: top words Corpus A
    # -----------------------------------------------------------------
    print("\n[Step 7] Top words Corpus A...")
    all_tokens: list[str] = []
    for toks in general_pp["tokens_stem"]:
        all_tokens.extend(toks)
    general_top_words = pd.DataFrame(
        Counter(all_tokens).most_common(THRESHOLDS["top_words"]["n"]),
        columns=["word", "count"]
    )
    general_top_words.to_csv(OUT / "06_general_top_words.csv", index=False)
    print(f"  -> {len(general_top_words)} words")

    # -----------------------------------------------------------------
    # Step 8: sentiment lexicon Corpus B
    # -----------------------------------------------------------------
    print("\n[Step 8] Sentiment lexicon Corpus B...")
    tray_pp["sentiment_score"] = tray_pp["text_clean"].apply(sentiment_score)
    tray_pp["sentiment_label"] = tray_pp["sentiment_score"].apply(sentiment_label)
    sent_summary = (tray_pp["sentiment_label"].value_counts()
                    .reset_index())
    sent_summary.columns = ["sentiment", "count"]
    sent_summary.to_csv(OUT / "07_tray_sentiment_summary.csv", index=False)
    print(sent_summary.to_string(index=False))

    # -----------------------------------------------------------------
    # Step 9: N-gram
    # -----------------------------------------------------------------
    print("\n[Step 9] N-gram analysis...")
    n_cfg = THRESHOLDS["ngram"]
    general_top_bigrams = get_top_ngrams(
        general_pp["text_joined"], (2, 2),
        n_cfg["bigram_top_n"], n_cfg["min_df"])
    tray_top_bigrams = get_top_ngrams(
        tray_pp["text_joined"], (2, 2),
        n_cfg["bigram_top_n"], n_cfg["min_df"])
    tray_top_trigrams = get_top_ngrams(
        tray_pp["text_joined"], (3, 3),
        n_cfg["trigram_top_n"], n_cfg["min_df"])
    general_top_bigrams.to_csv(OUT / "12_general_top_bigrams.csv", index=False)
    tray_top_bigrams.to_csv(OUT / "13_tray_top_bigrams.csv", index=False)
    tray_top_trigrams.to_csv(OUT / "14_tray_top_trigrams.csv", index=False)
    print(f"  general bigram={len(general_top_bigrams)}  "
          f"tray bigram={len(tray_top_bigrams)}  trigram={len(tray_top_trigrams)}")

    # -----------------------------------------------------------------
    # Step 10: co-occurrence
    # -----------------------------------------------------------------
    print("\n[Step 10] Co-occurrence analysis...")
    cc_cfg = THRESHOLDS["cooccurrence"]
    tray_co_df = build_cooccurrence_from_docs(
        tray_pp["text_joined"],
        min_df=cc_cfg["auto_vocab_min_df"],
        max_features=cc_cfg["auto_vocab_max_features"])
    tray_top_pairs = extract_top_pairs(tray_co_df, top_n=cc_cfg["pairs_top_n"])
    tray_top_pairs.to_csv(OUT / "15_tray_cooccurrence_pairs.csv", index=False)

    tray_design_pairs = build_keyword_cooccurrence(tray_pp, DESIGN_TERMS)
    tray_design_pairs.to_csv(OUT / "16_tray_design_cooccurrence_pairs.csv", index=False)
    print(f"  auto pairs={len(tray_top_pairs)}  design pairs={len(tray_design_pairs)}")

    # -----------------------------------------------------------------
    # Step 11-13: BERTopic + representative + need statement
    # -----------------------------------------------------------------
    bertopic_meta = {
        "language": THRESHOLDS["bertopic"]["language"],
        "min_topic_size": None,
        "n_topics_discovered": 0,
        "ran": False,
        "skip_reason": None,
    }
    topic_info = pd.DataFrame()
    topic_rep_df = pd.DataFrame()
    need_statement_df = pd.DataFrame()

    safety = THRESHOLDS["safety"]
    if len(tray_pp) < safety["min_corpus_b_for_full_run"]:
        bertopic_meta["skip_reason"] = (
            f"tray_pp ({len(tray_pp)}) < safety.min_corpus_b_for_full_run "
            f"({safety['min_corpus_b_for_full_run']})"
        )
        print(f"\n[Step 11] SKIP BERTopic: {bertopic_meta['skip_reason']}")
    else:
        print(f"\n[Step 11] BERTopic on {len(tray_pp)} docs...")
        try:
            topic_model, topics, min_topic_size = run_bertopic(tray_pp)
            tray_pp["topic"] = topics
            topic_info = topic_model.get_topic_info()
            topic_info.to_csv(OUT / "08_tray_topic_info.csv", index=False)
            bertopic_meta.update({
                "min_topic_size": int(min_topic_size),
                "n_topics_discovered": int((topic_info["Topic"] != -1).sum()),
                "ran": True,
            })
            print(f"  -> {bertopic_meta['n_topics_discovered']} topics "
                  f"(min_topic_size={min_topic_size})")

            print("\n[Step 12] Representative tweets per topic...")
            topic_rep_df = representative_docs_per_topic(
                tray_pp, top_n=THRESHOLDS["representative"]["top_n_per_topic"])
            topic_rep_df.to_csv(
                OUT / "09_tray_topic_representative_docs.csv", index=False)
            print(f"  -> {len(topic_rep_df)} rows")

            print("\n[Step 13] Draft need statements...")
            topic_keywords_map = {
                int(tid): [w for w, _ in (topic_model.get_topic(tid) or [])[:10]]
                for tid in topic_info[topic_info["Topic"] != -1]["Topic"].tolist()
            }
            need_rows = []
            for tid, kws in topic_keywords_map.items():
                need_rows.append({
                    "topic": tid,
                    "keywords": ", ".join(kws),
                    "tweet_count": int((tray_pp["topic"] == tid).sum()),
                    "draft_need_statement": draft_need_statement(kws),
                    "manual_final_need_statement": "",
                    "manual_notes": "",
                })
            need_statement_df = (pd.DataFrame(need_rows)
                                 .sort_values("tweet_count", ascending=False)
                                 .reset_index(drop=True))
            need_statement_df.to_csv(
                OUT / "10_tray_need_statements_draft.csv", index=False)
            print(f"  -> {len(need_statement_df)} need statements")
        except Exception as e:
            bertopic_meta["skip_reason"] = f"BERTopic error: {type(e).__name__}: {e}"
            print(f"  ERROR: {bertopic_meta['skip_reason']}")

    # -----------------------------------------------------------------
    # Step 14: manual review template
    # -----------------------------------------------------------------
    print("\n[Step 14] Manual review template...")
    cols = ["tweet_id", "created_at", "author_username", "text_raw",
            "text_clean", "sentiment_label", "tweet_url"]
    if "topic" in tray_pp.columns:
        cols.insert(-1, "topic")
    manual_review_df = tray_pp[[c for c in cols if c in tray_pp.columns]].copy()
    for c in ["manual_keep", "manual_topic_label", "manual_issue_category",
              "manual_design_implication", "manual_notes"]:
        manual_review_df[c] = ""
    manual_review_df.to_csv(OUT / "11_tray_manual_review.csv", index=False)
    print(f"  -> {len(manual_review_df)} rows")

    # -----------------------------------------------------------------
    # Stats files (loaded earlier from step1_consolidate)
    # -----------------------------------------------------------------
    general_stats_df = pd.read_csv(OUT / "00_general_query_stats.csv")
    tray_stats_df    = pd.read_csv(OUT / "00_tray_query_stats.csv")

    # -----------------------------------------------------------------
    # Step 15: multi-sheet Excel
    # -----------------------------------------------------------------
    print("\n[Step 15] Writing multi-sheet Excel...")
    xlsx_path = OUT / "mbg_x_foodtray_analysis.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as writer:
        general_stats_df.to_excel(writer, "query_stats_general", index=False)
        tray_stats_df.to_excel(writer, "query_stats_tray", index=False)
        general_df.to_excel(writer, "general_raw", index=False)
        tray_df.to_excel(writer, "tray_raw", index=False)
        general_pp.drop(columns=["tokens", "tokens_stem"], errors="ignore").to_excel(
            writer, "general_preprocessed", index=False)
        tray_pp.drop(columns=["tokens", "tokens_stem"], errors="ignore").to_excel(
            writer, "tray_preprocessed", index=False)
        issue_rank_df.to_excel(writer, "issue_ranking_general", index=False)
        general_top_words.to_excel(writer, "general_top_words", index=False)
        sent_summary.to_excel(writer, "tray_sentiment_summary", index=False)
        if not topic_info.empty:
            topic_info.to_excel(writer, "tray_topic_info", index=False)
        if not topic_rep_df.empty:
            topic_rep_df.to_excel(writer, "tray_topic_rep_docs", index=False)
        if not need_statement_df.empty:
            need_statement_df.to_excel(writer, "draft_need_statement", index=False)
        manual_review_df.to_excel(writer, "manual_review_tray", index=False)
        general_top_bigrams.to_excel(writer, "general_top_bigrams", index=False)
        tray_top_bigrams.to_excel(writer, "tray_top_bigrams", index=False)
        tray_top_trigrams.to_excel(writer, "tray_top_trigrams", index=False)
        tray_top_pairs.to_excel(writer, "tray_cooccurrence_pairs", index=False)
        tray_design_pairs.to_excel(writer, "tray_design_cooccurrence", index=False)
    print(f"  -> {xlsx_path}")

    # -----------------------------------------------------------------
    # Step 16: report.md
    # -----------------------------------------------------------------
    print("\n[Step 16] Writing report.md...")
    write_report(
        out_path=OUT / "report.md",
        general_pp=general_pp, tray_pp=tray_pp,
        issue_rank_df=issue_rank_df,
        sent_summary=sent_summary,
        topic_info=topic_info,
        topic_rep_df=topic_rep_df,
        need_statement_df=need_statement_df,
        tray_design_pairs=tray_design_pairs,
        general_top_bigrams=general_top_bigrams,
        tray_top_bigrams=tray_top_bigrams,
        tray_top_trigrams=tray_top_trigrams,
        bertopic_meta=bertopic_meta,
    )
    print(f"  -> {OUT / 'report.md'}")

    # -----------------------------------------------------------------
    # Step 17: _run_meta.json
    # -----------------------------------------------------------------
    print("\n[Step 17] Writing _run_meta.json...")
    meta = {
        "run_id": RUN_ID,
        "timestamp_utc": TIMESTAMP_UTC,
        "config_hash": CONFIG_HASH,
        "window": THRESHOLDS["date_window"],
        "query_packs": {
            "general": list(QUERY_PACKS.get("general", {}).keys()),
            "tray":    list(QUERY_PACKS.get("tray", {}).keys()),
        },
        "volumes": {
            "general_raw": int(len(general_df)),
            "general_preprocessed": int(len(general_pp)),
            "tray_raw": int(len(tray_df)),
            "tray_preprocessed": int(len(tray_pp)),
        },
        "issue_ranking": issue_rank_df.to_dict(orient="records"),
        "sentiment_distribution": sent_summary.to_dict(orient="records"),
        "bertopic": bertopic_meta,
        "skipped_packs": [],
        "xpoz_calls": [
            {"tool": "countTweets", "count": 9},
            {"tool": "getTwitterPostsByKeywords", "count": 9,
             "response_type": "csv+fast", "async_polling": True},
        ],
    }
    (OUT / "_run_meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {OUT / '_run_meta.json'}")

    print("\n[DONE] Pipeline selesai.")


# ---------------------------------------------------------------------------
# Report writer (Step 16)
# ---------------------------------------------------------------------------

def _df_to_md(df: pd.DataFrame, max_rows: int = 20) -> str:
    if df is None or df.empty:
        return "_(tidak ada data)_\n"
    return df.head(max_rows).to_markdown(index=False) + "\n"


def write_report(*, out_path: Path,
                 general_pp: pd.DataFrame, tray_pp: pd.DataFrame,
                 issue_rank_df: pd.DataFrame,
                 sent_summary: pd.DataFrame,
                 topic_info: pd.DataFrame,
                 topic_rep_df: pd.DataFrame,
                 need_statement_df: pd.DataFrame,
                 tray_design_pairs: pd.DataFrame,
                 general_top_bigrams: pd.DataFrame,
                 tray_top_bigrams: pd.DataFrame,
                 tray_top_trigrams: pd.DataFrame,
                 bertopic_meta: dict) -> None:
    parts: list[str] = []
    parts.append("# Laporan Text Mining X — MBG & Food Tray\n")
    parts.append(f"**Run ID:** `{RUN_ID}`  ")
    parts.append(f"**Timestamp UTC:** {TIMESTAMP_UTC}  ")
    parts.append(f"**Config hash:** `{CONFIG_HASH}`  ")
    parts.append("**Periode:** 1 Agustus – 31 Oktober 2025  ")
    parts.append(f"**Total Corpus A (preprocessed):** {len(general_pp)}  ")
    parts.append(f"**Total Corpus B (preprocessed):** {len(tray_pp)}\n")

    parts.append("## 1. Ringkasan Eksekutif\n")
    if not issue_rank_df.empty:
        ftr = issue_rank_df[issue_rank_df["issue"] == "food_tray_ompreng"]
        rank_ft = int(ftr["rank"].iloc[0]) if not ftr.empty else None
        share_ft = float(ftr["share_of_issue_coded_tweets_pct"].iloc[0]) if not ftr.empty else 0.0
        if rank_ft:
            parts.append(
                f"- Isu **food tray / ompreng** menempati **rank #{rank_ft}** "
                f"dari {len(issue_rank_df)} kategori isu MBG di Corpus A "
                f"(share {share_ft:.2f}% dari tweet ber-issue).\n"
            )
    if not sent_summary.empty:
        sm = sent_summary.set_index("sentiment")["count"].to_dict()
        total = sum(sm.values()) or 1
        parts.append(
            f"- Distribusi sentimen Corpus B (food tray): "
            f"negatif {sm.get('negatif', 0)} ({sm.get('negatif', 0)/total*100:.1f}%), "
            f"netral {sm.get('netral', 0)} ({sm.get('netral', 0)/total*100:.1f}%), "
            f"positif {sm.get('positif', 0)} ({sm.get('positif', 0)/total*100:.1f}%).\n"
        )
    if bertopic_meta.get("ran"):
        parts.append(
            f"- BERTopic menemukan **{bertopic_meta['n_topics_discovered']} topic** "
            f"(min_topic_size={bertopic_meta['min_topic_size']}); draft need statement "
            f"diturunkan rule-based dari topic keyword.\n"
        )
    elif bertopic_meta.get("skip_reason"):
        parts.append(f"- BERTopic **di-skip**: {bertopic_meta['skip_reason']}.\n")

    parts.append("\n## 2. Metodologi Singkat\n")
    parts.append(
        "- Sumber data: Xpoz MCP (Twitter/X), 2 corpus paralel.\n"
        "- Query packs: 3 (general) + 6 (tray); rentang 2025-08-01 → 2025-10-31.\n"
        "- Preprocessing: regex + Sastrawi stemming + tokenize + dedupe.\n"
        "- Issue ranking Corpus A: keyword dictionary 5 kategori.\n"
        "- Sentimen Corpus B: lexicon (positif/netral/negatif), tidak menangani sarkasme.\n"
        "- Topic discovery Corpus B: BERTopic multilingual + KeyBERT representation.\n"
        "- N-gram & co-occurrence: scikit-learn CountVectorizer + Counter.\n"
        "- Need statement: rule-based mapping topic-keyword → template.\n"
    )

    parts.append("\n## 3. Posisi Isu Food Tray di Corpus A (rank 5 isu MBG)\n")
    parts.append(_df_to_md(issue_rank_df))
    if not issue_rank_df.empty:
        top_issue = issue_rank_df.iloc[0]
        parts.append(
            f"\nIsu paling sering muncul: **{top_issue['issue']}** "
            f"({int(top_issue['tweet_count'])} tweets, "
            f"{float(top_issue['share_of_issue_coded_tweets_pct']):.2f}% "
            f"dari tweet ber-issue).\n"
        )

    parts.append("\n## 4. Sentimen Corpus B (Food Tray)\n")
    parts.append(_df_to_md(sent_summary))

    parts.append("\n## 5. Topik BERTopic Corpus B\n")
    if bertopic_meta.get("ran"):
        parts.append(_df_to_md(topic_info, max_rows=30))
        parts.append("\n### 5.1 Kutipan representatif (top 2 per topic)\n")
        if not topic_rep_df.empty:
            for tid in sorted(topic_rep_df["topic"].unique()):
                sub = topic_rep_df[topic_rep_df["topic"] == tid].head(2)
                parts.append(f"\n**Topic {tid}:**\n")
                for _, r in sub.iterrows():
                    quote = (r["text_raw"] or "").replace("\n", " ")[:280]
                    parts.append(f"- _\"{quote}\"_ — [link]({r['tweet_url']})\n")
    else:
        parts.append(f"_BERTopic di-skip: {bertopic_meta.get('skip_reason')}_\n")

    parts.append("\n## 6. Co-occurrence Insight (Design Terms)\n")
    parts.append(_df_to_md(tray_design_pairs.head(10)))

    parts.append("\n### 6.1 Top bigram Corpus A\n")
    parts.append(_df_to_md(general_top_bigrams.head(15)))
    parts.append("\n### 6.2 Top bigram & trigram Corpus B\n")
    parts.append("**Bigram:**\n")
    parts.append(_df_to_md(tray_top_bigrams.head(15)))
    parts.append("\n**Trigram:**\n")
    parts.append(_df_to_md(tray_top_trigrams.head(15)))

    parts.append("\n## 7. Draft Need Statement (urut by tweet_count)\n")
    if not need_statement_df.empty:
        for _, r in need_statement_df.iterrows():
            parts.append(
                f"\n- **Topic {int(r['topic'])}** ({int(r['tweet_count'])} tweets) — "
                f"_keywords: {r['keywords']}_  \n"
                f"  → {r['draft_need_statement']}\n"
            )
    else:
        parts.append("_(BERTopic tidak dijalankan, draft need statement tidak tersedia)_\n")

    parts.append("\n## 8. Limitasi\n")
    parts.append(
        "- Data terbatas pada X (bias platform; tidak mewakili guru/petugas SPPG offline).\n"
        "- Lexicon sentiment: tidak menangkap sarkasme/negasi kompleks.\n"
        "- BERTopic: hasil sensitif terhadap `min_topic_size` + jumlah dokumen.\n"
        "- Window 3 bulan: kemungkinan over-representasi isu viral periode tersebut.\n"
        "- Bahasa Inggris/asing telah di-filter; mungkin kehilangan diaspora yang relevan.\n"
    )

    parts.append("\n## 9. Next Step\n")
    parts.append(
        "1. Manual review di `outputs/11_tray_manual_review.csv` (target ≥30 baris).\n"
        "2. Triangulasi dengan benchmarking produk tray komersial.\n"
        "3. Turunkan draft need statement → spesifikasi teknis "
        "(material, dimensi, mekanisme tutup, tahan suhu).\n"
        "4. Buat 2 alternatif desain → expert judgement SPPG.\n"
    )

    out_path.write_text("\n".join(parts), encoding="utf-8")


if __name__ == "__main__":
    main()
