import pandas as pd
import re
import uuid
import json
from datetime import datetime, timezone

KEYWORDS = {
    "mbg_raw.csv":                "mbg",
    "makan_bergizi_gratis_raw.csv": "makan bergizi gratis",
    "program_mbg_raw.csv":          "program mbg",
}

DATE_START = "2025-08-01"
DATE_END   = "2026-03-26"

def clean_text(t):
    t = str(t).lower()
    t = re.sub(r'http\S+|www\S+', '', t)
    t = re.sub(r'@\w+', '', t)
    t = re.sub(r'#', '', t)
    t = re.sub(r'[\n\r\t]', ' ', t)
    t = re.sub(r'[^a-zA-Z0-9\s]', '', t)
    t = re.sub(r' +', ' ', t).strip()
    return t

# --- Step 4: Load, tag, concat ---
frames = []
raw_counts = {}
for fname, label in KEYWORDS.items():
    df = pd.read_csv(fname, dtype=str, encoding="utf-8", encoding_errors="replace")
    df.columns = df.columns.str.strip('"')
    df["query_used"] = label
    raw_counts[label] = len(df)
    frames.append(df)

raw_df = pd.concat(frames, ignore_index=True)
total_raw = len(raw_df)
print(f"Total raw (sebelum dedupe): {total_raw}")

# Dedupe by id
raw_df = raw_df.drop_duplicates(subset=["id"]).reset_index(drop=True)
print(f"Setelah dedupe: {len(raw_df)}")

# Validasi tanggal
raw_df["created_at_date"] = raw_df["created_at_date"].astype(str).str[:10]
raw_df = raw_df[
    (raw_df["created_at_date"] >= DATE_START) &
    (raw_df["created_at_date"] <= DATE_END)
].reset_index(drop=True)
print(f"Setelah filter tanggal: {len(raw_df)}")
total_cleaned = len(raw_df)

# --- Step 5: Clean text ---
raw_df["text_clean"] = raw_df["text"].apply(clean_text)

# --- Step 6: Susun final CSV ---
raw_df["tweet_url"] = raw_df.apply(
    lambda r: f"https://x.com/{r['author_username']}/status/{r['id']}", axis=1
)

out = pd.DataFrame({
    "tweet_id":                 raw_df["id"].astype(str),
    "created_at":               raw_df["created_at"],
    "author_username":          raw_df["author_username"],
    "text_raw":                 raw_df["text"],
    "text_clean":               raw_df["text_clean"],
    "sentiment_label":          "",
    "topic":                    0,
    "tweet_url":                raw_df["tweet_url"],
    "manual_keep":              "",
    "manual_topic_label":       "",
    "manual_issue_category":    "",
    "manual_design_implication":"",
    "manual_notes":             "",
})

out.to_csv("scrape_mbg_manual_review.csv", index=False)
print(f"Saved: scrape_mbg_manual_review.csv ({len(out)} rows)")

# --- Step 7: Run meta ---
meta = {
    "run_id":        str(uuid.uuid4()),
    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    "window":        {"start": DATE_START, "end": DATE_END},
    "keywords":      list(KEYWORDS.values()),
    "total_raw":     total_raw,
    "total_cleaned": total_cleaned,
    "raw_per_keyword": raw_counts,
    "xpoz_calls": [
        {"tool": "getTwitterPostsByKeywords", "keyword": label,
         "estimated_count": raw_counts[label], "response_type": "csv"}
        for label in KEYWORDS.values()
    ],
}
with open("_run_meta_just_get_data.json", "w") as f:
    json.dump(meta, f, indent=2)
print("Saved: _run_meta_just_get_data.json")
