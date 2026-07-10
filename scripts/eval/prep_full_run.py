"""Phase 4 prep: build classifier batch prompts for every unlabelled primary tweet.

- Dedupes primaries across the three per-metric JSONs.
- Excludes the 146 human-labelled seed tweets (they enter tags.json with
  source: "human" directly).
- Reuses scripts/eval/classifier_prompt_prefix.txt verbatim (the prompt
  validated in Phase 3b).

Usage: python3 scripts/eval/prep_full_run.py <scratch_dir>
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path("/Users/sam/Developer/Book of Bangers (Opus)")
BATCH_SIZE = 20

scratch = Path(sys.argv[1])
PROMPT_DIR = scratch / "full" / "prompts"
RESULT_DIR = scratch / "full" / "results"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)
RESULT_DIR.mkdir(parents=True, exist_ok=True)

PREFIX = (ROOT / "scripts/eval/classifier_prompt_prefix.txt").read_text()

# ---------------------------------------------------------------------------
by_id = {}
primary_ids = set()
for f in ["top_rt", "top_likes", "top_qt"]:
    for r in json.load(open(ROOT / "site/data" / f"{f}.json")):
        by_id.setdefault(r["tweet_id"], r)
        if not r.get("is_context"):
            primary_ids.add(r["tweet_id"])

seed_ids = {
    r["tweet_id"]
    for r in csv.DictReader(open(ROOT / "scripts/eval/seed_labels_cleaned.csv"))
}
todo = sorted(primary_ids - seed_ids)
print(f"Primaries: {len(primary_ids):,}; seed excluded: {len(seed_ids)}; to label: {len(todo):,}")


def fmt(r):
    return f"@{r.get('username') or ''}: {r.get('full_text') or ''}".strip()


def reply_chain(r):
    chain, seen = [], set()
    pid = r.get("reply_to_tweet_id")
    while pid and pid not in seen:
        seen.add(pid)
        pr = by_id.get(pid)
        if not pr:
            break
        chain.append(fmt(pr))
        pid = pr.get("reply_to_tweet_id")
    chain.reverse()
    return "\n---\n".join(chain)


def quoted(r):
    q = r.get("quoted_tweet_id")
    qr = by_id.get(q) if q else None
    return fmt(qr) if qr else ""


def has_media(r):
    if r.get("media"):
        return True
    t = r.get("full_text") or ""
    return "pic.twitter.com/" in t or "pic.x.com/" in t


def media_url(r):
    for m in r.get("media") or []:
        if m.get("type") == "photo" and m.get("url"):
            return m["url"]
        if m.get("poster"):
            return m["poster"]
    return None


def render_item(i, r):
    parts = [f"ITEM {i}", f"HAS_MEDIA: {'yes' if has_media(r) else 'no'}"]
    parts.append(f"TWEET: {r.get('full_text') or ''}")
    rc = reply_chain(r)
    if rc:
        parts.append(f"REPLY CONTEXT (ancestors, oldest first):\n{rc}")
    q = quoted(r)
    if q:
        parts.append(f"QUOTED TWEET: {q}")
    return "\n".join(parts)


meta = {}
idmap = {}
batches = [todo[i : i + BATCH_SIZE] for i in range(0, len(todo), BATCH_SIZE)]
for bi, ids in enumerate(batches):
    result_path = RESULT_DIR / f"batch_{bi:04d}.json"
    items = "\n\n".join(render_item(i, by_id[tid]) for i, tid in enumerate(ids))
    prompt = f"""{PREFIX}

# Output instructions

Classify every ITEM. For each, produce: index (the ITEM number), tags (array of
slugs), confidence ("high"|"med"|"low"), media_dependent (boolean), and
optionally proposed_new_tag. Indexes MUST match the ITEM numbers exactly and
every ITEM must appear exactly once.

First, use the Write tool to save your predictions to this exact path:
{result_path}
as a JSON array: [{{"index": 0, "tags": [...], "confidence": "...", "media_dependent": false}}, ...]

Then return only {{"batch_done": true, "count": <number of items>}} via the StructuredOutput tool.

# Batch

{items}
"""
    (PROMPT_DIR / f"batch_{bi:04d}.txt").write_text(prompt)
    for i, tid in enumerate(ids):
        idmap[f"{bi}:{i}"] = tid

for tid in todo:
    r = by_id[tid]
    meta[tid] = {
        "username": r.get("username"),
        "has_media": has_media(r),
        "media_url": media_url(r),
    }

(scratch / "full" / "idmap.json").write_text(json.dumps(idmap))
(scratch / "full" / "meta.json").write_text(json.dumps(meta))
print(f"Batches: {len(batches)} x <= {BATCH_SIZE}")
print(f"With media: {sum(1 for m in meta.values() if m['has_media']):,}")
print(f"  of which have a usable media_url: {sum(1 for m in meta.values() if m['media_url']):,}")
