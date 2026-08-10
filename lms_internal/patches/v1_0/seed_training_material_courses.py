"""Create / update the staff Training-Material courses (tm-* slugs).

Seeds the courses built by tools/build_fixtures.py from the readiness tracker's
seed-ready list — each with an intro-video lesson, a graded Final-Exam quiz, and
an ungraded Training-Feedback survey.

Pure upsert: it only touches its own tm-* docs, never deletes or reconciles, so
it cannot affect the ISO seed, other courses, or admin edits made in the UI.

Logic lives in lms_internal.setup.seed.run_training_material_courses (also
runnable manually via `bench --site <site> execute
lms_internal.setup.seed.run_training_material_courses`).
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_training_material_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal seed_training_material_courses failed")
		raise
