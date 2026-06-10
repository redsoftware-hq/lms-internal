"""Quality Asia portal (LMS SPA) tweaks done without forking the LMS frontend.

The student portal is the upstream LMS Vue SPA; we avoid editing it. Anything
here drives the SPA through data it already reads (e.g. LMS Settings), so it
survives `bench update lms`.
"""

import frappe

# Frappe's built-in change-password page. Reachable by every logged-in user and
# also handles the "set new password" step of the forgot-password flow.
PASSWORD_RESET_ROUTE = "update-password"


def ensure_password_reset_link():
	"""Add a "Change Password" entry to the LMS portal sidebar pointing at Frappe's
	/update-password page.

	Implemented as an LMS Sidebar Item (config only) so the portal SPA is never
	forked. The SPA navigates by the item's `route`; the doctype's `web_page` link
	plays no part in navigation, so it is left empty (hence ignore_mandatory).
	Idempotent — safe to run on every migrate.
	"""
	settings = frappe.get_single("LMS Settings")
	for row in settings.sidebar_items:
		if (row.route or "").strip("/") == PASSWORD_RESET_ROUTE:
			return
	settings.append(
		"sidebar_items",
		{"title": "Change Password", "route": PASSWORD_RESET_ROUTE, "icon": "KeyRound"},
	)
	settings.flags.ignore_permissions = True
	settings.flags.ignore_mandatory = True  # web_page link is unused for nav
	settings.save(ignore_permissions=True)
	frappe.db.commit()
