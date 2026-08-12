"""Seed the staff Training-Material courses from the uploaded private File.

Re-issued under a new name because v1_0 / v1_1 / v1_2 / v1_3 / v1_4 are already
recorded in Patch Log on some sites — Frappe never re-runs a recorded patch, so a
fresh name is the only way to apply an updated fixture bundle.

This round carries the 2026-08-12 client drop: six new courses (Certification
Officer, Auditor Calibration, Marketing, Finance, Lead Implementer, MS
Documentation) plus client-supplied answer keys that also correct and extend the
exams of courses already live.

Upload the current bundle as a private File (setup.seed.TM_FIXTURE_FILE) BEFORE
deploying this: like any patch it runs once, seeding if the File is present and
skipping if it is not. Running once is also what keeps later admin edits in the
UI from being overwritten.
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_training_material_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal v1_5 seed_training_material_courses failed")
		raise
