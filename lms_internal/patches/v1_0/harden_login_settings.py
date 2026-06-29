"""Login hardening — safe System Settings defaults for the internal LMS.

Tightens password policy, login lockout, and session expiry, and removes the
"Login with Email Link" button (login_with_email_link=0, which also covers the
old simplify_login concern). The "Login with Frappe Cloud" button is a runtime
Frappe Cloud condition that can't be toggled here — hide it via brand.css if needed.

Idempotent — safe to re-run. (The parent's DWM migrated-user reset logic is
intentionally omitted: the internal LMS has no bulk-migrated accounts.)
"""

import frappe

SETTINGS = {
	"enable_password_policy": 1,
	"minimum_password_score": "2",
	"allow_consecutive_login_attempts": 5,
	"allow_login_after_fail": 300,
	"password_reset_limit": 3,
	"session_expiry": "24:00",
	"logout_on_password_reset": 1,
	"login_with_email_link": 0,
}


def execute():
	for key, value in SETTINGS.items():
		frappe.db.set_single_value("System Settings", key, value)
