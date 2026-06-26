"""One-time seed of Quality Asia branding / RBAC / files / users onto a fresh deployment.

Runs exactly once: Frappe records it in `Patch Log` after success and never runs
it again. So later admin edits (logo, permissions, accounts) made through the
UI are NOT overwritten by subsequent `bench migrate` runs.

The actual logic lives in lms_internal.setup.seed (also runnable manually via
`bench --site <site> execute lms_internal.setup.seed.run`).
"""

import frappe

from lms_internal.setup import seed


def execute():
	try:
		seed.run(commit=False)  # migrate wraps this in its own transaction
	except Exception:
		frappe.log_error(title="lms_internal seed_initial_data failed")
		raise
