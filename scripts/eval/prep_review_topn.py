"""Top-N-per-tag precision review prep (post-ship QA).

Usage: python3 scripts/eval/prep_review_topn.py <workdir> [--top-n 25]

For every visible tag (all taxonomy slugs except unclassified/unknown), take
the union of the top-N tweets carrying that tag under each of the three metric
orderings — i.e. exactly the slice a visitor sees when they click that chip.
Emit one review batch per <=25 (tweet, tag) pairs, grouped by tag, each batch
a self-contained prompt: the tag's taxonomy definition + the tweets (with
quoted/reply context and local image paths where the tweet has media).

Reviewers judge ONE tag per batch, precision only: keep | remove.
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path("/Users/sam/Developer/Book of Bangers (Opus)")
IMG_DIR_SHARED = Path(
    "/private/tmp/claude-502/-Users-sam-Developer-Book-of-Bangers--Opus-/"
    "f7eb5622-075c-458f-bff8-f26da31d85bf/scratchpad/full/images"
)
BATCH_SIZE = 25
HIDDEN = {"unclassified", "unknown"}

work = Path(sys.argv[1])
TOP_N = int(sys.argv[sys.argv.index("--top-n") + 1]) if "--top-n" in sys.argv else 25
prompt_dir = work / "prompts"
result_dir = work / "results"
for d in (prompt_dir, result_dir, IMG_DIR_SHARED):
    d.mkdir(parents=True, exist_ok=True)

tax = (ROOT / "data/taxonomy.md").read_text()
sections = {}
for m in re.finditer(r"^### (.+?)$\n(.*?)(?=^### |^## |\Z)", tax, re.M | re.S):
    sections[m.group(1).strip()] = m.group(2).strip()
slugs = [s for s in sections if s not in HIDDEN]

by_id = {}
ranked = {}  # metric -> [primary records in rank order]
for f in ["top_rt", "top_likes", "top_qt"]:
    recs = json.load(open(ROOT / "site/data" / f"{f}.json"))
    for r in recs:
        by_id.setdefault(r["tweet_id"], r)
    ranked[f] = [r for r in recs if not r.get("is_context")]

# --- pick review pairs ---
per_tag = {}  # slug -> [tweet_id in first-seen rank order]
for slug in slugs:
    seen = []
    for f in ["top_rt", "top_likes", "top_qt"]:
        hits = 0
        for r in ranked[f]:
            if slug in (r.get("tags") or []):
                if r["tweet_id"] not in seen:
                    seen.append(r["tweet_id"])
                hits += 1
                if hits >= TOP_N:
                    break
    per_tag[slug] = seen

n_pairs = sum(len(v) for v in per_tag.values())
print(f"tags: {len(slugs)}; review pairs: {n_pairs}; "
      f"unique tweets: {len(set(t for v in per_tag.values() for t in v))}")


def media_urls(r, cap=2):
    out = []
    for m in r.get("media") or []:
        if m.get("type") == "photo" and m.get("url"):
            out.append(m["url"])
        elif m.get("poster"):
            out.append(m["poster"])
        if len(out) >= cap:
            break
    return out


def ensure_images(tid):
    """Return local image paths for tweet, downloading if not already cached."""
    existing = sorted(IMG_DIR_SHARED.glob(f"{tid}_*"))
    if existing:
        return [str(p) for p in existing]
    r = by_id.get(tid)
    paths = []
    for j, u in enumerate(media_urls(r) if r else []):
        ext = ".jpg" if ".png" not in u.lower() else ".png"
        dest = IMG_DIR_SHARED / f"{tid}_{j}{ext}"
        try:
            req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as resp:
                dest.write_bytes(resp.read())
            paths.append(str(dest))
        except Exception as e:
            print(f"  FAIL {u}: {e}")
        time.sleep(0.2)
    return paths


def fmt(r):
    return f"@{r.get('username') or ''}: {r.get('full_text') or ''}".strip()


downloaded = 0
def render_item(i, tid):
    global downloaded
    r = by_id[tid]
    parts = [f"ITEM {i}", f"TWEET by @{r.get('username')}: {r.get('full_text') or ''}"]
    if r.get("media"):
        paths = ensure_images(tid)
        if paths:
            for p in paths:
                parts.append(f"IMAGE FILE: {p}")
        else:
            parts.append("HAS_MEDIA: yes, but image unavailable — judge from text; "
                         "if the text alone is compatible with the tag, keep.")
    pid = r.get("reply_to_tweet_id")
    if pid and by_id.get(pid):
        parts.append(f"IN REPLY TO: {fmt(by_id[pid])}")
    q = r.get("quoted_tweet_id")
    if q and by_id.get(q):
        parts.append(f"QUOTED TWEET: {fmt(by_id[q])}")
    return "\n".join(parts)


HUMOUR_NOTE = """
CALIBRATION (this tag specifically): `humour` is known to be over-applied in this
dataset. Keep it only when comic effect is a primary payload of the tweet — the
tweet is a joke, bit, or absurdist play. REMOVE it when the tweet is a sincere
observation or insight that is merely witty, playful in tone, or uses an amusing
turn of phrase as a vehicle. Wit in service of a serious point is not `humour`.
"""

manifest = {}
bi = 0
for slug in slugs:
    tids = per_tag[slug]
    chunks = [tids[i:i + BATCH_SIZE] for i in range(0, len(tids), BATCH_SIZE)]
    for chunk in chunks:
        result_path = result_dir / f"batch_{bi:03d}.json"
        body = "\n\n".join(render_item(i, tid) for i, tid in enumerate(chunk))
        note = HUMOUR_NOTE if slug == "humour" else ""
        prompt = f"""You are auditing ONE tag on a curated tweet-anthology site for precision.

TAG UNDER REVIEW: `{slug}`

Its definition from the site taxonomy:

{sections[slug]}
{note}
Every tweet below currently carries the tag `{slug}` and sits near the top of
the site's ranking, so mistakes here are highly visible. For each ITEM decide:

- "keep"   — the tag genuinely applies. Tweets carry up to 4 tags (AND
             semantics), so `{slug}` need not be the *best* tag, just a correct
             one. Borderline-but-defensible stays. When an ITEM has IMAGE FILE
             lines you MUST Read each image before judging — the image is often
             the payload.
- "remove" — a reasonable curator would object to this tag on this tweet:
             the tweet merely *mentions* the topic rather than being about it,
             or the tag is a clear misread. Give a one-line reason.

Precision only: do NOT suggest additional tags; do not judge the tweet's other
tags.

First, use the Write tool to save your verdicts to this exact path:
{result_path}
as a JSON array: [{{"index": 0, "verdict": "keep"}}, {{"index": 1, "verdict": "remove", "reason": "..."}}, ...]
Indexes MUST match the ITEM numbers exactly; every ITEM appears exactly once.

Then return {{"tag": "{slug}", "reviewed": <n items>, "removed": <n removes>}} via StructuredOutput.

# Tweets

{body}
"""
        (prompt_dir / f"batch_{bi:03d}.txt").write_text(prompt)
        manifest[str(bi)] = {"tag": slug, "tweet_ids": chunk}
        bi += 1

(work / "manifest.json").write_text(json.dumps(manifest))
print(f"batches: {bi} x <= {BATCH_SIZE}")
