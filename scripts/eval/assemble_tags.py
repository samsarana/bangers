"""Assemble data/tags.json from batch result files.

Usage: python3 scripts/eval/assemble_tags.py <scratch_full_dir>

Inputs:
  <dir>/results/batch_*.json   — text-pass predictions (Phase 4)
  <dir>/idmap.json             — (batch:index) -> tweet_id
  <dir>/meta.json              — tweet_id -> {username, has_media, media_url}
  <dir>/vision_results/batch_*.json + vision_idmap.json  — optional (Phase 5)
  <dir>/no_media.json          — optional; media_dependent ids with no fetchable image
  scripts/eval/seed_labels_cleaned.csv — human labels, source: "human"

Output: data/tags.json — {tweet_id: {username, tags, confidence,
        media_dependent, source, proposed_new_tag?}}

Also prints: missing batches / missing indexes / invalid slugs, so failed
agents can be re-run before shipping.
"""
import csv
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
work = Path(sys.argv[1])

slugs = set(re.findall(r"^### (.+)$", (ROOT / "data/taxonomy.md").read_text(), re.M))
idmap = json.loads((work / "idmap.json").read_text())
meta = json.loads((work / "meta.json").read_text())

records = {}
problems = []
seen_keys = set()

for f in sorted((work / "results").glob("batch_*.json")):
    bi = int(f.stem.split("_")[1])
    try:
        arr = json.loads(f.read_text())
    except json.JSONDecodeError as e:
        problems.append(f"{f.name}: parse error {e}")
        continue
    for p in arr:
        key = f"{bi}:{p['index']}"
        tid = idmap.get(key)
        if tid is None:
            problems.append(f"{f.name}: no idmap for index {p['index']}")
            continue
        seen_keys.add(key)
        tags = [t for t in p.get("tags", []) if t in slugs]
        bad = [t for t in p.get("tags", []) if t not in slugs]
        if bad:
            problems.append(f"{tid}: dropped invalid slugs {bad}")
        if "LLMs" in tags and "AI" not in tags:
            tags.append("AI")
        rec = {
            "username": meta.get(tid, {}).get("username"),
            "tags": tags or ["unknown"],
            "confidence": p.get("confidence", "low"),
            "media_dependent": bool(p.get("media_dependent")),
            "source": "text",
        }
        if p.get("proposed_new_tag"):
            rec["proposed_new_tag"] = p["proposed_new_tag"]
        records[tid] = rec

missing = sorted(set(idmap) - seen_keys)
missing_batches = sorted({k.split(":")[0] for k in missing})

# --- vision overlay (Phase 5) ---
vision_n = 0
vmap_path = work / "vision_idmap.json"
if vmap_path.exists():
    vmap = json.loads(vmap_path.read_text())
    vseen = set()
    for f in sorted((work / "vision_results").glob("batch_*.json")):
        bi = int(f.stem.split("_")[1])
        try:
            arr = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"vision {f.name}: parse error {e}")
            continue
        for p in arr:
            tid = vmap.get(f"{bi}:{p['index']}")
            if tid is None or tid not in records:
                continue
            vseen.add(f"{bi}:{p['index']}")
            tags = [t for t in p.get("tags", []) if t in slugs]
            if "LLMs" in tags and "AI" not in tags:
                tags.append("AI")
            records[tid].update(
                tags=tags or ["unknown"],
                confidence=p.get("confidence", "low"),
                media_dependent=bool(p.get("media_dependent")),
                source="vision",
            )
            if p.get("proposed_new_tag"):
                records[tid]["proposed_new_tag"] = p["proposed_new_tag"]
            vision_n += 1
    vmissing = sorted(set(vmap) - vseen)
    if vmissing:
        problems.append(f"vision: {len(vmissing)} items missing: {vmissing[:10]}")

# no-image fallback: media_dependent + unfetchable media + unknown -> unclassified
nm_path = work / "no_media.json"
if nm_path.exists():
    for tid in json.loads(nm_path.read_text()):
        r = records.get(tid)
        if r and r["tags"] == ["unknown"]:
            r.update(tags=["unclassified"], confidence="med", source="text")

# --- human seed labels ---
for row in csv.DictReader(open(ROOT / "scripts/eval/seed_labels_cleaned.csv")):
    records[row["tweet_id"]] = {
        "username": row["username"],
        "tags": [t for t in row["tags"].split(";") if t],
        "confidence": "high",
        "media_dependent": False,
        "source": "human",
    }

# --- manual overrides (review removals + one-off corrections) — applied LAST ---
ov_path = ROOT / "scripts/eval/tag_overrides.json"
if ov_path.exists():
    ov_n = 0
    for tid, ov in json.loads(ov_path.read_text()).items():
        r = records.get(tid)
        if r is None:
            problems.append(f"override for unknown tweet_id {tid}")
            continue
        bad = [t for t in ov["tags"] if t not in slugs]
        if bad:
            problems.append(f"override {tid}: invalid slugs {bad} — skipped")
            continue
        r.update(tags=ov["tags"], confidence="high", source="human")
        ov_n += 1
    print(f"overrides applied: {ov_n}")

out = ROOT / "data/tags.json"
out.write_text(json.dumps(records, ensure_ascii=False, separators=(",", ":")))

n = len(records)
dist = Counter(t for r in records.values() for t in r["tags"])
print(f"records: {n:,}  (vision-updated: {vision_n})")
print(f"missing text-pass items: {len(missing)}  (batches: {missing_batches[:20]})")
print(f"confidence: {Counter(r['confidence'] for r in records.values())}")
print(f"source: {Counter(r['source'] for r in records.values())}")
print(f"media_dependent still true: {sum(1 for r in records.values() if r['media_dependent'])}")
print(f"top tags: {dist.most_common(15)}")
print(f"unknown: {dist['unknown']}, unclassified: {dist['unclassified']}")
if problems:
    print(f"\nproblems ({len(problems)}):")
    for p in problems[:25]:
        print(f"  {p}")
print(f"\nwrote {out} ({out.stat().st_size/1024:.0f} KB)")
