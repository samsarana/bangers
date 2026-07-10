"""Phase 3b scoring: compare batch predictions against ground truth.

Usage: python3 scripts/eval/score_eval.py <scratch_eval_dir> [--out eval_results.csv]

Reads <scratch>/results/batch_*.json + <scratch>/idmap.json + seed_labels_cleaned.csv.
Writes scripts/eval/eval_results.csv and prints the summary.
"""
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/Users/sam/Developer/Book of Bangers (Opus)")

# Known rubric boundaries, used to auto-draft mismatch hypotheses.
CONFUSION_PAIRS = [
    ({"practical-philosophy", "philosophy"}, "philosophy vs practical-philosophy boundary (abstract vs behavioural)"),
    ({"psychology", "practical-philosophy"}, "psychology-describes vs practical-philosophy-prescribes boundary"),
    ({"world-modelling", "social-dynamics"}, "macro world-modelling vs interpersonal social-dynamics scale"),
    ({"epistemics", "public-epistemics"}, "personal vs societal epistemics"),
    ({"politics", "policy-and-governance"}, "partisan politics vs institutional policy"),
    ({"twitter-meta", "internet-culture"}, "platform-specific vs broad internet culture"),
    ({"culture", "internet-culture"}, "real-world vs online culture"),
    ({"unknown", "unclassified"}, "unknown vs unclassified administrative distinction"),
    ({"AI", "LLMs"}, "AI container vs LLMs specificity"),
    ({"technology", "software-development"}, "tech-broad vs software-specific"),
    ({"labour", "career"}, "worker-experience vs individual-trajectory"),
]


def match_type(true_set, pred_set):
    if pred_set == true_set:
        return "exact"
    inter = true_set & pred_set
    if not inter:
        return "miss"
    if true_set < pred_set:
        return "superset"
    if pred_set < true_set:
        return "subset"
    return "overlap"


def hypothesis(true_set, pred_set, mt, confidence, media_dep, has_media):
    if mt == "exact":
        return ""
    missing = true_set - pred_set
    extra = pred_set - true_set
    notes = []
    if has_media == "yes" and (media_dep or "unknown" in pred_set):
        notes.append("media-dependent: text alone under-determines the tweet")
    involved = missing | extra
    for pair, desc in CONFUSION_PAIRS:
        if pair & missing and pair & extra:
            notes.append(desc)
    if "humour" in extra:
        notes.append("model over-applied humour (comic surface, serious payload)")
    if "humour" in missing:
        notes.append("model missed humour as primary register")
    if not notes:
        if missing and not extra:
            notes.append(f"under-tagging: missed {', '.join(sorted(missing))}")
        elif extra and not missing:
            notes.append(f"over-tagging: added {', '.join(sorted(extra))}")
        else:
            notes.append(
                f"substituted {', '.join(sorted(missing))} with {', '.join(sorted(extra))}"
            )
    return "; ".join(notes)


def main():
    scratch = Path(sys.argv[1])
    idmap = json.loads((scratch / "idmap.json").read_text())
    truth = {
        r["tweet_id"]: r
        for r in csv.DictReader(open(ROOT / "scripts/eval/seed_labels_cleaned.csv"))
    }
    slugs = set(re.findall(r"^### (.+)$", (ROOT / "data/taxonomy.md").read_text(), re.M))

    preds = {}
    problems = []
    for f in sorted(scratch.glob("results/batch_*.json")):
        bi = int(f.stem.split("_")[1])
        try:
            arr = json.loads(f.read_text())
        except json.JSONDecodeError as e:
            problems.append(f"{f.name}: JSON parse error {e}")
            continue
        for p in arr:
            tid = idmap.get(f"{bi}:{p['index']}")
            if tid is None:
                problems.append(f"{f.name}: index {p['index']} has no idmap entry")
                continue
            bad = [t for t in p["tags"] if t not in slugs]
            if bad:
                problems.append(f"{tid}: invalid slugs {bad}")
            preds[tid] = p

    # Vision overlay, if the vision pass has run
    vmap_path = scratch / "vision_idmap.json"
    if vmap_path.exists():
        vmap = json.loads(vmap_path.read_text())
        for f in sorted(scratch.glob("vision_results/batch_*.json")):
            bi = int(f.stem.split("_")[1])
            try:
                arr = json.loads(f.read_text())
            except json.JSONDecodeError as e:
                problems.append(f"vision {f.name}: JSON parse error {e}")
                continue
            for p in arr:
                tid = vmap.get(f"{bi}:{p['index']}")
                if tid is None:
                    continue
                bad = [t for t in p["tags"] if t not in slugs]
                if bad:
                    problems.append(f"vision {tid}: invalid slugs {bad}")
                p["source"] = "vision"
                preds[tid] = p

    rows_out = []
    mt_counts = Counter()
    mt_by_conf = defaultdict(Counter)
    tag_tp = Counter()
    tag_fp = Counter()
    tag_fn = Counter()
    media_dep_ids = []

    for tid, t in truth.items():
        if tid not in preds:
            continue
        p = preds[tid]
        true_set = set(x for x in t["tags"].split(";") if x)
        pred_set = set(p["tags"])
        mt = match_type(true_set, pred_set)
        mt_counts[mt] += 1
        mt_by_conf[p["confidence"]][mt] += 1
        for tag in true_set & pred_set:
            tag_tp[tag] += 1
        for tag in pred_set - true_set:
            tag_fp[tag] += 1
        for tag in true_set - pred_set:
            tag_fn[tag] += 1
        if p.get("media_dependent"):
            media_dep_ids.append(tid)
        rows_out.append(
            {
                "tweet_id": tid,
                "tweet_url": t["tweet_url"],
                "true_tags": ";".join(sorted(true_set)),
                "predicted_tags": ";".join(sorted(pred_set)),
                "confidence": p["confidence"],
                "source": p.get("source", "text"),
                "match_type": mt,
                "hypothesis": hypothesis(
                    true_set, pred_set, mt, p["confidence"],
                    p.get("media_dependent"), t["has_media"],
                ),
                "proposed_new_tag": p.get("proposed_new_tag", ""),
            }
        )

    out = ROOT / "scripts/eval" / (sys.argv[sys.argv.index("--out") + 1] if "--out" in sys.argv else "eval_results.csv")
    with open(out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    n = len(rows_out)
    print(f"=== Phase 3b scoring ({n} tweets) ===")
    for mt in ["exact", "superset", "subset", "overlap", "miss"]:
        c = mt_counts[mt]
        print(f"  {mt:9s} {c:4d}  ({c/n*100:5.1f}%)")
    good = mt_counts["exact"] + mt_counts["superset"]
    print(f"  exact+superset: {good/n*100:.1f}%   miss: {mt_counts['miss']/n*100:.1f}%")
    print()
    print("--- by confidence ---")
    for conf in ["high", "med", "low"]:
        row = mt_by_conf[conf]
        tot = sum(row.values())
        if not tot:
            continue
        mism = tot - row["exact"] - row["superset"]
        print(f"  {conf:4s}: n={tot:3d}  exact={row['exact']:3d}  ex+sup={row['exact']+row['superset']:3d}  problematic={mism:3d} ({mism/tot*100:.0f}%)")
    print()
    print("--- worst tags (FN = model missed; FP = model over-applied) ---")
    tags_all = sorted(set(tag_fn) | set(tag_fp), key=lambda t: -(tag_fn[t] + tag_fp[t]))
    for t in tags_all[:15]:
        print(f"  {t:24s} FN={tag_fn[t]:2d}  FP={tag_fp[t]:2d}  TP={tag_tp[t]:2d}")
    print()
    print(f"media_dependent flagged: {len(media_dep_ids)}")
    (Path(scratch) / "media_dependent_ids.json").write_text(json.dumps(media_dep_ids))
    if problems:
        print(f"\n--- problems ({len(problems)}) ---")
        for p in problems[:20]:
            print(f"  {p}")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
