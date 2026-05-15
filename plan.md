# Tag system for Book of Bangers

## Context

The site currently lets readers filter by year and search text. There is no thematic browsing — a visitor who wants "the funny ones" or "the relationships ones" has to scroll. Adding a tag system makes ~10,700 unique primary tweets navigable by theme.

The three JSONs are not equivalent populations. `top_rt` and `top_likes` overlap ~67%; `top_qt` overlaps the other two only ~15% and skews toward provocations/frameworks rather than punchy/personal posts. A taxonomy seeded only from one file will under-cover the others. ~33% of tweets have media; for some, text alone is uninterpretable.

The pipeline must:

1. Produce a stable, reader-friendly taxonomy (≤100 tags) that covers all three corpora.
2. Auto-label ~10,700 unique primaries within Claude Pro limits.
3. Handle media-dependent tweets with a principled default rather than a half-fix.
4. Surface low-confidence cases so the user can review without reading everything.
5. Ship to the static frontend with minimal schema churn.

## Phased plan

### Phase 1 — Seed labelling (user, with Haiku assist) ✅ COMPLETE

**Goal:** Give the model enough labelled examples to derive a coherent taxonomy.

**Sample:** A small Python script (`scripts/sample_seed.py`) draws **150 tweets** stratified across the three files (~50 each), with a mix of high/low engagement, ~⅓ with media, and spread across years.

**Pre-labelling pass:** Before you label, Haiku (spawned via the Agent tool — no API key) takes one pass over the 150 tweets and proposes 3 free-form tags per tweet, grounded in the example tags from your original message (`relationships`, `humour`, `practical-philosophy`, `culture`, `community`, `productivity`, `twitter-meta`). These are **suggestions to react to**, not a fixed vocabulary — the human labeller can accept, reject, or replace them. Reduces blank-page friction; speeds up human labeller's pass.

**Format for labels — CSV** with columns:

```
tweet_id, source_file, full_text, has_media, suggested_tags, your_tags, notes
```

- `suggested_tags`: Haiku's free-form proposals.
- `your_tags`: semicolon-separated, free-form. Free to ignore the suggestions entirely.
- `notes`: optional; reasoning behind labels, or for disagreeing with Haiku's proposals.

**Flag for user input:** None — proceed once plan is approved.

---

### Phase 2 — Taxonomy consolidation

**Goal:** Convert 150 free-form labels into a fixed taxonomy.

**Method:** Single Claude conversation (Claude Code, no subagents needed). Input: the labelled CSV. Pay attention to the `notes` column, which contains the user's reasoning behind label choices. Output: `taxonomy.md` containing

- A flat list of ≤100 tags.
- For each tag: a **canonical slug** (lowercase-hyphenated, e.g. `practical-philosophy`) plus a **display name** (e.g. "Practical philosophy"). Slug is what gets stored in JSON and used in classifier prompts; display name is what the frontend renders. Consolidate to British English spelling (`humour` not `humor`).
- One-sentence definition per tag.
- 2-3 canonical example tweets per tag, drawn from the seed set.
- An explicit "when unsure" rubric: tie-breakers, max-tags-per-tweet rule (**≤4, all applicable** — *not* best-fit; if two tags genuinely apply, assign both), and a reserved `unknown` slug.

**Flag for user input:** Review and edit `taxonomy.md` before Phase 3. This is the single highest-leverage human step in the pipeline — every auto-label downstream inherits its quality. Also review it against old-taxonomy.md.

---

### Phase 3 — Evalation

Run Phase 4 auto-labelling and Phase 5 media handling on the 150-tweet manually-labelled sample. Cross-check against the user's labels, report every mismatch with your hypothesis for why it occurred and how to fix it. Output to CSV, including `tweet_url` for each row.

Also print to text file the exact prompt sent to each Haiku agent.

Expect multiple iterations here.

---

### Phase 4 — Auto-labelling

**Goal:** Tag the remaining ~10,550 unique primaries.

**Method:** Claude Code with Haiku 4.5 subagents (cheaper, fast, sufficient for classification against a fixed taxonomy). User has no API key—spawn these via subagent tool, not via SDK. Batched calls:

- Group tweets into batches that are small enough to keep per-tweet attention, large enough to amortise the taxonomy in the prompt.
- **Important:** Some tweets require context to interpret correctly — replies need their parent tweet(s), quote-tweets need the quoted tweet. Include this context in each batch object, clearly distinguishing it from the main tweet. It's already rendered on the frontend, so should be accessible to you.
- Each subagent receives: the full taxonomy file and one batch.
- Returns JSON: `[{tweet_id, tags: [...], confidence: "high"|"med"|"low", proposed_new_tag?: string}]` — slugs only in `tags`, drawn from the taxonomy's canonical slug list.

**Prompt structure** (key elements, full version drafted in Phase 4 execution):

- System: role = "tweet classifier", strict output schema, must pick from taxonomy or set `confidence: "low"`.
- Taxonomy block (cached effectively via prompt prefix consistency).
- Examples block: 1–2 worked examples spanning common tags. Include reasoning in the working.
- Input: batch of `{full_text, reply_context, quoted_tweet, has_media, media_alt_if_any}` — `tweet_id` and `username` are stripped before sending to the model and rejoined in `auto_label.py` after.
- Rules:
  - **Multi-tag semantics: AND, not best-fit.** Assign every tag that genuinely applies (up to 4). Don't pick only the most salient one. But don't hesitate to only assign one tag if it's the only clear fit.
  - If no tag fits → `unknown` + `confidence: low` + optional `proposed_new_tag`.
  - `proposed_new_tag` format: lowercase-hyphenated slug, **max 3 words**, must name a *theme* (e.g. `travel`), not a meta-comment (`needs-context`, `unclear`, `too-personal` are invalid).

**Execution order:** `auto_label.py` **explicitly deduplicates** by `tweet_id` across all three input files before batching. (The three input files contain 15,000 tweets in total, but there are only ~10,700 unique tweets). Results are written to a single `site/data/tags.json` keyed by `tweet_id`, persisting `{username, tags, confidence, media_dependent, proposed_new_tag?, source: "text"|"vision"}` per record. Storing `confidence` and `media_dependent` in the file (not just transient state) is what enables Phase 5 to selectively re-run vision on the right subset, and Phase 6 review to filter on confidence.

**Flag for user input:** Pilot only. I'll run a 100-tweet pilot batch, show you the output, then proceed with the rest after you green-light it.

---

### Phase 5 — Media handling

Vision pass over the `media_dependent + confidence in {low, medium}` bucket. Covers everything — images and videos. For videos, use **only the thumbnail** (the `poster` URL already in the `media` field), never the full video. Same prompt as Phase 4 plus the image; same output schema. Goal: every primary tweet ends up with at least one tag.

This keeps Phase 4 cheap (no vision cost on the majority of the ~10,700 primaries — only the `media_dependent + low-confidence` subset gets the vision pass) while guaranteeing complete coverage.

---

### Phase 6 — Review, refinement, schema

**Review surfaces** (one Python script, `scripts/review_tags.py`):

1. All `confidence in {low, medium}` tweets, grouped by tweet (CSV for spot-checking).
2. All `proposed_new_tag` suggestions, grouped and counted.
3. Per-tag samples (10 random tweets per tag) so you can sanity-check that each tag is internally coherent.

**Iteration loop:** If review surfaces enough drift, expand taxonomy and re-label only the affected subset (low-confidence + tweets currently holding a tag whose definition changed).

**Schema change:** Add to each tweet record (primary tweets only — context tweets stay untagged):

```json
"tags": ["humour", "relationships"]
```

Empty array if `unknown` . Existing fields untouched. Both `_row_to_record` in `build.py` and `_extract_external_record` need a no-op default (`tags: []`) so the contract stays symmetric per CLAUDE.md.

A new build step reads `site/data/tags.json` and merges `tags` into each per-metric file. Idempotent — safe to re-run.

**Frontend change** (separate, after data lands): tag chip filter row below the year selector, multi-select with AND semantics, persisted to URL hash so tagged views are shareable. Bump `?v=N` on `app.js` and `style.css` per the CLAUDE.md cache-busting rule.

---

## Critical files

- `build.py` — add `tags: []` default in `_row_to_record` and `_extract_external_record`; add a merge stage that reads `site/data/tags.json`.
- `site/data/tags.json` — **new**, single source of truth keyed by `tweet_id`.
- `site/data/taxonomy.md` — **new**, human-readable taxonomy doc (also input to the system prompt input for Phase 4).
- `scripts/sample_seed.py` — **new**, stratified sampler for Phase 1.
- `scripts/auto_label.py` — **new**, drives Phase 3 batched subagent calls.
- `scripts/review_tags.py` — **new**, surfaces review CSVs for Phase 5.
- `site/js/app.js` — tag filter UI (Phase 6, frontend, separate task).
- `site/css/style.css` — chip styling.
- `site/index.html` — version bump.

## Verification

- After Phase 4 pilot: read `tags.json` for the pilot 100, spot-check 20 manually.
- After Phase 6 merge: run `python build.py --no-media` and confirm each `top_*.json` primary record has a `tags` field; `jq '[.[] | select(.is_context==false) | .tags | length] | add'` should be > 0.
- After frontend change: load `python3 -m http.server`, click a tag, confirm filtered count matches the JSON.
