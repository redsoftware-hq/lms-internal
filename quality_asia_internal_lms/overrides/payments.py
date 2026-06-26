"""Force India as the billing country during checkout.

The browser supplies `country` to both the order-summary (display) and the
payment-link (charge) endpoints, and that value gates the 18% GST in
`lms.lms.utils.apply_gst`. A tampered request with `country != "India"` would
therefore skip GST — a real tax/revenue leak, since the frontend dropdown can
be bypassed entirely (devtools / curl).

Quality Asia sells to India only, so we enforce `country = "India"` on the
SERVER for both endpoints, ignoring whatever the client sends. This guarantees
INR + 18% GST on what is actually charged, and keeps the displayed summary
consistent with the charge. App-owned + upgrade-safe (registered via
`override_whitelisted_methods` in hooks.py), like the Razorpay override.
"""

import frappe

from lms.lms.payments import get_payment_link as _get_payment_link
from lms.lms.utils import get_order_summary as _get_order_summary

FORCED_COUNTRY = "India"


@frappe.whitelist()
def get_payment_link(
	doctype: str,
	docname: str,
	address: dict,
	payment_for_certificate: int,
	coupon_code: str | None = None,
	country: str | None = None,
):
	"""Charge path — enforce India so GST cannot be skipped by client input."""
	return _get_payment_link(
		doctype,
		docname,
		address,
		payment_for_certificate,
		coupon_code=coupon_code,
		country=FORCED_COUNTRY,
	)


@frappe.whitelist()
def get_order_summary(
	doctype: str, docname: str, coupon: str | None = None, country: str | None = None
):
	"""Display path — keep the shown summary identical to what will be charged."""
	return _get_order_summary(doctype, docname, coupon=coupon, country=FORCED_COUNTRY)
