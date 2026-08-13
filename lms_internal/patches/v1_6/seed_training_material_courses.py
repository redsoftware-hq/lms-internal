"""Seed the staff Training-Material courses from the uploaded private File.

Re-issued as v1_6 because v1_5 may already be recorded in Patch Log on the
deployed site -- a recorded patch never re-runs, so a fresh name is the only way
to apply the current bundle. Running twice is harmless: the seed is a pure
upsert over tm-* docs.

This bundle carries the full 2026 set: 12 courses, titles taken from the client's
Google Form filenames, client-verified exams, and the per-course reference PDF
link.

Upload the bundle as a private File (setup.seed.TM_FIXTURE_FILE) BEFORE deploying
this, along with the 12 <slug>-material.pdf files. Like any patch it runs once,
seeding if the File is present and skipping if it is not.
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_training_material_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal v1_6 seed_training_material_courses failed")
		raise
