# Book of Bangers

A static site that turns the [Community Archive](https://www.community-archive.org/) parquet
into a browsable anthology of top tweets from the TPOT community, ranked by likes,
retweets, and quote-tweets.

## What's in here

```
build.py                  pipeline: parquet  →  site/data/*.json
requirements.txt
cache/                    on-disk cache for the syndication API (gitignored)
enriched_tweets.parquet   input data (gitignored, ~860 MB)
site/                     the deployable site — drag this folder onto Netlify
  index.html
  css/style.css
  js/app.js
  data/top_rt.json
  data/top_likes.json
  data/top_qt.json
```

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Drop `enriched_tweets.parquet` in the project root.

## Running the build

```bash
# fast iteration, no media fetching
python build.py --no-media

# full build (fetches media metadata from cdn.syndication.twimg.com — ~20 min cold,
# resumable thanks to cache/)
python build.py
```

Diagnostics print to stdout: row counts, dedup, retweets filtered, year breakdown,
top-5 preview per metric, and per-file output sizes. Use these to sanity-check
each run.

`build.py` writes the three JSON files directly into `site/data/`.

## Previewing locally

The site is fully static — any local file server will do.

```bash
python3 -m http.server 5173 --directory site
# → open http://localhost:5173
```

## Deploying

Drag the `site/` folder onto [Netlify](https://app.netlify.com/drop) (or any
static host). No backend, no build step at deploy time.

## Notable decisions

- **Hand-rolled, no framework.** Vanilla JS, ~600 lines. Good fit for a small,
  long-lived static site.
- **Top 5,000 per metric, three separate files.** Each file is fetched on demand
  when you switch metrics; cached afterwards. Around 4–6 MB each ungzipped,
  ~1 MB after gzip.
- **Pagination is intentional.** 100 cards on load, then a button — never
  infinite scroll. The site is an anthology; every step deeper should be a
  deliberate choice.
- **Self-quotes excluded from QT counts.** A user retweeting their own thread
  shouldn't inflate the score.
- **Reply chains: up to 3 ancestors inlined**, then "Earlier in thread →".
- **Two persisted display toggles.** Reading mode (hide social layer) and a
  links toggle (hide all outbound x.com links to keep the anthology
  self-contained).
- **Light mode only**, mobile responsive. The aesthetic target is a printed
  literary magazine, not a social product.

## Caveats

- Counts are point-in-time, taken at the May 2026 snapshot.
- QT counts are *corpus-internal*: only quote-tweets present in the archive
  are counted. They are a lower bound.
- Media fetch occasionally fails (rate limits, deleted media, expired t.co
  redirects). Failures are logged and ignored — the card just renders without
  media. Re-running `build.py` retries failed fetches.
