"""
Phase 1 — Seed sampler + Haiku pre-labelling pass.

Draws 150 tweets (50 per metric file), stratified by year and media presence,
then asks Haiku to propose 3 free-form tags per tweet.

Output: seed_labels.csv  (tweet_id, source_file, full_text, has_media,
                           suggested_tags, your_tags, notes)

Usage:
    python scripts/sample_seed.py [--dry-run]
    ANTHROPIC_API_KEY=... python scripts/sample_seed.py
"""

import argparse
import csv
import json
import math
import os
import random
import sys
import textwrap
from pathlib import Path

import anthropic

ROOT = Path(__file__).parent.parent
DATA = ROOT / "site" / "data"
OUT  = ROOT / "seed_labels.csv"

SEED = 42
PER_FILE = 50
MEDIA_FRACTION = 1 / 3          # ~17 of 50 should have media

EXAMPLE_TAGS = (
    "relationships, humour, practical-philosophy, culture, community, "
    "confronting, productivity, twitter-meta"
)

SYSTEM_PROMPT = textwrap.dedent(f"""
    You are a thematic tagger for a curated archive of short social-media posts
    from the TPOT / intellectual-Twitter community (roughly 2011–2026).

    For each tweet you receive, propose exactly 3 free-form thematic tags.

    Guidelines:
    - Tags should name the *theme or emotional register* of the post, not its
      literal topic. Good examples: {EXAMPLE_TAGS}.
    - Use lowercase-hyphenated slugs (e.g. "practical-philosophy", not
      "Practical Philosophy").
    - Be specific enough to be useful but general enough to apply to many tweets.
    - If the tweet is media-only or hard to read without images, still propose
      your best 3 tags from context clues in the text.
    - Do NOT propose: "other", "misc", "unclassified", or meta-comments like
      "needs-context".

    Respond with a JSON array of exactly 3 strings, nothing else.
    Example: ["humour", "culture", "twitter-meta"]
""").strip()


def load_primaries(fname: str) -> list[dict]:
    path = DATA / f"{fname}.json"
    with open(path) as f:
        data = json.load(f)
    return [t for t in data if not t.get("is_context") and not t.get("is_external")]


def stratified_sample(tweets: list[dict], n: int, rng: random.Random) -> list[dict]:
    """
    Sample n tweets stratified by year, with MEDIA_FRACTION having media.
    Within each stratum mixes high-rank (first 20% of list) and mid/low.
    """
    n_media    = round(n * MEDIA_FRACTION)
    n_no_media = n - n_media

    media_pool    = [t for t in tweets if t.get("media")]
    no_media_pool = [t for t in tweets if not t.get("media")]

    def year_stratified(pool: list[dict], count: int) -> list[dict]:
        if not pool:
            return []
        by_year: dict[int, list[dict]] = {}
        for t in pool:
            by_year.setdefault(t["year"], []).append(t)

        years = sorted(by_year)
        # proportional allocation with a minimum of 1 per year if budget allows
        alloc: dict[int, int] = {}
        remaining = count
        for yr in years:
            share = max(1, round(len(by_year[yr]) / len(pool) * count))
            alloc[yr] = share
        # trim/pad to exactly `count`
        total = sum(alloc.values())
        delta = count - total
        sorted_years = sorted(years, key=lambda y: len(by_year[y]), reverse=True)
        i = 0
        while delta != 0:
            yr = sorted_years[i % len(sorted_years)]
            alloc[yr] += 1 if delta > 0 else -1
            alloc[yr] = max(0, alloc[yr])
            delta += -1 if delta > 0 else 1
            i += 1

        result = []
        for yr, k in alloc.items():
            if k <= 0:
                continue
            pool_yr = by_year[yr]
            cutoff = max(1, math.ceil(len(pool_yr) * 0.20))
            high   = pool_yr[:cutoff]
            low    = pool_yr[cutoff:]
            n_high = max(1, round(k * 0.40))
            n_low  = k - n_high
            picked = rng.sample(high, min(n_high, len(high)))
            picked += rng.sample(low,  min(n_low,  len(low)))
            # if we fell short, top up from whichever side has leftovers
            remaining_pool = [t for t in pool_yr if t not in picked]
            while len(picked) < k and remaining_pool:
                extra = rng.choice(remaining_pool)
                picked.append(extra)
                remaining_pool.remove(extra)
            result.extend(picked[:k])
        return result

    sample_media    = year_stratified(media_pool,    n_media)
    sample_no_media = year_stratified(no_media_pool, n_no_media)
    combined = sample_media + sample_no_media
    rng.shuffle(combined)
    return combined


def haiku_tags(client: anthropic.Anthropic, tweet: dict, dry_run: bool) -> str:
    if dry_run:
        return "humour;culture;twitter-meta"

    text = tweet["full_text"]
    has_media = bool(tweet.get("media"))
    user_msg = f"Tweet: {text}"
    if has_media:
        user_msg += "\n[This tweet has attached media not shown here.]"

    try:
        resp = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=64,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = resp.content[0].text.strip()
        tags = json.loads(raw)
        if isinstance(tags, list) and len(tags) == 3:
            return ";".join(str(t).strip() for t in tags)
        return raw.replace('"', "").replace("[", "").replace("]", "").replace(",", ";")
    except Exception as e:
        print(f"  [warn] Haiku call failed for {tweet['tweet_id']}: {e}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Skip Haiku API calls; write placeholder tags")
    args = parser.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not args.dry_run:
        print("Error: ANTHROPIC_API_KEY not set. Use --dry-run to skip API calls.",
              file=sys.stderr)
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key) if not args.dry_run else None
    rng = random.Random(SEED)

    files = ["top_rt", "top_likes", "top_qt"]
    all_samples: list[tuple[str, dict]] = []

    for fname in files:
        tweets = load_primaries(fname)
        sample = stratified_sample(tweets, PER_FILE, rng)
        print(f"{fname}: sampled {len(sample)} "
              f"({sum(1 for t in sample if t.get('media'))} with media, "
              f"years {sorted(set(t['year'] for t in sample))})")
        all_samples.extend((fname, t) for t in sample)

    total = len(all_samples)
    print(f"\nTotal: {total} tweets. Running Haiku pre-labelling pass...")

    rows = []
    for i, (source, tweet) in enumerate(all_samples, 1):
        print(f"  [{i}/{total}] {tweet['tweet_id']} ({source})", end=" ", flush=True)
        suggested = haiku_tags(client, tweet, args.dry_run)
        print(f"→ {suggested}")
        rows.append({
            "tweet_id":      tweet["tweet_id"],
            "source_file":   source,
            "full_text":     tweet["full_text"],
            "has_media":     "yes" if tweet.get("media") else "no",
            "suggested_tags": suggested,
            "your_tags":     "",
            "notes":         "",
        })

    with open(OUT, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["tweet_id", "source_file", "full_text", "has_media",
                        "suggested_tags", "your_tags", "notes"],
        )
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nWrote {len(rows)} rows → {OUT}")
    print("Open seed_labels.csv, fill in 'your_tags' for each row, then proceed to Phase 2.")


if __name__ == "__main__":
    main()
