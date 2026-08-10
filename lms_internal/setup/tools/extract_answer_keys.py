#!/usr/bin/env python3
"""
extract_answer_keys.py — answer-key inference for the role-based Training Material.

Adapted from extract_quiz_from_forms.py (which is hardwired to the ISO-folder
layout). This version is MANIFEST-DRIVEN: it walks course_manifest.json, and for
every included course that has a `quiz_form`, it parses that Google-Forms xlsx
export and infers the correct answer per graded (knowledge) question.

Inference (decision C1):
  default  correct = most common answer among high-scorers (Score >= 85% of max),
           confidence = fraction of those high-scorers who agree.
  --strict correct = most common answer among ONLY full-mark (100%) submissions;
           if there are none, the question is left with no key (confidence 0).

Any question below --confidence (default 0.90) is added to "low_confidence" and the
file is written with "verified": false. The tracker treats the course's graded_quiz
condition as UNMET until you review those questions against the live Google Form and
flip "verified" to true (or edit the "correct" values).

Outputs (one per included course with a form):
    setup/build/answer_keys/<course_id>.json

Run:
    python lms_internal/setup/tools/extract_answer_keys.py
    python lms_internal/setup/tools/extract_answer_keys.py --strict
    python lms_internal/setup/tools/extract_answer_keys.py --material-root "/path"
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

try:
    import openpyxl
except ImportError:
    sys.exit("openpyxl required: pip install openpyxl (it is present in the frappe venv)")

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = REPO_ROOT / "lms_internal" / "setup" / "data"
BUILD_DIR = REPO_ROOT / "lms_internal" / "setup" / "build"
MANIFEST = DATA_DIR / "course_manifest.json"

METADATA_KEYWORDS = ["timestamp", "email address", "email", "score", "name", "role", "contact no", "company name"]
SKIP_KEYWORDS = ["resume", "attach", "company profile", "networking"]
# Feedback (ungraded rating) columns — not part of the graded answer key.
FEEDBACK_KEYWORDS = [
    "would you rate the effectiveness", "overall, how would you rate",
    "instructor's knowledge", "suitable amount of time", "delivered in a suitable",
    "overall satisfaction", "quality of training", "comprehensiveness of the training",
    "training material (topics", "how effectively did the training", "recommend",
]

HIGH_SCORE_FRAC = 0.85
CONFIDENCE_FLAG = 0.90


def _col_type(h_lower: str) -> str:
    if not h_lower.strip():
        return "skip"
    if any(k in h_lower for k in METADATA_KEYWORDS):
        return "meta"
    if any(k in h_lower for k in SKIP_KEYWORDS):
        return "skip"
    if any(k in h_lower for k in FEEDBACK_KEYWORDS):
        return "feedback"
    return "exam"


def _read_rows(path: Path):
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows = [list(r) for r in ws.iter_rows(values_only=True)]
    wb.close()
    if not rows:
        return [], []
    header = ["" if c is None else str(c) for c in rows[0]]
    return header, rows[1:]


def _score(row, score_col):
    try:
        return float(row[score_col])
    except (TypeError, ValueError, IndexError):
        return 0.0


def extract_course(form_path: Path, strict: bool, confidence_flag: float):
    header, rows = _read_rows(form_path)
    if not rows:
        return None

    score_col = next(
        (i for i, h in enumerate(header) if "score" == h.strip().lower()),
        next((i for i, h in enumerate(header) if "score" in h.lower()), 2),
    )
    scores = [_score(r, score_col) for r in rows]
    max_score = max(scores) if scores else 0.0

    if strict:
        key_rows = [r for r, s in zip(rows, scores) if max_score and s >= max_score]
    else:
        threshold = HIGH_SCORE_FRAC * max_score if max_score else 0.0
        key_rows = [r for r, s in zip(rows, scores) if s >= threshold]

    total = len(rows)
    questions = []
    for ci, col_header in enumerate(header):
        if _col_type(col_header.strip().lower()) != "exam":
            continue
        all_ans = [str(r[ci]).strip() for r in rows if ci < len(r) and r[ci] not in (None, "")]
        if not all_ans:
            continue
        counts = Counter(all_ans)
        distinct = [o for o, _ in counts.most_common()]
        top4_cov = sum(c for _, c in counts.most_common(4)) / len(all_ans)
        resp_rate = len(all_ans) / total if total else 0.0
        # MCQ heuristic: few distinct values, well-covered, widely answered.
        if len(distinct) > 6 or top4_cov < 0.90 or resp_rate < 0.50:
            continue
        options = distinct[:4]

        key_ans = [str(r[ci]).strip() for r in key_rows if ci < len(r) and r[ci] not in (None, "")]
        if key_ans:
            correct, n = Counter(key_ans).most_common(1)[0]
            confidence = n / len(key_ans)
        else:
            correct, confidence = None, 0.0

        # Canonicalise Google Forms 0/1 boolean encoding.
        if set(options) <= {"0", "1"}:
            options = ["True", "False"]
            correct = {"0": "False", "1": "True"}.get(correct, correct)

        questions.append({
            "question": col_header.strip(),
            "options": options,
            "correct": correct,
            "confidence": round(confidence, 4),
            "n_key_agree": len(key_ans),
        })

    low_conf = [q["question"][:70] for q in questions if q["confidence"] < confidence_flag]
    return {
        "max_score": max_score,
        "num_responses": total,
        "num_key_rows": len(key_rows),
        "questions": questions,
        "low_confidence": low_conf,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--material-root")
    ap.add_argument("--strict", action="store_true", help="Use only full-mark (100%%) submissions as the key.")
    ap.add_argument("--confidence", type=float, default=CONFIDENCE_FLAG)
    ap.add_argument("--only", help="Comma-separated course ids to limit to.")
    args = ap.parse_args()

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    material_root = Path(args.material_root or manifest["material_root"])
    forms_dir = material_root / manifest["forms_dir"]
    only = set(args.only.split(",")) if args.only else None

    out_dir = BUILD_DIR / "answer_keys"
    out_dir.mkdir(parents=True, exist_ok=True)

    mode = "strict full-marks" if args.strict else f"high-scorer consensus (>= {int(HIGH_SCORE_FRAC*100)}%)"
    print(f"Answer-key inference mode: {mode}\n")

    done, flagged = 0, 0
    for course in manifest["courses"]:
        cid = course.get("id", "")
        if cid.startswith("_") or not course.get("include"):
            continue
        if only and cid not in only:
            continue
        qf = course.get("quiz_form")
        if not qf:
            continue
        fpath = forms_dir / qf
        if not fpath.exists():
            print(f"  [WARN] {cid}: form not found -> {qf}")
            continue

        res = extract_course(fpath, args.strict, args.confidence)
        if res is None or not res["questions"]:
            print(f"  [WARN] {cid}: no graded questions detected")
            continue

        payload = {
            "course_id": cid,
            "form": qf,
            "mode": mode,
            "max_score": res["max_score"],
            "num_responses": res["num_responses"],
            "num_key_rows": res["num_key_rows"],
            "verified": False,
            "low_confidence": res["low_confidence"],
            "questions": res["questions"],
        }
        (out_dir / f"{cid}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
        done += 1
        n_low = len(res["low_confidence"])
        flagged += n_low
        flag = f"  ⚠️ {n_low} low-confidence — VERIFY" if n_low else "  (all high-confidence)"
        print(f"  {cid:26s} {len(res['questions'])} Qs  keyrows={res['num_key_rows']}{flag}")

    print(f"\nWrote {done} answer-key file(s) to {out_dir.relative_to(REPO_ROOT)}")
    print(f"{flagged} question(s) need manual verification. After checking each against the")
    print('live Google Form, set "verified": true in that course\'s answer-key file, then')
    print("re-run course_tracker.py to update the gate.")


if __name__ == "__main__":
    main()
