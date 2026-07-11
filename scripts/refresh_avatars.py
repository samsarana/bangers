"""Refresh dead avatar URLs in the site data.

Usage: python3 scripts/refresh_avatars.py

Old pbs.twimg.com/profile_images URLs die whenever an account changes its
picture, so a snapshot's avatars rot over time. For every unique primary
account: HEAD-check the stored URL; if dead, ask Twitter's syndication
profile endpoint for the current one and verify it's alive.

Verified replacements go to data/avatar_refresh.json ({username_lower: url})
and are patched into the three site JSONs in place (every record for that
username, context included). build.py re-applies the map at its write stage
so a rebuild from the parquet doesn't resurrect dead URLs. Accounts that are
gone entirely (suspended/renamed) stay dead — the frontend's initial-letter
fallback covers them.

Idempotent; re-run any time avatars look stale.
"""
import json
import re
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_PATH = ROOT / "data" / "avatar_refresh.json"
UA = {"User-Agent": "Mozilla/5.0"}
FILES = ["top_rt", "top_likes", "top_qt"]


def alive(url):
    req = urllib.request.Request(url, method="HEAD", headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception:
        return False


def fresh_avatar(username):
    # The endpoint rate-limits hard (429 at anything quicker than a few
    # seconds per request) — back off and retry rather than giving up.
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{username}"
    for attempt in range(4):
        req = urllib.request.Request(url, headers=UA)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = resp.read().decode("utf-8", "replace")
            m = re.search(r'"profile_image_url_https"\s*:\s*"([^"]+)"', body)
            return m.group(1).replace("\\/", "/") if m else None
        except Exception as e:
            if getattr(e, "code", None) == 429 and attempt < 3:
                time.sleep(30 * (attempt + 1))
                continue
            print(f"  {username}: profile fetch failed ({e})")
            return None


# 1. collect unique primary accounts and their stored avatar URL
stored = {}
data = {}
for f in FILES:
    data[f] = json.loads((ROOT / "site/data" / f"{f}.json").read_text())
    for r in data[f]:
        if not r.get("is_context") and r.get("avatar_media_url"):
            stored.setdefault(r["username"], r["avatar_media_url"])

# 2. find dead ones (concurrent HEADs)
with ThreadPoolExecutor(16) as ex:
    ok = dict(zip(stored, ex.map(alive, stored.values())))
dead = [u for u, is_ok in ok.items() if not is_ok]
print(f"accounts: {len(stored)}; dead avatar URLs: {len(dead)}")

# 3. resolve current avatars for the dead ones (gentle: sequential + sleep)
refresh = json.loads(MAP_PATH.read_text()) if MAP_PATH.exists() else {}
resolved = 0
for u in dead:
    cur = fresh_avatar(u)
    time.sleep(8)
    if cur and cur != stored[u] and alive(cur):
        refresh[u.lower()] = cur
        resolved += 1
        print(f"  {u}: refreshed")
    else:
        print(f"  {u}: no live replacement (account gone?) — initial fallback")
print(f"resolved {resolved}/{len(dead)}")

MAP_PATH.write_text(json.dumps(refresh, indent=1))

# 4. patch the site JSONs in place
for f in FILES:
    n = 0
    for r in data[f]:
        url = refresh.get((r.get("username") or "").lower())
        if url and r.get("avatar_media_url") != url:
            r["avatar_media_url"] = url
            n += 1
    out = ROOT / "site/data" / f"{f}.json"
    out.write_text(json.dumps(data[f], ensure_ascii=False, separators=(",", ":")))
    print(f"{f}.json: {n} records patched")
print(f"map: {MAP_PATH} ({len(refresh)} accounts)")
