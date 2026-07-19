"""Refresh dead avatar URLs in the site data.

Usage: python3 scripts/refresh_avatars.py

Old pbs.twimg.com/profile_images URLs die whenever an account changes its
picture, so a snapshot's avatars rot over time. For every unique primary
account: HEAD-check the stored URL; if dead, fetch any of the account's
tweets from cdn.syndication.twimg.com/tweet-result (whose payload carries
the account's current profile image) and verify the replacement is alive.

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


def _float_to_base36(x):
    """Mirror JavaScript Number.prototype.toString(36) (build.py's copy)."""
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    int_part, frac = int(x), x - int(x)
    chars, n = [], int_part
    while n:
        chars.append(digits[n % 36])
        n //= 36
    s = "".join(reversed(chars)) or "0"
    if frac > 0:
        s += "."
        for _ in range(12):
            frac *= 36
            d = int(frac)
            frac -= d
            s += digits[d]
            if frac == 0:
                break
        s = s.rstrip("0").rstrip(".")
    return s


def media_token(tweet_id):
    """twimg syndication token: base36 of (id/1e15)*pi, '0' and '.' stripped."""
    import math
    return _float_to_base36((int(tweet_id) / 1e15) * math.pi).replace("0", "").replace(".", "")


def fresh_avatar(username, tweet_id):
    # cdn.syndication.twimg.com/tweet-result (the endpoint build.py uses for
    # media; tolerates ~5 req/s) returns the account's CURRENT profile image
    # alongside any of its tweets. Far kinder than the timeline-profile
    # endpoint, which 429s after a handful of requests.
    url = (f"https://cdn.syndication.twimg.com/tweet-result"
           f"?id={tweet_id}&token={media_token(tweet_id)}")
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            d = json.loads(resp.read().decode("utf-8", "replace"))
        return (d.get("user") or {}).get("profile_image_url_https")
    except Exception as e:
        print(f"  {username}: tweet-result fetch failed ({e})")
        return None


# 1. collect unique primary accounts, their stored avatar URL, and one
#    (most recent) tweet id to hand to the tweet-result endpoint
stored = {}
sample_tid = {}
data = {}
for f in FILES:
    data[f] = json.loads((ROOT / "site/data" / f"{f}.json").read_text())
    for r in data[f]:
        if not r.get("is_context") and r.get("avatar_media_url"):
            stored.setdefault(r["username"], r["avatar_media_url"])
            tid = r["tweet_id"]
            if int(tid) > int(sample_tid.get(r["username"], "0")):
                sample_tid[r["username"]] = tid

# 2. find dead ones (concurrent HEADs)
with ThreadPoolExecutor(16) as ex:
    ok = dict(zip(stored, ex.map(alive, stored.values())))
dead = [u for u, is_ok in ok.items() if not is_ok]
print(f"accounts: {len(stored)}; dead avatar URLs: {len(dead)}")

# 3. resolve current avatars for the dead ones (gentle: sequential + sleep)
refresh = json.loads(MAP_PATH.read_text()) if MAP_PATH.exists() else {}
resolved = 0
for u in dead:
    cur = fresh_avatar(u, sample_tid[u])
    time.sleep(0.3)
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
