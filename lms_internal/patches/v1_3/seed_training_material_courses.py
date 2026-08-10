"""Seed the staff Training-Material courses from the uploaded private File.

Re-issued under a new name because the earlier patches (v1_0 / v1_1 / v1_2) are
already recorded in Patch Log on some sites — Frappe never re-runs a recorded
patch, so a fresh name is the only way to apply updated fixture data.

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
		frappe.log_error(title="lms_internal v1_3 seed_training_material_courses failed")
		raise
