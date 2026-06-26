"""Create / override the 10 ISO Internal Auditor training courses.

Generated from the client's content sheet (titles, intros, descriptions,
training video + reference-PDF links, 70% pass). Nine courses are free; ISO
42001 is paid (Rs. 1000). Each course has a single Final-Exam lesson holding an
LMS Quiz — passing that quiz is the only requirement to earn the certificate.

Quizzes are seeded as empty stubs where the client has not yet supplied
questions; a later re-run fills them in place (idempotent). Runs once via the
Patch Log, so later admin edits in the UI are preserved.

Logic lives in quality_asia_internal_lms.setup.seed.run_iso_auditor_courses (also
runnable manually via `bench --site <site> execute
quality_asia_internal_lms.setup.seed.run_iso_auditor_courses`).
"""

import frappe

from quality_asia_internal_lms.setup import seed


def execute():
	try:
		seed.run_iso_auditor_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="quality_asia_internal_lms seed_iso_auditor_courses failed")
		raise
