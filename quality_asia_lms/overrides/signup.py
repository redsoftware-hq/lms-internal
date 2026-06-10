"""Custom self-signup for the Quality Asia portal.

Frappe's /login#signup page renders the template returned by the
`signup_form_template` hook (it uses the last app's value). Because this app
loads after `lms`, `get_signup_template` below overrides the stock/LMS signup
form with no fork of either app.

The form collects Name, Email, mandatory Mobile Number, and optional Address;
`sign_up` mirrors `lms.lms.user.sign_up` (roles, verification email, country
from IP) and additionally stores mobile_no (standard) and address (custom field).
"""

import re

import frappe
from frappe import _
from frappe.utils import cint, escape_html, random_string
from frappe.website.utils import is_signup_disabled

ALLOWED_MOBILE_CHARS = re.compile(r"^[+0-9\s\-]+$")


def get_signup_template():
	"""`signup_form_template` hook → our signup form."""
	return "quality_asia_lms/templates/signup-form.html"


def _validate_mobile(mobile_no):
	"""Lenient phone check: only +, digits, spaces, hyphens, 7-15 digits total.
	Accepts Indian and international numbers; rejects junk and empty."""
	if not mobile_no:
		frappe.throw(_("Mobile Number is required"))
	if not ALLOWED_MOBILE_CHARS.match(mobile_no):
		frappe.throw(_("Please enter a valid mobile number"))
	digits = re.sub(r"\D", "", mobile_no)
	if not (7 <= len(digits) <= 15):
		frappe.throw(_("Please enter a valid mobile number"))


@frappe.whitelist(allow_guest=True)  # nosemgrep: frappe-semgrep-rules.rules.security.guest-whitelisted-method
def sign_up(email: str, full_name: str, mobile_no: str, address: str = ""):
	if is_signup_disabled():
		frappe.throw(_("Sign Up is disabled"), _("Not Allowed"))

	email = (email or "").strip()
	full_name = (full_name or "").strip()
	mobile_no = (mobile_no or "").strip()
	address = (address or "").strip()

	if not full_name or not email:
		frappe.throw(_("Name and email are required"))
	_validate_mobile(mobile_no)

	user = frappe.db.get("User", {"email": email})
	if user:
		if user.enabled:
			return 0, _("Already Registered")
		return 0, _("Registered but disabled")

	max_signups = cint(frappe.get_system_settings("max_signups_allowed_per_hour") or 300)
	if frappe.db.get_creation_count("User", 60) >= max_signups:
		frappe.respond_as_web_page(
			_("Temporarily Disabled"),
			_(
				"Too many users signed up recently, so the registration is disabled. Please try back in an hour"
			),
			http_status_code=429,
		)

	user = frappe.get_doc(
		{
			"doctype": "User",
			"email": email,
			"first_name": escape_html(full_name),
			"mobile_no": mobile_no,
			"address": address,
			"country": "",
			"enabled": 1,
			"new_password": random_string(10),
			"user_type": "Website User",
		}
	)
	user.flags.ignore_permissions = True
	user.flags.ignore_password_policy = True
	user.insert()

	# Same role assignment as the stock LMS signup.
	default_role = frappe.db.get_single_value("Portal Settings", "default_role")
	if default_role:
		user.add_roles(default_role)
	user.add_roles("LMS Student")

	# Best-effort country from IP, like LMS — never block signup if it fails.
	try:
		from lms.lms.user import set_country_from_ip

		set_country_from_ip(None, user.name)
	except Exception:
		frappe.clear_last_message()

	if user.flags.email_sent:
		return 1, _("Please check your email for verification")
	return 2, _("Please ask your administrator to verify your sign-up")
