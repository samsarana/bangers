"""Vision-pass prep (Phase 3b + Phase 5): download media and build vision prompts.

Usage: python3 scripts/eval/prep_vision.py <ids_json> <workdir> [--csv seed|full]

- <ids_json>: JSON array of tweet_ids needing vision.
- <workdir>: prompts land in <workdir>/vision_prompts, images in <workdir>/images,
  results expected in <workdir>/vision_results.

Media URL selection: photo -> url, video/gif -> poster. Tweets with no usable
URL (media removed / fetch failed at build time) are listed in no_media.json —
their merge fallback is handled downstream, no agent is spawned.

Vision agents get batches of up to 5 tweets; each item names its local image
path and the agent must Read every image before classifying.
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BATCH_SIZE = 5

ids = json.loads(Path(sys.argv[1]).read_text())
work = Path(sys.argv[2])
img_dir = work / "images"
prompt_dir = work / "vision_prompts"
result_dir = work / "vision_results"
for d in (img_dir, prompt_dir, result_dir):
    d.mkdir(parents=True, exist_ok=True)

PREFIX = (ROOT / "scripts/eval/classifier_prompt_prefix.txt").read_text()

by_id = {}
for f in ["top_rt", "top_likes", "top_qt"]:
    for r in json.load(open(ROOT / "site/data" / f"{f}.json")):
        by_id.setdefault(r["tweet_id"], r)


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


def fmt(r):
    return f"@{r.get('username') or ''}: {r.get('full_text') or ''}".strip()


def download(url, dest):
    if dest.exists() and dest.stat().st_size > 0:
        return True
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            dest.write_bytes(resp.read())
        return True
    except Exception as e:
        print(f"  FAIL {url}: {e}")
        return False


items = []       # (tweet_id, [image paths])
no_media = []
for tid in ids:
    r = by_id.get(tid)
    urls = media_urls(r) if r else []
    paths = []
    for j, u in enumerate(urls):
        ext = ".jpg" if ".png" not in u.lower() else ".png"
        dest = img_dir / f"{tid}_{j}{ext}"
        if download(u, dest):
            paths.append(str(dest))
        time.sleep(0.2)
    if paths:
        items.append((tid, paths))
    else:
        no_media.append(tid)

print(f"ids: {len(ids)}; with images: {len(items)}; no usable media: {len(no_media)}")
(work / "no_media.json").write_text(json.dumps(no_media))


def render_item(i, tid, paths):
    r = by_id[tid]
    parts = [f"ITEM {i}", "HAS_MEDIA: yes (image file(s) provided below — you MUST Read them)"]
    for p in paths:
        parts.append(f"IMAGE FILE: {p}")
    parts.append(f"TWEET: {r.get('full_text') or ''}")
    # reply/quote context, same as text pass
    chain, seen = [], set()
    pid = r.get("reply_to_tweet_id")
    while pid and pid not in seen:
        seen.add(pid)
        pr = by_id.get(pid)
        if not pr:
            break
        chain.append(fmt(pr))
        pid = pr.get("reply_to_tweet_id")
    if chain:
        chain.reverse()
        parts.append("REPLY CONTEXT (ancestors, oldest first):\n" + "\n---\n".join(chain))
    q = r.get("quoted_tweet_id")
    qr = by_id.get(q) if q else None
    if qr:
        parts.append(f"QUOTED TWEET: {fmt(qr)}")
    return "\n".join(parts)


batches = [items[i : i + BATCH_SIZE] for i in range(0, len(items), BATCH_SIZE)]
idmap = {}
for bi, batch in enumerate(batches):
    result_path = result_dir / f"batch_{bi:03d}.json"
    body = "\n\n".join(render_item(i, tid, paths) for i, (tid, paths) in enumerate(batch))
    prompt = f"""{PREFIX}

# Vision instructions

Every ITEM below has attached media, downloaded locally. Before classifying an
ITEM you MUST use the Read tool on each of its IMAGE FILE paths and incorporate
what the image shows. The image is often the tweet's entire payload. After
seeing the image, media_dependent should be reported as false ONLY if you can
now tag confidently; if the image still leaves the meaning unclear, keep
media_dependent true and use `unknown` with confidence "low".

# Output instructions

Classify every ITEM. For each, produce: index (the ITEM number), tags (array of
slugs), confidence ("high"|"med"|"low"), media_dependent (boolean), and
optionally proposed_new_tag. Indexes MUST match the ITEM numbers exactly and
every ITEM must appear exactly once.

First, use the Write tool to save your predictions to this exact path:
{result_path}
as a JSON array: [{{"index": 0, "tags": [...], "confidence": "...", "media_dependent": false}}, ...]

Then return the same predictions via the StructuredOutput tool.

# Batch

{body}
"""
    (prompt_dir / f"batch_{bi:03d}.txt").write_text(prompt)
    for i, (tid, _) in enumerate(batch):
        idmap[f"{bi}:{i}"] = tid

(work / "vision_idmap.json").write_text(json.dumps(idmap))
print(f"vision batches: {len(batches)} x <= {BATCH_SIZE}")
