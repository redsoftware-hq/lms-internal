"""Back-end employee onboarding for the invite-only internal LMS.

Public sign-up is disabled (LMS Settings.disable_signup = 1), so staff accounts
are created here instead. Each employee gets a Website User with the LMS Student
role and Frappe's standard welcome email — a "set your password" link — so we
never set or handle a password ourselves.

Usage (a few employees inline):
  bench --site <site> execute quality_asia_internal_lms.setup.invite.invite_employees \
    --kwargs "{'rows': [{'email': 'asha@client.com', 'full_name': 'Asha Rao'}]}"

Usage (from a CSV with header `email,full_name`):
  bench --site <site> execute quality_asia_internal_lms.setup.invite.invite_employees \
    --kwargs "{'csv_path': '/path/to/employees.csv'}"

Idempotent: an existing user is left in place (only the LMS Student role is
added if missing) and is never re-sent a welcome email.
"""

import csv

import frappe

ROLE = "LMS Student"


def _split_name(full_name):
	parts = (full_name or "").strip().split(None, 1)
	first = parts[0] if parts else ""
	last = parts[1] if len(parts) > 1 else ""
	return first, last


def _invite_one(email, full_name, send_welcome_email=True):
	email = (email or "").strip().lower()
	if not email:
		return None, "skipped: missing email"

	if frappe.db.exists("User", email):
		doc = frappe.get_doc("User", email)
		if not any(r.role == ROLE for r in doc.roles):
			doc.append("roles", {"role": ROLE})
			doc.flags.ignore_permissions = True
			doc.save()
			return email, "existing user: LMS Student role added"
		return email, "existing user: unchanged"

	first, last = _split_name(full_name)
	doc = frappe.new_doc("User")
	doc.update({
		"email": email,
		"first_name": first or email,
		"last_name": last,
		"user_type": "Website User",
		"send_welcome_email": 1 if send_welcome_email else 0,
	})
	doc.append("roles", {"role": ROLE})
	doc.flags.ignore_permissions = True
	doc.insert()
	return email, ("created + welcome email queued" if send_welcome_email else "created")


def invite_employees(rows=None, csv_path=None, send_welcome_email=True, commit=True):
	"""Create Website Users (LMS Student) for staff and send the welcome/set-password email.

	rows:     list of {"email", "full_name"} dicts.
	csv_path: path to a CSV with header `email,full_name` (merged with rows if both given).
	"""
	rows = list(rows or [])
	if csv_path:
		with open(csv_path, newline="", encoding="utf-8") as f:
			rows.extend(csv.DictReader(f))

	results = []
	for r in rows:
		email = r.get("email")
		full_name = r.get("full_name") or r.get("name") or ""
		try:
			who, status = _invite_one(email, full_name, send_welcome_email)
			results.append((who or email, status))
		except Exception as e:
			frappe.log_error(title="invite_employees failed", message=f"{email}: {e}")
			results.append((email, f"error: {e}"))

	if commit:
		frappe.db.commit()
	for who, status in results:
		print(f"[qa-invite] {who}: {status}")
	return results
