"""One-time seed of Quality Asia branding/RBAC/courses onto a fresh deployment.

Runs exactly once: Frappe records it in `Patch Log` after success and never runs
it again. So later admin edits (logo, permissions, course content) made through the
UI are NOT overwritten by subsequent `bench migrate` runs.

The actual logic lives in quality_asia_lms.setup.seed (also runnable manually via
`bench --site <site> execute quality_asia_lms.setup.seed.run`).
"""

import frappe

from quality_asia_lms.setup import seed


def execute():
	try:
		seed.run(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="quality_asia_lms seed_initial_data failed")
		raise
