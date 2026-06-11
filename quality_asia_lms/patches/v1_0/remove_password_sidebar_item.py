"""One-time removal of the "Change Password" LMS sidebar item (QA-15 cleanup).

QA-17 originally added a "Change Password" entry to the LMS portal sidebar via an
`after_migrate` hook. QA-15 moved password change into the Edit Profile modal, so
the sidebar entry is now a duplicate. The hook is gone, but the item it already
wrote into LMS Settings persists in every environment's DB — this patch removes it.

Self-contained (does not import the deleted overrides.portal) and idempotent:
runs once per site, recorded in Patch Log, and a no-op if the item is absent.
"""

import frappe

PASSWORD_RESET_ROUTE = "update-password"


def execute():
	if not frappe.db.exists("DocType", "LMS Settings"):
		return
	settings = frappe.get_single("LMS Settings")
	rows = [r for r in settings.sidebar_items if (r.route or "").strip("/") == PASSWORD_RESET_ROUTE]
	if not rows:
		return
	for row in rows:
		settings.sidebar_items.remove(row)
	settings.flags.ignore_permissions = True
	settings.flags.ignore_mandatory = True
	settings.save(ignore_permissions=True)
