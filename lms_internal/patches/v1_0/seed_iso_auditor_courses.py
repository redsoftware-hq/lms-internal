"""Create / override the ISO Internal Auditor demo training courses.

Ported from the parent quality-asia-lms catalogue, trimmed to three demo
courses for the internal LMS: ISO 9001 (QMS), ISO 14001 (EMS) and ISO 27001
(ISMS). Each course has a Final-Exam lesson holding a graded LMS Quiz (passing
it is the only requirement to earn the certificate) plus an ungraded Feedback
lesson whose quiz collects a short 4-point training-evaluation survey.

Existing LMS Quiz / Question docs are never deleted, so re-runs are safe and
idempotent and later admin edits in the UI are preserved.

Logic lives in lms_internal.setup.seed.run_iso_auditor_courses (also runnable
manually via `bench --site <site> execute
lms_internal.setup.seed.run_iso_auditor_courses`).
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_iso_auditor_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal seed_iso_auditor_courses failed")
		raise
