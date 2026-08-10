#!/usr/bin/env python3
"""
course_tracker.py — readiness gate for Training-Material -> LMS course seeding.

Single source of truth is setup/data/course_manifest.json. For every candidate
course this script resolves each required condition against what actually exists
on disk / in the build inputs, then classifies the course:

    READY     include=true AND every required condition is met  -> seed-eligible
    PENDING   include=true but one or more required conditions unmet (blockers listed)
    EXCLUDED  include=false (a doubt we have deliberately parked; reason shown)

It prints a dashboard and writes setup/build/seed_ready.json (the READY ids). The
seeder consumes only that list, so nothing half-built can leak into a seed run.

Condition resolution
--------------------
  content        all deck files (>=1) exist under decks_dir; empty decks = unmet
  graded_quiz    build/answer_keys/<id>.json exists AND "verified": true
                 (the extractor emits it with verified=false until you confirm
                  every low-confidence answer, then flip the flag)
  feedback_quiz  the quiz_form xlsx exists (feedback questions come from it)
  youtube_intro  build/youtube_links.json has an "intro" for <id>
  description    build/descriptions.json has a non-empty entry for <id>
  category       manifest category is non-empty
  thumbnail      optional; met if youtube_intro met or an explicit thumbnail given

Run (standalone, no frappe needed):
    python lms_internal/setup/tools/course_tracker.py
    python lms_internal/setup/tools/course_tracker.py --material-root "/path/to/Training Material"
    python lms_internal/setup/tools/course_tracker.py --json      # machine-readable dump
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "lms_internal" / "setup" / "data"
BUILD_DIR = REPO_ROOT / "lms_internal" / "setup" / "build"
MANIFEST = DATA_DIR / "course_manifest.json"

# Conditions that are optional (do not block READY) unless required=true in manifest.
DEFAULT_OPTIONAL = {"thumbnail"}

# Minimum number of seedable (>=2-option) exam questions for a course to be READY.
MIN_VALID_QUESTIONS = 5


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [WARN] could not read {path.name}: {exc}", file=sys.stderr)
        return default


def _resolve_conditions(course, material_root, decks_dir, forms_dir, youtube, descriptions):
    """Return {cond_name: (met: bool, detail: str)} for each declared condition."""
    cid = course["id"]
    conds = course.get("conditions", {})
    out = {}

    def has_all_decks():
        decks = course.get("decks") or []
        if not decks:
            return False, "no decks listed"
        missing = [d for d in decks if not (material_root / decks_dir / d).exists()]
        if missing:
            return False, f"{len(missing)} deck file(s) missing"
        return True, f"{len(decks)} deck(s)"

    def has_form():
        qf = course.get("quiz_form")
        if not qf:
            return False, "no form"
        return (material_root / forms_dir / qf).exists(), qf[:34]

    def has_answer_key():
        akf = BUILD_DIR / "answer_keys" / f"{cid}.json"
        if not akf.exists():
            return False, "answer key not generated"
        data = _load_json(akf, {})
        if not data.get("verified"):
            n = len(data.get("low_confidence", []))
            return False, f"unverified ({n} low-confidence Q)"
        # Only questions with >=2 options can be seeded (Choices need >=2). Low-
        # response forms can't recover distractors -> too few valid Qs to seed.
        valid = [q for q in data.get("questions", []) if len(q.get("options", [])) >= 2]
        if len(valid) < MIN_VALID_QUESTIONS:
            return False, f"only {len(valid)} valid Q (<{MIN_VALID_QUESTIONS}); need form option lists"
        return True, f"{len(valid)} valid Qs verified"

    for name, spec in conds.items():
        required = spec.get("required", True)
        if name == "content":
            met, detail = has_all_decks()
        elif name == "graded_quiz":
            met, detail = has_answer_key()
        elif name == "feedback_quiz":
            met, detail = has_form()
        elif name == "youtube_intro":
            met = bool(youtube.get(cid, {}).get("intro"))
            detail = "provided" if met else "awaiting link"
        elif name == "description":
            desc = descriptions.get(cid)
            if isinstance(desc, dict):
                met = bool((desc.get("description") or "").strip())
            else:
                met = bool((desc or "").strip())
            detail = "provided" if met else "awaiting text"
        elif name == "category":
            met = bool(course.get("category"))
            detail = course.get("category") or "unset"
        elif name == "thumbnail":
            met = bool(youtube.get(cid, {}).get("intro")) or bool(course.get("thumbnail"))
            detail = "derivable" if met else "awaiting"
        else:
            met, detail = False, "unknown condition"
        out[name] = {"required": required, "met": met, "detail": detail}
    return out


def evaluate(material_root_override=None):
    manifest = _load_json(MANIFEST, None)
    if manifest is None:
        sys.exit(f"ERROR: manifest not found at {MANIFEST}")

    material_root = Path(material_root_override or manifest["material_root"])
    decks_dir = manifest["decks_dir"]
    forms_dir = manifest["forms_dir"]
    youtube = _load_json(BUILD_DIR / "youtube_links.json", {})
    descriptions = _load_json(BUILD_DIR / "descriptions.json", {})

    results = []
    for course in manifest["courses"]:
        if course.get("id", "").startswith("_"):
            continue
        entry = {
            "id": course["id"],
            "title": course["title"],
            "tier": course.get("tier"),
            "category": course.get("category"),
            "include": course.get("include", False),
        }
        if not course.get("include", False):
            entry["status"] = "EXCLUDED"
            entry["reason"] = course.get("exclude_reason", "(no reason given)")
            entry["conditions"] = {}
            entry["blockers"] = []
            results.append(entry)
            continue

        conds = _resolve_conditions(course, material_root, decks_dir, forms_dir, youtube, descriptions)
        blockers = [n for n, c in conds.items() if c["required"] and not c["met"]]
        entry["conditions"] = conds
        entry["blockers"] = blockers
        entry["status"] = "READY" if not blockers else "PENDING"
        results.append(entry)
    return results, material_root


def _print_dashboard(results, material_root):
    order = {"READY": 0, "PENDING": 1, "EXCLUDED": 2}
    results = sorted(results, key=lambda r: (order[r["status"]], r.get("tier") or 9, r["id"]))
    icon = {"READY": "✅", "PENDING": "⏳", "EXCLUDED": "❌"}

    print(f"\nMaterial root: {material_root}")
    print(f"Manifest:      {MANIFEST.relative_to(REPO_ROOT)}")
    print("=" * 78)
    cond_cols = ["content", "graded_quiz", "feedback_quiz", "youtube_intro", "description", "category"]
    for r in results:
        line = f"{icon[r['status']]} [{r['status']:8s}] T{r.get('tier') or '-'}  {r['title']}"
        print("\n" + line)
        if r["status"] == "EXCLUDED":
            print(f"      reason: {r['reason']}")
            continue
        for c in cond_cols:
            info = r["conditions"].get(c)
            if not info:
                continue
            mark = "✔" if info["met"] else ("✘" if info["required"] else "○")
            print(f"      {mark} {c:14s} {info['detail']}")
        if r["blockers"]:
            print(f"      -> blocked on: {', '.join(r['blockers'])}")

    ready = [r for r in results if r["status"] == "READY"]
    pending = [r for r in results if r["status"] == "PENDING"]
    excluded = [r for r in results if r["status"] == "EXCLUDED"]
    print("\n" + "=" * 78)
    print(f"READY: {len(ready)}   PENDING: {len(pending)}   EXCLUDED: {len(excluded)}")
    if ready:
        print("Seed-eligible now: " + ", ".join(r["id"] for r in ready))
    else:
        print("Seed-eligible now: (none yet)")


def main():
    ap = argparse.ArgumentParser(description="Course readiness gate for seeding.")
    ap.add_argument("--material-root", help="Override the material_root from the manifest.")
    ap.add_argument("--json", action="store_true", help="Emit machine-readable JSON instead of the dashboard.")
    args = ap.parse_args()

    results, material_root = evaluate(args.material_root)

    BUILD_DIR.mkdir(parents=True, exist_ok=True)
    ready_ids = [r["id"] for r in results if r["status"] == "READY"]
    (BUILD_DIR / "seed_ready.json").write_text(json.dumps(ready_ids, indent=2) + "\n")

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        _print_dashboard(results, material_root)
        print(f"\nWrote seed-ready ids -> {(BUILD_DIR / 'seed_ready.json').relative_to(REPO_ROOT)}")


if __name__ == "__main__":
    main()
