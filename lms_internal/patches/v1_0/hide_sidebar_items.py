"""Hide Batches, Certifications, Jobs, Statistics from the LMS sidebar.

LMS Settings has built-in toggle fields for these sidebar items. Setting them
to 0 hides the corresponding sidebar links in the Vue SPA for all users —
irrelevant clutter for an internal staff-training LMS.
"""

import frappe


def execute():
	for field in ("batches", "certifications", "jobs", "statistics"):
		frappe.db.set_single_value("LMS Settings", field, 0)
