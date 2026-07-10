"""Phase 6 review surfaces for the tag pipeline.

Reads data/tags.json (+ per-metric JSONs for tweet text/urls) and writes
three CSVs next to this script's eval outputs:

  scripts/eval/review_low_confidence.csv  — all confidence in {low, med}
  scripts/eval/review_proposed_tags.csv   — proposed_new_tag suggestions, grouped
  scripts/eval/review_tag_samples.csv     — up to 10 sample tweets per tag

Deterministic sampling (seeded) so re-runs produce the same samples.
"""
import csv
import json
import random
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"
OUT = ROOT / "scripts" / "eval"

tags_map = json.loads((ROOT / "data" / "tags.json").read_text())

by_id = {}
for name in ["top_rt.json", "top_likes.json", "top_qt.json"]:
    for r in json.loads((DATA / name).read_text()):
        by_id.setdefault(r["tweet_id"], r)


def url(tid):
    r = by_id.get(tid) or {}
    u = r.get("username") or "i"
    return f"https://x.com/{u}/status/{tid}"


def text(tid):
    return (by_id.get(tid) or {}).get("full_text", "")


# 1. low/med confidence
rows = [
    {
        "tweet_id": tid,
        "tweet_url": url(tid),
        "confidence": rec["confidence"],
        "source": rec["source"],
        "media_dependent": rec["media_dependent"],
        "tags": ";".join(rec["tags"]),
        "full_text": text(tid)[:280],
    }
    for tid, rec in tags_map.items()
    if rec.get("confidence") in ("low", "med")
]
rows.sort(key=lambda r: (r["confidence"], r["tweet_id"]))
with open(OUT / "review_low_confidence.csv", "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["tweet_id"])
    w.writeheader()
    w.writerows(rows)
print(f"low/med confidence: {len(rows)}")

# 2. proposed new tags
prop = defaultdict(list)
for tid, rec in tags_map.items():
    if rec.get("proposed_new_tag"):
        prop[rec["proposed_new_tag"]].append(tid)
with open(OUT / "review_proposed_tags.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["proposed_new_tag", "count", "example_urls"])
    for tag, tids in sorted(prop.items(), key=lambda kv: -len(kv[1])):
        w.writerow([tag, len(tids), " ".join(url(t) for t in tids[:5])])
print(f"proposed tags: {len(prop)} distinct, {sum(len(v) for v in prop.values())} total")

# 3. per-tag samples
per_tag = defaultdict(list)
for tid, rec in tags_map.items():
    for t in rec["tags"]:
        per_tag[t].append(tid)
rng = random.Random(42)
with open(OUT / "review_tag_samples.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["tag", "n_total", "tweet_id", "tweet_url", "confidence", "source", "full_text"])
    for tag in sorted(per_tag):
        tids = per_tag[tag]
        for tid in rng.sample(tids, min(10, len(tids))):
            rec = tags_map[tid]
            w.writerow([tag, len(tids), tid, url(tid), rec["confidence"], rec["source"], text(tid)[:280]])
print(f"tag sample rows written for {len(per_tag)} tags")
print(f"tag distribution: {Counter({t: len(v) for t, v in per_tag.items()}).most_common(12)}")
