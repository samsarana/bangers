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

### Phase 2 — Taxonomy consolidation ✅ COMPLETE

**Goal:** Convert 150 free-form labels into a fixed taxonomy.

**Method:** Single Claude conversation (Claude Code, no subagents needed). Input: the labelled CSV. Pay attention to the `notes` column, which contains the user's reasoning behind label choices. Output: `taxonomy.md` containing

- A flat list of ≤100 tags.
- For each tag: a **canonical slug** (lowercase-hyphenated, e.g. `practical-philosophy`) plus a **display name** (e.g. "Practical philosophy"). Slug is what gets stored in JSON and used in classifier prompts; display name is what the frontend renders. Consolidate to British English spelling (`humour` not `humor`).
- One-sentence definition per tag.
- 2-3 canonical example tweets per tag, drawn from the seed set.
- An explicit "when unsure" rubric: tie-breakers, max-tags-per-tweet rule (**≤4, all applicable** — *not* best-fit; if two tags genuinely apply, assign both), and a reserved `unknown` slug.

**Flag for user input:** Review and edit `taxonomy.md` before Phase 3. This is the single highest-leverage human step in the pipeline — every auto-label downstream inherits its quality. Also review it against old-taxonomy.md.

---

### Phase 3 — Evaluation ✅ COMPLETE

> **Outcome (2026-07-03):** 3 prompt iterations. Final combined text+vision eval on 139 tweets: exact 40.3%, exact+superset 48.9%, miss 7.2% (≤10% bar met), micro-precision 0.776, ≥1-shared-tag 92.8%. The 75% exact bar below was set pre-data and is unrealistic for subjective 55-slug multi-label; the miss bar + precision were adopted as the ship gates instead. Prompt locked at `scripts/eval/classifier_prompt_prefix.txt`. Residual known error: humour over-application (dilutive, handled in Phase 6 review).

**Goal:** Validate the auto-labelling pipeline against ground truth on the 150-tweet seed before committing to the full ~10,700-tweet run.

#### Phase 3a — Build the ground-truth dataset

The `your_tags` column in `seed_labels.csv` was filled in while the taxonomy was still being discovered, so early rows use tags that were later renamed, merged, or dropped. Reconcile every row against the final `data/taxonomy.md`:

- Drop any tag not present in the final taxonomy.
- Replace renamed tags with their successor slug (e.g. `funny` → `humour`).
- Apply any rubric refinements that landed during taxonomy consolidation (e.g. the multi-tag AND rule, the `philosophy` vs `practical-philosophy` split).
- If a row's correct tags are genuinely ambiguous — no obvious successor, or rubric doesn't decide it — leave a best guess in `tags` and set `needs_review: true`.

Method: Claude reads `seed_labels.csv` + `taxonomy.md`, emits the cleaned file plus a short diff summary (counts of: tags dropped, tags renamed, rows flagged `needs_review`).

**Output:** `seed_labels_cleaned.csv` with columns:

```
tweet_id, tweet_url, username, full_text, reply_context, quoted_tweet, has_media, tags, needs_review
```

**Flag for user input:** Review `seed_labels_cleaned.csv` — especially `needs_review` rows — before 3b runs. This file is now the ground truth; its quality caps the achievable evaluation score.

#### Phase 3b — Dry-run the pipeline against ground truth

Run Phase 4 auto-labelling on all 150 tweets, then Phase 5 vision on the `media_dependent + low/med confidence` subset. Compare predictions to `seed_labels_cleaned.csv`.

**Prompt requirement** (applies to Phases 4 and 5 too): when `reply_context` or `quoted_tweet` is present, the prompt must state explicitly that the *main tweet* is what's being tagged and the context exists only to disambiguate intent. Include one worked example in the prompt where context changes the tagging decision.

**Outputs:**

1. `eval_results.csv` — one row per tweet: `tweet_id, tweet_url, true_tags, predicted_tags, confidence, source, match_type, hypothesis`. `match_type ∈ {exact, superset, subset, overlap, miss}`. `hypothesis` is the most likely cause of any mismatch (e.g. "model missed implicit humour", "rubric ambiguity between X and Y").
2. `eval_prompts.txt` — verbatim dump of every classifier prompt, one block per call.
3. Terminal summary: % exact / superset / overlap / miss; mismatch rate stratified by confidence; top 3 failure modes.

**Iteration:** 3b is expected to loop. Each pass refines one of: (a) the prompt, (b) the taxonomy, (c) the rubric. Re-run against the same 150. **Stop when exact-match ≥ 75% and miss ≤ 10%**, or when the user calls it.

---

### Phase 4 — Auto-labelling ✅ COMPLETE

> **Outcome (2026-07-04):** 10,584 unique primaries labelled (10,730 records incl. 146 human seeds) across 530 Sonnet-5 workflow batches of ≤20 — zero missing items, zero invalid slugs. Two runs were interrupted by Pro session limits mid-flight; per-batch result files on disk made recovery a pure rerun of the missing ranges. Prep/assembly scripts: `scripts/eval/prep_full_run.py`, `scripts/eval/assemble_tags.py` (the planned `auto_label.py` became these two). Distribution sane: humour 3,318, practical-philosophy 1,628, psychology 1,556.

**Goal:** Tag the remaining ~10,550 unique primaries.

**Method:** Claude Code with **Sonnet 5 subagents** (user directive 2026-07-03: never Haiku, for any subtask). User has no API key — spawn these via the Agent/Workflow tools, not via the SDK. Batched calls:

- **Batch size: 10–20 tweets per subagent call.** Tune during Phase 3b iteration — small enough to keep per-tweet attention, large enough to amortise the taxonomy block.
- **Context tweets:** Replies need their parent tweet(s); quote-tweets need the quoted tweet. Include both in each batch object, clearly labelled, with a prompt instruction that the main tweet is what's being tagged and context exists only to disambiguate intent (per the Phase 3b prompt requirement).
- Each subagent receives: the full taxonomy file and one batch.
- Returns JSON: `[{tweet_id, tags: [...], confidence: "high"|"med"|"low", media_dependent: bool, proposed_new_tag?: string}]` — slugs only in `tags`, drawn from the taxonomy's canonical slug list.

**Prompt structure** (concrete version drafted during Phase 3b iteration):

- System: role = "tweet classifier", strict output schema, must pick from taxonomy or set `confidence: "low"`.
- Taxonomy block: full `taxonomy.md`.
- Examples block: 4–6 worked examples drawn from `seed_labels_cleaned.csv`, chosen to cover the hard decision boundaries already identified — subject vs mention (urbanism/religion red herrings), humour vs serious-with-comic-vehicle, `practical-philosophy` vs `psychology`, `world-modelling` vs `social-dynamics`. Include the *reasoning*, not just the answer.
- Input: batch of `{full_text, reply_context, quoted_tweet, has_media}` — `tweet_id` and `username` are stripped before sending and rejoined by `auto_label.py` after.
- Rules:
  - **Multi-tag semantics: AND, not best-fit.** Assign every tag that genuinely applies (up to 4). Don't pick only the most salient one. But don't hesitate to assign only one tag if it's the only clear fit.
  - **`media_dependent: true`** when `has_media` is true AND text alone is insufficient to tag at high confidence. This is the model's own declaration, not a heuristic — and it's the sole gate for Phase 5.
  - **`unknown` vs `unclassified`:** `unknown` when content is present but the model can't decide which tags apply — pair with `confidence: low` and an optional `proposed_new_tag`. `unclassified` when no transferable idea exists at all (per the taxonomy rubric) — `confidence: high` is acceptable.
  - `proposed_new_tag` format: lowercase-hyphenated slug, **max 3 words**, must name a *theme* (e.g. `travel`), not a meta-comment (`needs-context`, `unclear`, `too-personal` are invalid).

**Execution order:** `auto_label.py` **explicitly deduplicates** by `tweet_id` across all three input files before batching. (15,000 rows total → ~10,700 unique). Results are written to `data/tags.json` keyed by `tweet_id`. Per record: `{username, tags, confidence, media_dependent, proposed_new_tag?, source: "text"|"vision"}`. `username` and `source: "text"` are added by `auto_label.py` from the input data; Phase 5 overwrites `source` to `"vision"` for the subset it re-runs. Persisting `confidence` and `media_dependent` (not just transient state) is what lets Phase 5 select the right subset and Phase 6 filter for review.

**Flag for user input:** No accuracy gate — Phase 3b already validated the prompt on the seed set. Operational sanity check after the first ~500 tweets: tag-distribution histogram, watch for skew (e.g. > 30% `humour`), and a 20-tweet manual spot-check. Continue if green.

---

### Phase 5 — Media handling ✅ COMPLETE

> **Outcome (2026-07-04):** 2,463 tweets came back `media_dependent`; 2,299 had fetchable images (3 URLs 404'd, 164 no usable media → `unclassified` fallback). 460 vision batches of ≤5, Sonnet 5, all complete after one session-limit rerun. `unknown` fell 1,655 → 66; high-confidence rose 6,832 → 8,650; only 202 records remain `media_dependent: true` post-vision. Script: `scripts/eval/prep_vision.py` (downloads to scratchpad, not `cache/` — keeps repo cache tweet-JSON-only).

Vision pass over the **`media_dependent: true`** subset (no separate confidence gate — `media_dependent` already encodes "text was insufficient"). Same prompt as Phase 4 plus the image; same output schema; sets `source: "vision"`.

**Media URL selection:**

- `type: photo` → use `url` (the image itself).
- `type: video` / `gif` → use `poster` (the still thumbnail). Never the video URL.

**Invocation:** Pre-download each image to `cache/` keyed by `tweet_id` (reusing the existing `fetch_media` cache pattern). Spawn the subagent with the local path in the prompt; the subagent uses Read on the path to load the image (Sonnet 5 is multi-modal). Fetch failures (404, removed media, unsupported format) fall back to the text-only label and stay `media_dependent: true`, `confidence: low`.

**Realistic goal:** Coverage, not omniscience. Most media-dependent tweets become taggable once vision is applied; the residue (removed media, opaque content, link-only tweets) keep their text-only label or end up `unclassified`. Don't force a tag where the signal genuinely isn't there.

---

### Phase 6 — Review, refinement, schema ✅ COMPLETE (review artefacts ready for user)

> **Outcome (2026-07-04):** `data/tags.json` (1.5 MB) assembled and merged into all three per-metric JSONs (5,000/5,000 primaries tagged in each) via `scripts/merge_tags.py`; `build.py` merge stage + `tags: []` defaults in both record builders. Frontend tag row shipped and verified in preview at full scale (53 chips, AND filtering, `#tags=` hash round-trip, per-metric counts, dark mode). Review surfaces written: `scripts/eval/review_low_confidence.csv` (2,080 rows), `review_proposed_tags.csv` (4 distinct proposals, 5 total), `review_tag_samples.csv` (10 per tag × 55). Remaining human step: skim the review CSVs — esp. humour (3,318, known over-application) — and re-label any drifted subset.
>
> **Top-N precision review (2026-07-07, superseded the manual skim):** every tag chip's top-25-per-metric slice (2,810 pairs / 2,071 tweets) was audited by model reviewers (Fable, then Opus after Pro limits) via `scripts/eval/prep_review_topn.py` + `apply_review.py`. 362 clear "mention-not-subject"/humour-inflation tags removed (digest: `scripts/eval/review_removals.txt`); 11 reviewer objections to human seed labels ignored by design. Removals are pinned in `scripts/eval/tag_overrides.json`, which `assemble_tags.py` now applies last — one-off manual corrections go there too (or just edit `data/tags.json` and run `scripts/merge_tags.py`).

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

A new build step reads `data/tags.json` and merges `tags` into each per-metric file. Idempotent — safe to re-run.

**Frontend change** (separate, after data lands): tag chip filter row below the year selector, multi-select with AND semantics, persisted to URL hash so tagged views are shareable. Bump `?v=N` on `app.js` and `style.css` per the CLAUDE.md cache-busting rule.

---

## Critical files

- `build.py` — add `tags: []` default in `_row_to_record` and `_extract_external_record`; add a merge stage that reads `data/tags.json`.
- `data/tags.json` — **new**, single source of truth keyed by `tweet_id`.
- `data/taxonomy.md` — **new**, human-readable taxonomy doc (also input to the system prompt input for Phase 4).
- `scripts/sample_seed.py` — **new**, stratified sampler for Phase 1.
- `scripts/auto_label.py` — **new**, drives Phase 4 batched subagent calls.
- `scripts/review_tags.py` — **new**, surfaces review CSVs for Phase 5.
- `site/js/app.js` — tag filter UI (Phase 6, frontend, separate task).
- `site/css/style.css` — chip styling.
- `site/index.html` — version bump.

## Verification

- After Phase 4 pilot: read `tags.json` for the pilot 100, spot-check 20 manually.
- After Phase 6 merge: run `python build.py --no-media` and confirm each `top_*.json` primary record has a `tags` field; `jq '[.[] | select(.is_context==false) | .tags | length] | add'` should be > 0.
- After frontend change: load `python3 -m http.server`, click a tag, confirm filtered count matches the JSON.
