"""Phase 3b step 1: build classifier prompts for the seed-set eval run.

Reads seed_labels_cleaned.csv + taxonomy.md, emits:
  - scripts/eval/classifier_prompt_prefix.txt  (shared prefix, reused in Phase 4)
  - <scratch>/eval/prompts/batch_NN.txt        (one full prompt per batch)
  - <scratch>/eval/idmap.json                  ((batch, index) -> tweet_id)
  - scripts/eval/eval_prompts.txt              (verbatim dump of every prompt)

The 6 worked-example tweets are excluded from the eval batches (their labels
appear in the prompt, so scoring them would be leakage).
"""
import csv
import json
import re
import sys
from pathlib import Path

ROOT = Path("/Users/sam/Developer/Book of Bangers (Opus)")
SCRATCH = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/eval")
PROMPT_DIR = SCRATCH / "eval" / "prompts"
PROMPT_DIR.mkdir(parents=True, exist_ok=True)
(SCRATCH / "eval" / "results").mkdir(parents=True, exist_ok=True)

BATCH_SIZE = 14

# Tweets used as worked examples inside the prompt — excluded from scoring.
EXAMPLE_IDS = {
    "1540716423139426305",  # computers/cars-cities — subject vs mention
    "1938046721373655066",  # jogging humidity — humour primary, not advice
    "2036952566672875955",  # farm $26M — substance primary, humour secondary
    "1951438215438827642",  # jogging 3 years + quoted dating tweet — context changes tags
    "1394772091660951555",  # joking shapes reality — psychology + practical-philosophy
    "2004978122853417358",  # baby announcement — unclassified
    "1185299145504018432",  # Airbnb Math — humour + economics (under-tagging guard)
}

taxonomy = (ROOT / "data/taxonomy.md").read_text()
slugs = re.findall(r"^### (.+)$", taxonomy, re.M)

RULES = f"""## Valid tag slugs (use EXACTLY these strings)

{", ".join(slugs)}

## How to read each item

Each ITEM in the batch has:
- TWEET: the main tweet — this is the ONLY thing you are tagging.
- REPLY CONTEXT (optional): ancestor tweet(s) this tweet replies to, oldest first, separated by `---`.
- QUOTED TWEET (optional): the tweet the main tweet quotes.
- HAS_MEDIA: yes/no — whether the tweet has attached images/video. You cannot see the media itself.

Context tweets exist ONLY to help you interpret the main tweet's intent. Tag the
main tweet's contribution — including themes in the context that the main tweet
directly engages with — but never tag themes that live solely in the context.

## Rules

1. **AND, not best-fit.** Assign every tag that genuinely applies, up to 4
   thematic tags (TIL / announcement / unclassified are administrative and do
   not count toward the 4). One tag is fine when only one fits — but
   **under-tagging is the single most common failure mode**. A typical banger
   carries 2–3 tags. Before finalising each item, re-scan the slug list and ask
   "does any OTHER tag genuinely apply?" — secondary themes that are genuinely
   present get tagged even when one theme dominates. A joke about a rigged
   system gets the system's domain tag too; an insight told through a personal
   story gets the insight's domain, not just the story's.
2. **Subject, not mention.** Tag what the tweet is ABOUT, not what it name-drops.
   A tweet using a city analogy to make a tech point is not `urbanism`; a joke
   built around a Buddhist term is not `religion` unless religion is the subject.
3. **Humour, precisely.** Tag `humour` whenever the tweet is built to make the
   reader laugh or smile — punchline structure, absurd juxtaposition, comic
   anecdote — even when substantive tags also apply (then tag both). Do NOT tag
   `humour` merely because the tone is casual or irreverent ("lol", emoji,
   internet voice) while the payload is a serious observation.
4. **media_dependent: true** when HAS_MEDIA is yes AND the text alone leaves you
   unable to tag at high confidence. This flags the tweet for a later vision pass.
5. **unknown vs unclassified.** `unknown` = content exists but you cannot tell
   which tags apply (always confidence "low", usually media_dependent).
   `unclassified` = there is genuinely no transferable idea (pure personal
   update, removed media with empty text) — high confidence is fine.
   **Media takes precedence:** if HAS_MEDIA is yes and the text alone is
   insufficient (however short — "gm", "oh", a bare link), the payload is
   almost certainly in the media you cannot see → `unknown`, confidence "low",
   media_dependent true. NEVER conclude `unclassified` for a media tweet from
   its text alone; that verdict belongs to the vision pass.
   **Link-only tweets (HAS_MEDIA: no):** if the payload sits behind an external
   link and the visible text carries no transferable idea of its own →
   `unclassified`, NOT `unknown` (site readers cannot see behind the link
   either).
   **Reaction posts:** pure hype or reaction ("angels sing", "let's go",
   wordless enthusiasm about a product/event) with no transferable idea beyond
   the enthusiasm itself → `unclassified`, even when the subject is
   identifiable. Do not tag the subject's domain.
6. **proposed_new_tag** (optional): only when no taxonomy tag fits but a clear
   theme exists. Lowercase-hyphenated, max 3 words, must name a THEME
   (`travel`), never a meta-comment (`needs-context`, `unclear` are invalid).
7. Every tweet tagged `LLMs` must also be tagged `AI`.
8. Follow the taxonomy's tie-breakers ("When unsure" section) exactly.
9. Use ONLY slugs from the list above in `tags` — exact strings, case-sensitive.
10. **Tag-specific notes.**
   - `psychology` applies whenever the tweet claims something about internal
     mental mechanisms — motivation, self-concept, emotion, attention — however
     informally phrased. Pop-psychological observations count.
   - `technology` is the broad-tech tag: do NOT add it when the tweet is
     specifically covered by `software-development`, `cybersecurity`, `AI`, or
     `LLMs`.
   - `twitter-meta` vs `internet-culture` quick test: is the subject the
     experience of tweeting/reading tweets/accounts/blocking/this platform's
     discourse? → `twitter-meta`. Online phenomena beyond this platform
     (memes, fandom, forum culture) → `internet-culture`.
   - The three most UNDER-applied tags are `epistemics`, `healing-and-growth`,
     and `psychology`. When a tweet's point is about HOW to reason, notice, or
     update (not just what to believe), add `epistemics`. When a personal story
     shows a developmental shift — something worked through, a changed
     self-understanding — add `healing-and-growth`. Informal claims about
     internal mental mechanisms still earn `psychology`.
   - `humour` doubt tie-break: if you cannot tell whether the author intends
     amusement or is simply writing casually, do NOT tag humour.

## Worked examples

EXAMPLE 1
HAS_MEDIA: no
TWEET: I wonder if 50 years from now we're going to look back at how we've redesigned our world around computers with the same regret that people look back at how we redesigned cities around cars. 🤔
Reasoning: The subject is technological change and civilisation-scale regret. The cars/cities comparison is a rhetorical analogy, not the subject — so NOT `urbanism` (rule 2). Macro claim about how the world got reshaped → `world-modelling`; about technology broadly → `technology`.
→ tags: ["technology", "world-modelling"], confidence: "high", media_dependent: false

EXAMPLE 2
HAS_MEDIA: no
TWEET: my advice is if you decide to go on a run for the first time in half a decade or more, don't do it in 94% humidity
Reasoning: Framed as advice, but it is a self-deprecating joke about a mishap — there is no transferable principle. Humour is the primary register; NOT `practical-philosophy`.
→ tags: ["humour"], confidence: "high", media_dependent: false

EXAMPLE 3
HAS_MEDIA: no
TWEET: if someone offered me $26M for my farm but I wanted to keep farming I would take the money and buy a bigger farm
Reasoning: Mildly funny, but the payload is a genuine heuristic about resources serving goals — the humour is not the main point, so no `humour` (rule 3). Prescriptive reframe → `practical-philosophy`; reasoning about money/assets → `economics`.
→ tags: ["practical-philosophy", "economics"], confidence: "high", media_dependent: false

EXAMPLE 4
HAS_MEDIA: no
TWEET: The old joke was that jogging would add three years to your life.  But those three years would be spent jogging.
QUOTED TWEET: @[user]: dating these "don't die" guys is insufferable. he won't have a glass of wine with you, says 9pm is too "late" to go to ur friend's party. sure he might live forever but not with me
Reasoning: The main tweet is a joke, and it directly engages the quoted complaint about dating longevity-obsessed men — the quote is what the joke comments on. So the context legitimately contributes `relationships`. The joke also carries a real point about trading life-quality for longevity → `practical-philosophy`.
→ tags: ["humour", "practical-philosophy", "relationships"], confidence: "high", media_dependent: false

EXAMPLE 5
HAS_MEDIA: no
TWEET: the stuff you joke about (even ironically or whatever) has a way of shaping your reality so be careful and deliberate with that stuff. a lot of people out here fumbling their own bags by joking about outcomes they don't want. you might as well joke about the outcomes you do want
Reasoning: Describes a psychological mechanism (jokes shaping self-narrative) AND prescribes behaviour. Per the taxonomy tie-breaker, when a psychological insight becomes explicitly actionable, apply both.
→ tags: ["practical-philosophy", "psychology"], confidence: "high", media_dependent: false

EXAMPLE 6
HAS_MEDIA: yes
TWEET: beautiful baby girl born on dec 25 (which was also my 29th birthday!) 🎄🤍 https://t.co/eOO9Z9YNlc
Reasoning: A pure personal announcement — shares a moment, conveys no transferable idea. That is exactly `unclassified`. The text is sufficient to determine this; seeing the photo would not change it, so media_dependent stays false.
→ tags: ["unclassified"], confidence: "high", media_dependent: false

EXAMPLE 7
HAS_MEDIA: yes
TWEET: this is incredible https://t.co/xxxxxxx
Reasoning: The entire payload is in media I cannot see. Content exists but tags are undeterminable from text → `unknown`, confidence "low", and media_dependent true so the vision pass picks it up.
→ tags: ["unknown"], confidence: "low", media_dependent: true

EXAMPLE 8
HAS_MEDIA: no
TWEET: Airbnb Math:

$40/night x 2 nights = $164
Reasoning: A punchline-structured joke → `humour`. But the joke's subject is pricing and hidden fees — a genuinely economic observation — so `economics` applies too (rule 1: a joke about a system gets the system's domain tag). Stopping at `humour` alone would be the classic under-tagging failure.
→ tags: ["humour", "economics"], confidence: "high", media_dependent: false
"""

PREFIX = f"""You are a tweet classifier for "Book of Bangers", a curated anthology of the
best tweets from the TPOT Twitter community. Assign thematic tags from the fixed
taxonomy below to each tweet in the batch at the end of this document.

# Taxonomy

{taxonomy}

{RULES}
"""


def render_item(i, r):
    parts = [f"ITEM {i}", f"HAS_MEDIA: {r['has_media']}"]
    parts.append(f"TWEET: {r['full_text']}")
    if r["reply_context"]:
        parts.append(f"REPLY CONTEXT (ancestors, oldest first):\n{r['reply_context']}")
    if r["quoted_tweet"]:
        parts.append(f"QUOTED TWEET: {r['quoted_tweet']}")
    return "\n".join(parts)


def build_batches(rows, batch_size=BATCH_SIZE):
    batches = []
    for b in range(0, len(rows), batch_size):
        batches.append(rows[b : b + batch_size])
    return batches


def batch_prompt(batch_rows, result_path):
    items = "\n\n".join(render_item(i, r) for i, r in enumerate(batch_rows))
    return f"""{PREFIX}

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

{items}
"""


def main():
    rows = list(csv.DictReader(open(ROOT / "scripts/eval/seed_labels_cleaned.csv")))
    eval_rows = [r for r in rows if r["tweet_id"] not in EXAMPLE_IDS]
    print(f"Seed rows: {len(rows)}; eval rows after excluding {len(EXAMPLE_IDS)} examples: {len(eval_rows)}")

    batches = build_batches(eval_rows)
    idmap = {}
    dump_blocks = []
    for bi, batch in enumerate(batches):
        result_path = SCRATCH / "eval" / "results" / f"batch_{bi:02d}.json"
        prompt = batch_prompt(batch, result_path)
        (PROMPT_DIR / f"batch_{bi:02d}.txt").write_text(prompt)
        for i, r in enumerate(batch):
            idmap[f"{bi}:{i}"] = r["tweet_id"]
        dump_blocks.append(f"{'='*70}\n=== BATCH {bi:02d} ===\n{'='*70}\n\n{prompt}")

    (SCRATCH / "eval" / "idmap.json").write_text(json.dumps(idmap, indent=1))
    (ROOT / "scripts/eval/classifier_prompt_prefix.txt").write_text(PREFIX)
    (ROOT / "scripts/eval/eval_prompts.txt").write_text("\n\n".join(dump_blocks))

    print(f"Batches: {len(batches)} x <= {BATCH_SIZE}")
    print(f"Prompt files in: {PROMPT_DIR}")
    print(f"Prefix chars: {len(PREFIX):,} (~{len(PREFIX)//4:,} tokens)")
    print(f"Valid slugs: {len(slugs)}")


if __name__ == "__main__":
    main()
