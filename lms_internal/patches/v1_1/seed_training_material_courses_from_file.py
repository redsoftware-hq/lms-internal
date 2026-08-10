"""Seed the staff Training-Material courses from the uploaded private File.

The v1_0 patch of the same purpose ran before any fixture data existed on the
site, logged "no course data found" and was recorded in Patch Log — Frappe will
never re-run it. This patch repeats the seed now that the data ships as a
private File (setup.seed.TM_FIXTURE_FILE), uploaded in Desk.

Upload the File BEFORE deploying this patch: like every patch it runs once and
is then recorded, so if the File is missing at that moment it will skip and not
retry. Running once is also what protects later admin edits in the UI from
being overwritten.
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run_training_material_courses(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal seed_training_material_courses_from_file failed")
		raise
