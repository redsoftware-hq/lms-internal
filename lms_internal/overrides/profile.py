"""Backend for the extra profile field (mobile number) that we add to the LMS
portal's Edit Profile modal via injected JS (QA-15).

This runs server-side in our app, so it's robust and deploys cleanly on Frappe
Cloud; only the modal UI that calls it is injected into the SPA. Each method is
scoped to the *logged-in* user — a website user can only read/write their own
profile.

The internal LMS does not collect job-applicant data (company / residential
address / resume), so only the native ``mobile_no`` field is exposed here.
"""

import re

import frappe
from frappe import _

EXTRA_FIELDS = ("mobile_no",)

# Lenient mobile rule (7–15 digits; +, spaces and hyphens are allowed and ignored).
_MOBILE_RE = re.compile(r"\D")


def _validate_mobile(value):
	if not value:
		return
	digits = _MOBILE_RE.sub("", value)
	if not (7 <= len(digits) <= 15):
		frappe.throw(_("Please enter a valid mobile number."))


def _require_user():
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in to edit your profile."), frappe.PermissionError)
	return user


@frappe.whitelist()
def get_profile_extras():
	"""Current values, to pre-fill the injected modal fields. Includes the email
	(read-only in the UI — it's the login id and isn't editable here)."""
	return frappe.db.get_value("User", _require_user(), ("email",) + EXTRA_FIELDS, as_dict=True) or {}


@frappe.whitelist()
def update_profile_extras(mobile_no=None):
	"""Save the profile fields for the logged-in user.

	Only the fields passed (non-None) are touched, so the injected UI can save
	independently of the stock modal's own save. Mobile, when provided, is
	validated with a lenient rule.
	"""
	user = _require_user()
	values = {}

	if mobile_no is not None:
		mobile_no = mobile_no.strip()
		_validate_mobile(mobile_no)
		values["mobile_no"] = mobile_no

	if values:
		frappe.db.set_value("User", user, values)
	return values
