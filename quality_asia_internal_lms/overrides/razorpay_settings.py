import frappe
from frappe import _
from frappe.integrations.utils import create_request_log, make_post_request
from payments.payment_gateways.doctype.razorpay_settings.razorpay_settings import (
	RazorpaySettings as _RazorpaySettings,
)


class RazorpaySettings(_RazorpaySettings):
	def create_order(self, **kwargs):
		kwargs["amount"] = int(round(float(kwargs["amount"]) * 100))

		integration_request = create_request_log(kwargs, service_name="Razorpay")

		payment_options = {
			"amount": kwargs.get("amount"),
			"currency": kwargs.get("currency", "INR"),
			"receipt": kwargs.get("receipt"),
			"payment_capture": kwargs.get("payment_capture"),
		}
		if self.api_key and self.api_secret:
			try:
				order = make_post_request(
					"https://api.razorpay.com/v1/orders",
					auth=(
						self.api_key,
						self.get_password(fieldname="api_secret", raise_exception=False),
					),
					data=payment_options,
				)
				order["integration_request"] = integration_request.name
				return order
			except Exception:
				frappe.log(frappe.get_traceback())
				frappe.throw(_("Could not create razorpay order"))
