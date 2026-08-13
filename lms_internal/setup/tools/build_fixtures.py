#!/usr/bin/env python3
"""
build_fixtures.py — generate seed fixtures for READY Training-Material courses.

Reads (never writes) the build inputs the tracker already validated:
    build/seed_ready.json          which courses are READY
    data/course_manifest.json      titles / categories
    build/youtube_links.json       intro video per course
    build/descriptions.json        short_introduction + description
    build/answer_keys/<id>.json    verified graded questions

Writes ONLY these three NEW, namespaced files (tm- prefix) — it never touches the
*_iso_auditor.json fixtures or any existing course:
    data/courses_training_material.json
    data/quizzes_training_material.json
    data/questions_training_material.json

Each course gets: an intro-video lesson, a graded Final Exam (from the verified
answer key), and a Training Feedback survey (reusing the 5 shared QA-FEEDBACK-*
questions, copied in here so this fixture set is self-contained and idempotent).

Run:
    python lms_internal/setup/tools/build_fixtures.py
"""
from __future__ import annotations

import html
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DATA = REPO_ROOT / "lms_internal" / "setup" / "data"
BUILD = REPO_ROOT / "lms_internal" / "setup" / "build"

INSTRUCTOR = "samarth@qualityasia.in"
PASSING = 70
MARKS_PER_Q = 2
CARD = "Red"
FEEDBACK_QS = ["QA-FEEDBACK-EFFECTIVENESS", "QA-FEEDBACK-INSTRUCTOR",
               "QA-FEEDBACK-STRUCTURE", "QA-FEEDBACK-SATISFACTION", "QA-FEEDBACK-MATERIAL"]


def _load(p, default=None):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def _wrap(text):
    return f'<div class="ql-editor read-mode"><p>{html.escape(text, quote=False)}</p></div>'


def _quiz_block(quiz_name, block_id):
    return json.dumps({"time": 0, "blocks": [{"id": block_id, "type": "quiz",
                       "data": {"quiz": quiz_name}}], "version": "2.29.0"})


def _lesson(name, title, chapter, course, *, content="", body="", youtube=None):
    return {"name": name, "title": title, "include_in_preview": 0, "is_scorm_package": 0,
            "chapter": chapter, "course": course, "content": content, "body": body,
            "youtube": youtube, "quiz_id": None, "question": None, "file_type": "",
            "doctype": "Course Lesson"}


def _chapter(name, title, course, course_title, lesson_name):
    return {"chapter": {"name": name, "title": title, "course": course,
                        "course_title": course_title, "is_scorm_package": 0,
                        "doctype": "Course Chapter", "lessons": [{"idx": 1, "lesson": lesson_name}]},
            "lessons": []}  # lesson doc appended by caller


def _question_doc(name, text, options, correct):
    doc = {"name": name, "question": _wrap(text), "type": "Choices", "multiple": 0}
    for i in range(1, 5):
        opt = options[i - 1] if i - 1 < len(options) else None
        doc[f"option_{i}"] = opt
        doc[f"is_correct_{i}"] = 1 if (opt is not None and opt == correct) else 0
        doc[f"explanation_{i}"] = None
    for i in range(1, 5):
        doc[f"possibility_{i}"] = None
    doc["doctype"] = "LMS Question"
    return doc


def _quiz_doc(name, title, lesson, course, question_rows, total_marks, *,
              passing=PASSING, is_feedback=False):
    return {"name": name, "title": title, "max_attempts": 1 if is_feedback else 0,
            "show_answers": 0, "show_submission_history": 0, "total_marks": total_marks,
            "passing_percentage": passing, "duration": None, "shuffle_questions": 0,
            "limit_questions_to": 0, "enable_negative_marking": 0, "marks_to_cut": 1,
            "lesson": lesson, "course": course, "doctype": "LMS Quiz", "questions": question_rows}


def main():
    ready = _load(BUILD / "seed_ready.json", [])
    if not ready:
        print("No READY courses in seed_ready.json — run course_tracker.py first.")
        return
    manifest = _load(DATA / "course_manifest.json")
    by_id = {c["id"]: c for c in manifest["courses"] if not c["id"].startswith("_")}
    youtube = _load(BUILD / "youtube_links.json", {})
    descriptions = _load(BUILD / "descriptions.json", {})
    iso_qs = _load(DATA / "questions_iso_auditor.json", [])
    shared_fb = [q for q in iso_qs if q["name"] in FEEDBACK_QS]

    out_courses, out_quizzes, out_questions = [], [], list(shared_fb)  # start with shared feedback qs

    for cid in ready:
        meta = by_id[cid]
        title = meta["title"]
        slug = f"tm-{cid}"
        desc = descriptions.get(cid, {})
        short_intro = desc.get("short_introduction", title) if isinstance(desc, dict) else title
        description = desc.get("description", "") if isinstance(desc, dict) else str(desc)
        intro_vid = (youtube.get(cid) or {}).get("intro") or ""
        course_title = title
        ak = _load(BUILD / "answer_keys" / f"{cid}.json", {})
        # Only questions with >=2 options are seedable (Choices require >=2).
        all_qs = ak.get("questions", [])
        exam_qs = [q for q in all_qs if len(q.get("options", [])) >= 2]
        dropped = len(all_qs) - len(exam_qs)

        # chapter/lesson/quiz names
        v_ch, v_ls = f"{slug}-video", f"{slug}-video-lesson"
        e_ch, e_ls = f"{slug}-exam", f"{slug}-exam-lesson"
        f_ch, f_ls = f"{slug}-feedback", f"{slug}-feedback-lesson"
        e_quiz, f_quiz = f"quiz-{slug}", f"quiz-{slug}-feedback"

        # --- exam questions + rows ---
        q_rows = []
        for i, q in enumerate(exam_qs, 1):
            qname = f"TM-{cid.upper().replace('-', '_')}-Q{i:02d}"
            out_questions.append(_question_doc(qname, q["question"], q["options"], q["correct"]))
            q_rows.append({"idx": i, "question": qname, "marks": MARKS_PER_Q,
                           "question_detail": q["question"][:140], "type": "Choices"})
        total_marks = len(q_rows) * MARKS_PER_Q

        out_quizzes.append(_quiz_doc(e_quiz, f"{title} Final Exam", e_ls, slug, q_rows, total_marks))
        fb_rows = [{"idx": i, "question": n, "marks": 0, "question_detail": "", "type": "Choices"}
                   for i, n in enumerate(FEEDBACK_QS, 1)]
        # titles now end in "Training" (they follow the client's form names), so append
        # only "Feedback" to avoid "... Training Training Feedback"
        fb_title = f"{title} Feedback" if title.endswith("Training") else f"{title} Training Feedback"
        out_quizzes.append(_quiz_doc(f_quiz, fb_title, f_ls, slug, fb_rows, 0,
                                     passing=0, is_feedback=True))

        # --- chapters (with lesson docs) ---
        chapters = []
        c1 = _chapter(v_ch, "Course Video", slug, course_title, v_ls)
        c1["lessons"] = [_lesson(v_ls, f"{title} — Training Video", v_ch, slug,
                                 youtube=intro_vid, body="<p>Watch the full training video below.</p>")]
        c2 = _chapter(e_ch, "Final Exam", slug, course_title, e_ls)
        c2["lessons"] = [_lesson(e_ls, f"{title} Final Exam", e_ch, slug,
                                 content=_quiz_block(e_quiz, f"exam{cid}"))]
        c3 = _chapter(f_ch, "Training Feedback", slug, course_title, f_ls)
        c3["lessons"] = [_lesson(f_ls, "Training Feedback", f_ch, slug,
                                 content=_quiz_block(f_quiz, f"fb{cid}"))]
        chapters = [c1, c2, c3]

        course = {
            "name": slug, "title": title, "video_link": intro_vid, "tags": "",
            "status": "Approved", "image": "", "card_gradient": CARD, "published": 1,
            "published_on": "2026-07-15", "upcoming": 0, "featured": 0,
            "disable_self_learning": 0, "short_introduction": short_intro,
            "description": description, "paid_course": 0, "paid_certificate": 0,
            "enable_certification": 1, "course_price": 0, "currency": "INR",
            "amount_usd": 0, "evaluator": None, "timezone": None, "rating": 0.0,
            "notification_sent": 0, "doctype": "LMS Course",
            "category": meta.get("category"),
            "chapters": [{"idx": i, "chapter": ch["chapter"]["name"]} for i, ch in enumerate(chapters, 1)],
            "instructors": [{"idx": 1, "instructor": INSTRUCTOR}],
        }
        out_courses.append({"course": course, "chapters": chapters})
        drop_note = f"  (dropped {dropped} <2-opt)" if dropped else ""
        print(f"  built {cid:26s} slug={slug}  exam={len(q_rows)}Q{drop_note}  video={'y' if intro_vid else 'MISSING'}")

    (DATA / "courses_training_material.json").write_text(json.dumps(out_courses, indent=2, ensure_ascii=False) + "\n")
    (DATA / "quizzes_training_material.json").write_text(json.dumps(out_quizzes, indent=2, ensure_ascii=False) + "\n")
    (DATA / "questions_training_material.json").write_text(json.dumps(out_questions, indent=2, ensure_ascii=False) + "\n")
    print(f"\nWrote {len(out_courses)} courses, {len(out_quizzes)} quizzes, "
          f"{len(out_questions)} questions ({len(shared_fb)} shared feedback) to data/*_training_material.json")


if __name__ == "__main__":
    main()
