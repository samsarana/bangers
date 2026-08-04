"""Apply top-N review verdicts: strip removed tags, record overrides, report.

Usage: python3 scripts/eval/apply_review.py <review_workdir>

- Reads <workdir>/manifest.json + <workdir>/results/batch_*.json.
- Every "remove" verdict drops that tag from the tweet's record in
  data/tags.json (a tweet stripped of its last tag becomes ["unclassified"]).
- Final tags of every modified tweet are written into
  scripts/eval/tag_overrides.json so re-running assemble_tags.py can't
  resurrect a removed tag.
- Run scripts/merge_tags.py afterwards to patch the per-metric JSONs.
"""
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
work = Path(sys.argv[1])

manifest = json.loads((work / "manifest.json").read_text())
tags_path = ROOT / "data/tags.json"
records = json.loads(tags_path.read_text())

removals = []  # (tweet_id, tag, reason)
missing_batches = []
for bi, info in sorted(manifest.items(), key=lambda kv: int(kv[0])):
    f = work / "results" / f"batch_{int(bi):03d}.json"
    if not f.exists():
        missing_batches.append(bi)
        continue
    verdicts = json.loads(f.read_text())
    tids = info["tweet_ids"]
    for v in verdicts:
        if v.get("verdict") == "remove":
            i = v["index"]
            if 0 <= i < len(tids):
                removals.append((tids[i], info["tag"], v.get("reason", "")))

overrides_path = ROOT / "scripts/eval/tag_overrides.json"
overrides = json.loads(overrides_path.read_text()) if overrides_path.exists() else {}

per_tag = Counter()
protected = 0
for tid, tag, reason in removals:
    r = records.get(tid)
    if not r or tag not in r["tags"]:
        continue
    if r["source"] == "human" and tid not in overrides:
        # seed labels are ground truth; a reviewer disagreeing with the user loses
        protected += 1
        continue
    r["tags"] = [t for t in r["tags"] if t != tag]
    if not r["tags"]:
        r["tags"] = ["unclassified"]
    per_tag[tag] += 1
    overrides[tid] = {"tags": r["tags"], "note": f"top-N review: -{tag}"}

tags_path.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")))
overrides_path.write_text(json.dumps(overrides, ensure_ascii=False, indent=1))

print(f"remove verdicts: {len(removals)}; applied: {sum(per_tag.values())}; "
      f"skipped (human seed): {protected}")
print(f"missing batches: {missing_batches or 'none'}")
for tag, n in per_tag.most_common():
    print(f"  -{n}  {tag}")
print(f"overrides file now holds {len(overrides)} tweets")

# reasons digest for the user
digest = work / "removal_reasons.txt"
digest.write_text("\n".join(f"{tid}  -{tag}  {reason}" for tid, tag, reason in removals))
print(f"reasons written to {digest}")
