# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this project is

Static anthology site of top tweets from the TPOT community. Two halves:

- A Python build pipeline (`build.py`) that turns `enriched_tweets.parquet` (~860 MB, 7.9 M rows) into three small JSON files in `site/data/`.
- A vanilla-JS static site (`site/`) that loads those JSONs, renders a paginated, filterable feed, and is deployable by drag-and-drop to Netlify.

There is **no backend, no framework, no build step at deploy time**. The brief and important context for the design are in `README.md`.

## Common commands

```bash
# Setup (once)
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Fast iteration build — skips syndication fetch entirely
python build.py --no-media

# Full build — fetches media metadata + external quote tweets from
# cdn.syndication.twimg.com. Cold cost ~25 min; resumable (see `cache/`).
python build.py

# Top-N override (default 5,000 per metric)
python build.py --top-n 1000

# Preview the site locally
python3 -m http.server 5173 --directory site
# or use the preview agent's launch.json (auto-port via $PORT)
```

The dev preview server is configured in `.claude/launch.json` (`autoPort: true`, reads `$PORT`).

## Build pipeline mental model

`build.py` runs in this order. Each stage prints a `=== Section ===` banner and diagnostics:

1. **Load + dedupe** parquet → identify the ~340 archive accounts (rows where `archive_upload_id` is non-null).
2. **Compute corpus-wide QT counts** from `quoted_tweet_id` references across the *full* deduped corpus, **excluding self-quotes**.
3. **Build primary set**: archive-account rows that do not start with "RT @". Replies are kept.
4. **Take top-N per metric** (`retweet_count`, `favorite_count`, `qt_count`).
5. **Gather local context tweets** by walking up to 3 reply ancestors and one quote level for each top tweet.
6. **Media fetch** (concurrent, rate-limited): for any tweet whose text contains `t.co/`, `pic.twitter.com/`, or `pic.x.com/`, hit `cdn.syndication.twimg.com/tweet-result` and extract `media`, `url_expansions`, `media_tcos`.
7. **External quote fetch**: for any `quoted_tweet_id` that does *not* resolve to a tweet in the loaded set or the wider corpus, fetch the syndication response and produce a context record marked `is_external: true`. Reuses the same cache + rate limiter.
8. **Write** `site/data/{top_rt,top_likes,top_qt}.json`.

### Important invariants

- Tweet IDs are **always strings** — JS would lose precision otherwise.
- Tweet IDs in `reply_to_tweet_id` and `quoted_tweet_id` may have stray `?s=20`-style suffixes in the parquet; `_normalize_tweet_id()` strips them at every entry point. Frontend lookups by ID assume cleaned IDs.
- Self-quotes (a user QTing their own tweet) are excluded from `qt_count`.
- `media_tcos` lists the t.co URLs that twitter auto-appends for the tweet's *own* attached media. The frontend strips these from displayed text when media renders inline. Mid-text t.co links to external URLs are preserved and resolved via `url_expansions`.
- Syndication token: `_float_to_base36((int(tweet_id) / 1e15) * pi)` with `0` and `.` stripped, mirroring twitter's JS recipe. See `_load_syndication`.
- The `cache/` directory is keyed by tweet_id and shared between media + external-quote fetches. Failed fetches return None silently and are not cached.
- Ratelimit is global across all worker threads (`_RateLimiter` token bucket), 5 req/sec by default. 8 worker threads.

## Frontend mental model

`site/js/app.js` is a single IIFE. State lives on a private `state` object: `{metric, year, search, visible, cache, loading}`. Three things drive the render:

- **`loadMetric(metric)`** — fetches the per-metric JSON once, caches it in `state.cache[metric]`, builds a `byId: Map` for O(1) tweet lookup. The same JSON contains primary + local-context + external-context records, distinguished by `is_context` and `is_external` booleans.
- **`getFiltered()`** — applies year and search filters in-memory. `@`-prefixed search queries strip the `@` for username matching.
- **`render()`** — slices to `state.visible` (default 100; +100 per "Load more" click), builds DOM nodes via `renderCard`. Reply ancestors and quoted tweets are looked up in `byId`; missing ones fall back to "Quoted tweet unavailable" / "Earlier in thread →".

### Frontend gotchas worth knowing

- **`<meta name="referrer" content="no-referrer">`** in `index.html` is critical. `video.twimg.com` returns 403 if the request includes a Referer pointing anywhere other than twitter.com. The `<video>` element does not support the `referrerpolicy` attribute (per spec it's only on `<a>`, `<img>`, `<iframe>`, `<link>`, `<script>`, `<area>`), so the page-level meta is the only way to make embedded videos play.
- **Asset cache busting** — `index.html` references `css/style.css?v=N` and `js/app.js?v=N`. Bump the version (`Edit ... replace_all=true`) when you change CSS or JS, or browsers will serve stale files. Python's `http.server` doesn't send `Cache-Control` headers.
- **HTML entities** — twitter syndication and the parquet text both contain `&amp;`, `&lt;` etc. `htmlDecode()` runs every body through a textarea trick before linkifying.
- **Display toggles** are settings in a popover behind a cog icon (`#settings-btn`). Body classes: `.content-only` (hide avatars/handles/dates), `.no-links` (hide outbound x.com links + "Open on X"). Both persist via `localStorage` keys `bob.contentOnly` and `bob.hideLinks`.
- **Image / video error handling**: broken `<img>` removes itself silently; broken `<video>` keeps its poster visible (don't auto-remove videos — playback errors are common and removing them on click-to-play looks like the card is broken).

## Aesthetic constraints

The brief in `README.md` and `site/css/style.css` define the design language:

- Warm parchment palette (`--bg: #f6f1e7`), deep cinnabar single accent (`--accent: #7a2a1f`), Source Serif body, Inter for chrome.
- "Anthology, not feed" — pagination is intentional (no infinite scroll), animations are minimal, no drop shadows except a tiny one on dialogs/popovers, no playful motion. Don't add a "share" button or social affordances.
- Light mode only. Mobile responsive (single media query at 640 px).

## Things to *not* do

- Don't introduce a framework (no React/Vue/Svelte/Next). The brief is explicit; vanilla JS keeps the deploy artefact small and the project long-lived.
- Don't refetch JSON every render — use `state.cache`.
- Don't add Referer-revealing tracking, third-party scripts, or anything that breaks the no-backend property.
- Don't change the tweet-record schema without updating both `_row_to_record` and `_extract_external_record` in `build.py` so local + external records stay symmetric.
