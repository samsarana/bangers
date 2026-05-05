"""
Book of Bangers — build pipeline.

Reads enriched_tweets.parquet, produces three JSON files in site/data/
(top_rt.json, top_likes.json, top_qt.json) for the static site to load.

Usage:
    python build.py             # full pipeline including media fetching
    python build.py --no-media  # skip media fetching (fast iteration)
    python build.py --top-n 5000  # override default top-N (5000)
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
import time
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).parent
PARQUET = ROOT / "enriched_tweets.parquet"
OUT_DIR = ROOT / "site" / "data"
CACHE_DIR = ROOT / "cache"

SYNDICATION_URL = "https://cdn.syndication.twimg.com/tweet-result"
MEDIA_RATE_LIMIT_RPS = 5  # 2-5 per spec — global cap across all workers
MEDIA_WORKERS = 8         # concurrent in-flight requests; throttled to RPS above
MEDIA_TIMEOUT = 10


def banner(msg: str) -> None:
    print(f"\n=== {msg} ===")


def info(msg: str, flush: bool = False) -> None:
    print(f"  {msg}", flush=flush)


# ---------------------------------------------------------------------------
# Stage 1-4: load, identify archive accounts, dedupe, primary set
# ---------------------------------------------------------------------------

def load_and_filter(parquet_path: Path) -> tuple[pd.DataFrame, pd.DataFrame, set[str]]:
    """Returns (full_dedup, primary_set, archive_account_ids)."""
    banner("Load & filter")
    df = pd.read_parquet(parquet_path)
    info(f"Loaded {len(df):,} rows")

    archive_ids = set(df.loc[df["archive_upload_id"].notna(), "account_id"].unique())
    info(f"Archive accounts: {len(archive_ids):,}")
    info(f"Archive-account rows: {df['account_id'].isin(archive_ids).sum():,}")
    info(f"Liked-tweet (non-archive) rows: {(~df['account_id'].isin(archive_ids)).sum():,}")

    before = len(df)
    df = df.drop_duplicates(subset=["tweet_id"], keep="first").reset_index(drop=True)
    info(f"Deduplicated by tweet_id: {before - len(df):,} duplicates removed → {len(df):,} unique tweets")

    primary = df[df["account_id"].isin(archive_ids)].copy()
    text = primary["full_text"].fillna("")
    is_rt = text.str.startswith("RT @")
    info(f"Retweets in archive set: {is_rt.sum():,} (filtered out)")
    primary = primary[~is_rt].copy()
    info(f"Primary set size: {len(primary):,}")

    return df, primary, archive_ids


# ---------------------------------------------------------------------------
# Stage 5: corpus-wide QT counts
# ---------------------------------------------------------------------------

def compute_qt_counts(full: pd.DataFrame) -> pd.Series:
    """Returns Series indexed by tweet_id → qt_count, excluding self-quotes."""
    banner("Compute QT counts")
    quoting = full[full["quoted_tweet_id"].notna()][["tweet_id", "account_id", "quoted_tweet_id"]].copy()
    info(f"Tweets with a quoted_tweet_id: {len(quoting):,}")

    # Lookup author of the quoted tweet to detect self-quotes
    author_by_id = full.set_index("tweet_id")["account_id"]
    quoting["quoted_author"] = quoting["quoted_tweet_id"].map(author_by_id)

    self_q = quoting["quoted_author"] == quoting["account_id"]
    info(f"Self-quotes excluded: {self_q.sum():,}")
    quoting = quoting[~self_q]

    counts = quoting["quoted_tweet_id"].value_counts()
    info(f"Distinct tweets with at least one external QT: {len(counts):,}")
    return counts


# ---------------------------------------------------------------------------
# Stage 7: top-N per metric
# ---------------------------------------------------------------------------

def top_n(df: pd.DataFrame, metric: str, n: int) -> pd.DataFrame:
    sub = df.sort_values(metric, ascending=False, kind="mergesort").head(n).copy()
    return sub


# ---------------------------------------------------------------------------
# Stage 8: gather context tweets (replies up to 3 ancestors, quoted tweet)
# ---------------------------------------------------------------------------

def gather_context(top_ids: set[str], full_indexed: pd.DataFrame) -> set[str]:
    """Return set of context tweet_ids needed for the given top tweets."""
    context: set[str] = set()
    # Reply ancestors (up to 3 levels)
    frontier = set(top_ids)
    for _ in range(3):
        sub = full_indexed.reindex(list(frontier))
        parents = sub["reply_to_tweet_id"].dropna()
        new_parents = set(parents) - top_ids - context
        new_parents.discard(None)
        context |= new_parents
        if not new_parents:
            break
        frontier = new_parents
    # Quoted tweets (one level)
    sub = full_indexed.reindex(list(top_ids | context))
    quoted = sub["quoted_tweet_id"].dropna()
    new_q = set(quoted) - top_ids - context
    context |= new_q
    # Filter to those that actually exist in the corpus
    existing = set(full_indexed.index)
    return context & existing


# ---------------------------------------------------------------------------
# Stage 9: media fetching
# ---------------------------------------------------------------------------

_DIGITS_RE = __import__("re").compile(r"\d+")


def _normalize_tweet_id(tweet_id: str) -> str | None:
    """A handful of `quoted_tweet_id` values in the parquet contain stray
    suffixes like `?s=20` (people copy-paste tweet URLs into quote-tweet
    fields). Strip to digits-only; return None if nothing left."""
    if not tweet_id:
        return None
    m = _DIGITS_RE.search(str(tweet_id))
    return m.group(0) if m else None


def media_token(tweet_id: str) -> str:
    """Reproduce twimg syndication token: base36 of (id/1e15)*pi, stripped."""
    val = (int(tweet_id) / 1e15) * math.pi
    # base36 encoding of float repr with '0' and '.' stripped
    s = repr(val)  # e.g. "5.234567890123e+00" or "1234.5678"
    # convert each char of representation? The known recipe:
    #   token = base36(int_part) etc — but the standard pattern is:
    #     ((id / 1e15) * pi).toString(36).replace(/(0+|\.)/g, '')
    # Replicate the JS toString(36) for floats: we approximate via integer*36 expansion.
    # Easier: convert via known Python equivalent
    # Use: float_to_base36 approximation
    return _float_to_base36(val).replace("0", "").replace(".", "")


def _float_to_base36(x: float) -> str:
    """Mirror JavaScript Number.prototype.toString(36) for positive floats."""
    if x == 0:
        return "0"
    digits = "0123456789abcdefghijklmnopqrstuvwxyz"
    neg = x < 0
    x = abs(x)
    int_part = int(x)
    frac = x - int_part
    # integer portion
    if int_part == 0:
        int_str = "0"
    else:
        chars = []
        n = int_part
        while n:
            chars.append(digits[n % 36])
            n //= 36
        int_str = "".join(reversed(chars))
    # fractional portion — JS produces up to ~ a dozen base-36 digits
    frac_str = ""
    if frac > 0:
        frac_str = "."
        for _ in range(12):
            frac *= 36
            d = int(frac)
            frac -= d
            frac_str += digits[d]
            if frac == 0:
                break
        # trim trailing zeros (JS does this)
        frac_str = frac_str.rstrip("0").rstrip(".")
    s = int_str + frac_str
    return ("-" if neg else "") + s


def needs_media(text: str) -> bool:
    """Broad heuristic: any t.co or pic.* link in text means *might* have media.
    The previous "trailing t.co" rule missed long tweets where the auto-appended
    media link was stripped from the parquet text — so we now fetch on any t.co
    occurrence. False positives just return no mediaDetails and cost one HTTP
    call apiece; harmless and resumable via cache."""
    if not isinstance(text, str):
        return False
    return ("t.co/" in text) or ("pic.twitter.com/" in text) or ("pic.x.com/" in text)


def _load_syndication(tweet_id: str, session: requests.Session) -> dict | None:
    """Fetch (or load from cache) the raw syndication response for a tweet.
    Returns the parsed dict, or None on any failure. The on-disk cache is
    keyed by tweet_id and shared by every consumer (media extraction AND
    external-quote fetching)."""
    tweet_id = _normalize_tweet_id(tweet_id)
    if not tweet_id:
        return None

    cache_path = CACHE_DIR / f"{tweet_id}.json"
    if cache_path.exists():
        try:
            return json.loads(cache_path.read_text())
        except Exception:
            pass  # corrupt cache → refetch

    token = media_token(tweet_id)
    try:
        r = session.get(
            SYNDICATION_URL,
            params={"id": tweet_id, "token": token},
            timeout=MEDIA_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (book-of-bangers build)"},
        )
    except requests.RequestException:
        return None
    if r.status_code != 200 or not r.text.strip():
        return None
    try:
        data = r.json()
    except ValueError:
        return None
    if not isinstance(data, dict) or not data:
        return None
    cache_path.write_text(json.dumps(data))
    return data


def fetch_media(tweet_id: str, session: requests.Session) -> dict | None:
    """Returns {media, url_expansions, media_tcos} or None on failure.
    Resilient against missing or partial syndication data."""
    data = _load_syndication(tweet_id, session)
    if data is None:
        return None
    return _extract_all(data)


def _extract_all(data: dict) -> dict:
    return {
        "media": _extract_media(data),
        "url_expansions": _extract_url_expansions(data),
        "media_tcos": _extract_media_tcos(data),
    }


def _extract_media(data: dict) -> list[dict]:
    """Each entry: {type, url?, poster?}. type ∈ {photo, video, gif}."""
    out: list[dict] = []
    for m in data.get("mediaDetails") or []:
        t = m.get("type")
        if t == "photo":
            url = m.get("media_url_https") or m.get("media_url")
            if url:
                out.append({"type": "photo", "url": url})
        elif t in ("video", "animated_gif"):
            poster = m.get("media_url_https") or m.get("media_url")
            # Pick highest-bitrate mp4 variant if present.
            video_url = None
            variants = (m.get("video_info") or {}).get("variants") or []
            mp4s = [v for v in variants if v.get("content_type") == "video/mp4"]
            if mp4s:
                mp4s.sort(key=lambda v: v.get("bitrate") or 0, reverse=True)
                video_url = mp4s[0].get("url")
            entry: dict = {"type": "gif" if t == "animated_gif" else "video"}
            if poster:
                entry["poster"] = poster
            if video_url:
                entry["url"] = video_url
            # If neither url nor poster — drop it (nothing to render).
            if "url" in entry or "poster" in entry:
                out.append(entry)
    return out


def _extract_url_expansions(data: dict) -> list[dict]:
    """t.co → expanded_url + display_url, from entities.urls. Excludes media."""
    ents = data.get("entities") or {}
    out: list[dict] = []
    for u in ents.get("urls") or []:
        url = u.get("url")
        exp = u.get("expanded_url")
        if not url or not exp:
            continue
        out.append({
            "url": url,
            "expanded_url": exp,
            "display_url": u.get("display_url") or exp,
        })
    return out


def _extract_media_tcos(data: dict) -> list[str]:
    """t.co URLs that point to the tweet's own media (entities.media[].url).
    These are the ones we want to STRIP from displayed text when media renders."""
    ents = data.get("entities") or {}
    return [m.get("url") for m in (ents.get("media") or []) if m.get("url")]


# ---------------------------------------------------------------------------
# External quote extraction — turn a syndication response into a context tweet
# record for tweets we don't have in the local archive.
# ---------------------------------------------------------------------------

def _extract_external_record(data: dict) -> dict | None:
    """Build a JSON-ready tweet record from a syndication API response.
    Used for `quoted_tweet_id` references that don't resolve to a tweet in
    the local corpus, so the frontend can render them inline. Returns None
    if the response is missing the minimum fields we need.

    The shape matches what `_row_to_record` produces for local tweets, with
    two additions: `is_context: True` and `is_external: True`. retweet_count
    and qt_count default to 0 — the syndication endpoint doesn't return them
    for the focal tweet."""
    tid = data.get("id_str")
    text = data.get("text")
    user = data.get("user") or {}
    if not tid or not text or not user.get("screen_name"):
        return None

    created = data.get("created_at")  # e.g. "2025-09-11T02:08:45.000Z"
    year = 0
    created_iso = None
    if created:
        try:
            ts = pd.to_datetime(created, utc=True)
            created_iso = ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            year = int(ts.year)
        except Exception:
            created_iso = created

    quoted = data.get("quoted_tweet") or {}
    return {
        "tweet_id": str(tid),
        "account_id": str(user.get("id_str") or ""),
        "username": user.get("screen_name") or "",
        "account_display_name": user.get("name") or user.get("screen_name") or "",
        "avatar_media_url": user.get("profile_image_url_https") or None,
        "created_at": created_iso,
        "year": year,
        "full_text": text,
        "retweet_count": int(data.get("retweet_count") or 0),
        "favorite_count": int(data.get("favorite_count") or 0),
        "qt_count": 0,
        "reply_to_tweet_id": data.get("in_reply_to_status_id_str") or None,
        "reply_to_username": data.get("in_reply_to_screen_name") or None,
        "quoted_tweet_id": (quoted.get("id_str") if quoted else None) or None,
        "conversation_id": None,
        "media": _extract_media(data),
        "url_expansions": _extract_url_expansions(data),
        "media_tcos": _extract_media_tcos(data),
        "is_context": True,
        "is_external": True,
    }


def fetch_external_tweet(tweet_id: str, session: requests.Session) -> dict | None:
    """Fetch the syndication endpoint for `tweet_id` and return a context-tweet
    record, or None if the fetch failed or the response was unusable."""
    data = _load_syndication(tweet_id, session)
    if data is None:
        return None
    return _extract_external_record(data)


def fetch_all_external_quotes(candidates: list[str]) -> dict[str, dict]:
    """Concurrent + rate-limited fetch of external quoted tweets, sharing the
    same cache and limiter contract as `fetch_all_media`. Failures are silent;
    cache hits skip rate limiting (they're disk-only)."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    banner("External quote fetch")
    info(f"Candidates: {len(candidates):,}")
    CACHE_DIR.mkdir(exist_ok=True)
    cached = {tid for tid in candidates if (CACHE_DIR / f"{tid}.json").exists()}
    info(f"Cache hits: {len(cached):,}; to fetch: {len(candidates) - len(cached):,}")

    results: dict[str, dict] = {}
    session = requests.Session()
    limiter = _RateLimiter(MEDIA_RATE_LIMIT_RPS)
    fetched = failed = 0
    t_last_log = time.time()

    def _one(tid: str) -> tuple[str, dict | None]:
        if tid in cached:
            return tid, fetch_external_tweet(tid, session)
        limiter.acquire()
        return tid, fetch_external_tweet(tid, session)

    with ThreadPoolExecutor(max_workers=MEDIA_WORKERS) as ex:
        futs = {ex.submit(_one, tid): tid for tid in candidates}
        done = 0
        for fut in as_completed(futs):
            tid, record = fut.result()
            done += 1
            if record is None:
                failed += 1
            else:
                fetched += 1
                results[tid] = record
            if time.time() - t_last_log > 5:
                info(
                    f"  {done:,}/{len(candidates):,}   ok={fetched:,} fail={failed:,}",
                    flush=True,
                )
                t_last_log = time.time()
    info(f"Done. ok={fetched:,} fail={failed:,} (records: {len(results):,})")
    return results


class _RateLimiter:
    """Simple token-bucket throttle, thread-safe."""
    def __init__(self, rps: float):
        import threading
        self.min_interval = 1.0 / rps
        self.lock = threading.Lock()
        self.next_ok = 0.0

    def acquire(self) -> None:
        with self.lock:
            now = time.time()
            wait = self.next_ok - now
            if wait > 0:
                time.sleep(wait)
                now = time.time()
            self.next_ok = max(now, self.next_ok) + self.min_interval


def fetch_all_media(tweets_by_id: dict, candidates: list[str]) -> dict[str, dict]:
    """Returns {tweet_id: {media, url_expansions, media_tcos}} for all candidates
    that responded successfully. Tweets with no extractable data are still
    recorded (with empty lists) so the frontend gets the URL expansions even
    when there is no media."""
    from concurrent.futures import ThreadPoolExecutor, as_completed

    banner("Media fetch")
    info(f"Candidates: {len(candidates):,}")
    CACHE_DIR.mkdir(exist_ok=True)
    cached = {tid for tid in candidates if (CACHE_DIR / f"{tid}.json").exists()}
    info(f"Cache hits: {len(cached):,}; to fetch: {len(candidates) - len(cached):,}")

    results: dict[str, dict] = {}
    session = requests.Session()
    limiter = _RateLimiter(MEDIA_RATE_LIMIT_RPS)
    fetched = failed = with_media = with_urls = 0
    t_last_log = time.time()

    def _one(tid: str) -> tuple[str, dict | None]:
        # cache hit: skip rate limiter, hit disk only
        if tid in cached:
            return tid, fetch_media(tid, session)
        limiter.acquire()
        return tid, fetch_media(tid, session)

    with ThreadPoolExecutor(max_workers=MEDIA_WORKERS) as ex:
        futs = {ex.submit(_one, tid): tid for tid in candidates}
        done = 0
        for fut in as_completed(futs):
            tid, payload = fut.result()
            done += 1
            if payload is None:
                failed += 1
            else:
                fetched += 1
                results[tid] = payload
                if payload.get("media"):
                    with_media += 1
                if payload.get("url_expansions"):
                    with_urls += 1
            if time.time() - t_last_log > 5:
                info(
                    f"  {done:,}/{len(candidates):,}   "
                    f"ok={fetched:,} fail={failed:,} media={with_media:,} expansions={with_urls:,}",
                    flush=True,
                )
                t_last_log = time.time()
    info(
        f"Done. ok={fetched:,} fail={failed:,} "
        f"(with media: {with_media:,}; with url expansions: {with_urls:,})"
    )
    return results


# ---------------------------------------------------------------------------
# Output assembly
# ---------------------------------------------------------------------------

def to_records(
    primary_ids: list[str],
    context_ids: set[str],
    full_indexed: pd.DataFrame,
    media_map: dict[str, dict],
) -> list[dict]:
    """Assemble the JSON-ready list. Primary tweets first (in rank order), then context."""
    out: list[dict] = []
    seen: set[str] = set()
    for tid in primary_ids:
        if tid in seen:
            continue
        seen.add(tid)
        out.append(_row_to_record(full_indexed.loc[tid], tid, False, media_map))
    for tid in context_ids:
        if tid in seen:
            continue
        seen.add(tid)
        out.append(_row_to_record(full_indexed.loc[tid], tid, True, media_map))
    return out


def _row_to_record(row, tid: str, is_context: bool, media_map: dict[str, dict]) -> dict:
    def s_or_none(v):
        if v is None:
            return None
        if isinstance(v, float) and math.isnan(v):
            return None
        return str(v)

    def i_or_zero(v):
        if v is None or (isinstance(v, float) and math.isnan(v)):
            return 0
        return int(v)

    created = row["created_at"]
    if isinstance(created, str):
        # Format: '2022-01-13 05:49:56+00' → ISO 8601
        try:
            ts = pd.to_datetime(created, utc=True)
            created_iso = ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")
            year = int(ts.year)
        except Exception:
            created_iso = created
            year = 0
    elif pd.isna(created):
        created_iso = None
        year = 0
    else:
        ts = pd.Timestamp(created)
        created_iso = ts.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        year = int(ts.year)

    extra = media_map.get(tid) or {}
    return {
        "tweet_id": str(tid),
        "account_id": s_or_none(row.get("account_id")),
        "username": s_or_none(row.get("username")),
        "account_display_name": s_or_none(row.get("account_display_name")) or s_or_none(row.get("username")),
        "avatar_media_url": s_or_none(row.get("avatar_media_url")),
        "created_at": created_iso,
        "year": year,
        "full_text": s_or_none(row.get("full_text")) or "",
        "retweet_count": i_or_zero(row.get("retweet_count")),
        "favorite_count": i_or_zero(row.get("favorite_count")),
        "qt_count": i_or_zero(row.get("qt_count")),
        # Normalize reply/quote IDs — some parquet rows have stray "?s=20"
        # suffixes that break tweet-id lookups in the frontend (and the
        # syndication API). Always strip to digits-only.
        "reply_to_tweet_id": _normalize_tweet_id(s_or_none(row.get("reply_to_tweet_id"))),
        "reply_to_username": s_or_none(row.get("reply_to_username")),
        "quoted_tweet_id": _normalize_tweet_id(s_or_none(row.get("quoted_tweet_id"))),
        "conversation_id": s_or_none(row.get("conversation_id")),
        "media": extra.get("media", []),
        "url_expansions": extra.get("url_expansions", []),
        "media_tcos": extra.get("media_tcos", []),
        "is_context": is_context,
        "is_external": False,
    }


# ---------------------------------------------------------------------------
# Diagnostic helpers
# ---------------------------------------------------------------------------

def print_top_preview(label: str, df: pd.DataFrame, metric: str) -> None:
    info(f"top 5 by {label}:")
    for i, (_, row) in enumerate(df.head(5).iterrows(), 1):
        text = (row["full_text"] or "")[:100].replace("\n", " ")
        year = row.get("year", "?")
        val = int(row[metric]) if not pd.isna(row[metric]) else 0
        info(f"  {i}. @{row['username']} ({year}) — {metric}={val:,}  {text!r}")


def print_year_breakdown(df: pd.DataFrame) -> None:
    yr = df["year"].value_counts().sort_index()
    info(f"year range: {yr.index.min()}–{yr.index.max()}")
    for y, c in yr.items():
        info(f"  {y}: {c:,}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-media", action="store_true", help="skip syndication fetch")
    ap.add_argument("--top-n", type=int, default=5000, help="top N per metric")
    args = ap.parse_args()

    if not PARQUET.exists():
        sys.exit(f"missing {PARQUET}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(exist_ok=True)

    full, primary, archive_ids = load_and_filter(PARQUET)

    qt_counts = compute_qt_counts(full)

    banner("Parse dates & attach qt_count")
    primary["created_at_ts"] = pd.to_datetime(primary["created_at"], utc=True, errors="coerce")
    primary["year"] = primary["created_at_ts"].dt.year.fillna(0).astype(int)
    primary["qt_count"] = primary["tweet_id"].map(qt_counts).fillna(0).astype(int)
    primary["retweet_count"] = primary["retweet_count"].fillna(0).astype(int)
    primary["favorite_count"] = primary["favorite_count"].fillna(0).astype(int)
    print_year_breakdown(primary)

    # Index the full corpus by tweet_id once for fast context lookup
    full["created_at_ts"] = pd.to_datetime(full["created_at"], utc=True, errors="coerce")
    full["year"] = full["created_at_ts"].dt.year.fillna(0).astype(int)
    full["qt_count"] = full["tweet_id"].map(qt_counts).fillna(0).astype(int)
    full["retweet_count"] = full["retweet_count"].fillna(0).astype(int)
    full["favorite_count"] = full["favorite_count"].fillna(0).astype(int)
    full_indexed = full.set_index("tweet_id", drop=False)

    sets: dict[str, pd.DataFrame] = {}
    for label, metric in [("rt", "retweet_count"), ("likes", "favorite_count"), ("qt", "qt_count")]:
        banner(f"Top {args.top_n:,} by {metric}")
        sub = top_n(primary, metric, args.top_n)
        sets[label] = sub
        print_top_preview(label, sub, metric)

    # Gather context for the union of all top tweets, then per-set we filter
    banner("Gather context tweets")
    all_top_ids: set[str] = set()
    per_set_top_ids: dict[str, list[str]] = {}
    for label, sub in sets.items():
        ids = sub["tweet_id"].tolist()
        per_set_top_ids[label] = ids
        all_top_ids.update(ids)
    context_ids = gather_context(all_top_ids, full_indexed)
    info(f"Context tweets identified (union): {len(context_ids):,}")

    # Identify media candidates (only fetch once per tweet_id across all sets)
    needed_ids = all_top_ids | context_ids
    media_map: dict[str, list[str]] = {}
    if not args.no_media:
        candidates = []
        for tid in needed_ids:
            row = full_indexed.loc[tid]
            text = row["full_text"]
            if needs_media(text if isinstance(text, str) else ""):
                candidates.append(tid)
        media_map = fetch_all_media(full_indexed, candidates)
    else:
        info("--no-media: skipping syndication fetch")

    # Compute per-set context (local) once per set, then identify quoted tweets
    # they reference that aren't anywhere in the local archive.
    banner("Identify external quote candidates")
    per_set_local: dict[str, dict] = {}
    in_corpus = set(full_indexed.index)
    all_external: set[str] = set()
    for label, primary_ids_list in per_set_top_ids.items():
        primary_set = set(primary_ids_list)
        per_context = gather_context(primary_set, full_indexed)
        local_ids = primary_set | per_context
        # quoted_tweet_ids referenced by anything in this set, deduped and
        # normalized (some parquet values have "?s=20"-style suffixes)
        sub = full_indexed.reindex(list(local_ids))
        quoted_refs = set()
        for q in sub["quoted_tweet_id"].dropna():
            n = _normalize_tweet_id(q)
            if n:
                quoted_refs.add(n)
        external = {q for q in quoted_refs if q not in local_ids and q not in in_corpus}
        per_set_local[label] = {
            "primary_ids": primary_ids_list,
            "context_ids": per_context,
            "external_ids": external,
        }
        info(
            f"{label}: primary={len(primary_set):,}  context={len(per_context):,}  "
            f"missing-quoted={len(external):,}"
        )
        all_external |= external
    info(f"Unique external quote candidates across all sets: {len(all_external):,}")

    # Fetch external tweets concurrently. Reuses the same cache & rate limit as
    # media fetching — many will already be cached from the media pass.
    external_records: dict[str, dict] = {}
    if not args.no_media:
        if all_external:
            external_records = fetch_all_external_quotes(sorted(all_external))
    else:
        info("--no-media: skipping external quote fetch")

    banner("Write outputs")
    file_map = {"rt": "top_rt.json", "likes": "top_likes.json", "qt": "top_qt.json"}
    for label in sets.keys():
        info_set = per_set_local[label]
        primary_ids = info_set["primary_ids"]
        per_context = info_set["context_ids"]
        records = to_records(primary_ids, per_context, full_indexed, media_map)

        # Append external context records (in stable id-sorted order so
        # rebuilds are deterministic).
        ext_added = 0
        for tid in sorted(info_set["external_ids"]):
            rec = external_records.get(tid)
            if rec is not None:
                records.append(rec)
                ext_added += 1

        out_path = OUT_DIR / file_map[label]
        with out_path.open("w") as f:
            json.dump(records, f, ensure_ascii=False, separators=(",", ":"))
        size_mb = out_path.stat().st_size / 1e6
        primary_count = sum(1 for r in records if not r["is_context"])
        local_ctx = sum(1 for r in records if r["is_context"] and not r.get("is_external"))
        info(
            f"{out_path.name}: {primary_count:,} primary + {local_ctx:,} local-context "
            f"+ {ext_added:,} external-context = {len(records):,} ({size_mb:.1f} MB)"
        )

    banner("Done")


if __name__ == "__main__":
    main()
