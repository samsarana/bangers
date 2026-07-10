"""Merge data/tags.json into the existing per-metric JSONs in place.

Idempotent: sets `tags` on every record on every run (primary tweets get their
tags from tags.json, context tweets and untagged primaries get []). `unknown`
is filtered out — it renders as untagged.

This is the fast path (no parquet load). `build.py` performs the same merge
during a full rebuild, so running either leaves the files in the same state.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "site" / "data"

raw = json.loads((ROOT / "data" / "tags.json").read_text())
tags_map = {
    tid: [t for t in rec.get("tags", []) if t != "unknown"]
    for tid, rec in raw.items()
}
print(f"tags.json: {len(tags_map):,} tweets")

for name in ["top_rt.json", "top_likes.json", "top_qt.json"]:
    p = DATA / name
    records = json.loads(p.read_text())
    tagged = 0
    for rec in records:
        if not rec.get("is_context") and rec["tweet_id"] in tags_map:
            rec["tags"] = tags_map[rec["tweet_id"]]
            tagged += 1
        else:
            rec["tags"] = []
    p.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
    primary = sum(1 for r in records if not r.get("is_context"))
    print(f"{name}: {tagged:,}/{primary:,} primaries tagged ({p.stat().st_size/1e6:.1f} MB)")
