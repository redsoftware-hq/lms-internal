"""Seed the staff Training-Material courses — retry of the v1_1 patch.

v1_1 ran on a site where the fixture File had not been uploaded yet, so it
logged "no course data found" and was recorded in Patch Log; Frappe will never
re-run it. This is the same seed under a new name, to run now that the private
File (setup.seed.TM_FIXTURE_FILE) is in place.

Still one-shot: it seeds if the File is there and skips if it is not, and being
recorded means later admin edits in the UI are never overwritten.
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_training_material_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal v1_2 seed_training_material_courses failed")
		raise
