"""Quality Asia certificate customizations on top of stock LMS Certificate.

  - Every generated certificate is forced onto our print format ("QA Certificate")
    and renders in the Quality Asia School format.
  - Two training dates are auto-filled relative to the issue date and shown on the
    certificate as e.g. "07th, 08th APRIL 2026".

Shipped entirely as code (fixtures + these hooks) so it survives `bench migrate`
and a fresh deploy — no fork of the LMS app.
"""

import base64
import mimetypes

import frappe
from frappe.utils import add_days, getdate

QA_TEMPLATE = "QA Certificate"

# Training runs over two consecutive days; the first day sits 15 days before the
# certificate's issue date (client rule, 2026-06-10). To shift the window, change
# only these two offsets.
TRAINING_START_OFFSET = -15
TRAINING_END_OFFSET = -14


def prepare_certificate(doc, method=None):
	"""before_insert on LMS Certificate: pin our print format and fill the dates."""
	if frappe.db.exists("Print Format", QA_TEMPLATE):
		doc.template = QA_TEMPLATE
	populate_training_dates(doc)


def populate_training_dates(doc):
	"""Auto-fill the two training dates from issue_date, only when blank so a
	manual override is never clobbered."""
	if not doc.issue_date:
		return
	issue = getdate(doc.issue_date)
	if not doc.get("training_start_date"):
		doc.training_start_date = add_days(issue, TRAINING_START_OFFSET)
	if not doc.get("training_end_date"):
		doc.training_end_date = add_days(issue, TRAINING_END_OFFSET)


def enforce_qa_certificate_template():
	"""after_migrate: bring every existing certificate onto the QA format + dates.

	Runs after fixtures are synced (so the print format already exists). Idempotent
	— only touches rows not already on the QA template."""
	if not frappe.db.exists("Print Format", QA_TEMPLATE):
		return
	names = frappe.get_all(
		"LMS Certificate", filters={"template": ["!=", QA_TEMPLATE]}, pluck="name"
	)
	for name in names:
		doc = frappe.get_doc("LMS Certificate", name)
		doc.template = QA_TEMPLATE
		populate_training_dates(doc)
		doc.save(ignore_permissions=True)
	if names:
		frappe.db.commit()


def qa_cert_image(filename):
	"""Return a base64 data URI for a certificate image shipped in the app.

	The print format embeds images inline rather than linking `/assets/...` because
	the PDF engine (wkhtmltopdf) cannot reliably fetch them over the network during
	rendering. Reading the file at print time keeps the images as real, swappable
	files in the repo."""
	path = frappe.get_app_path("quality_asia_lms", "public", "images", "qa-cert", filename)
	try:
		with open(path, "rb") as f:
			data = base64.b64encode(f.read()).decode()
	except OSError:
		frappe.log_error(title=f"QA Certificate: missing image {filename}")
		return ""
	mime = mimetypes.guess_type(filename)[0] or "image/jpeg"
	return f"data:{mime};base64,{data}"


def _ordinal(day):
	suffix = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
	return f"{day:02d}{suffix}"


def format_training_dates(start, end):
	"""Jinja helper for the print format. Renders the two training dates as
	'07th, 08th APRIL 2026', collapsing the month/year when shared and expanding
	them only when the range crosses a boundary."""
	if not start or not end:
		return ""
	start, end = getdate(start), getdate(end)
	if (start.year, start.month) == (end.year, end.month):
		return f"{_ordinal(start.day)}, {_ordinal(end.day)} {start.strftime('%B').upper()} {start.year}"
	if start.year == end.year:
		return (
			f"{_ordinal(start.day)} {start.strftime('%B').upper()}, "
			f"{_ordinal(end.day)} {end.strftime('%B').upper()} {end.year}"
		)
	return (
		f"{_ordinal(start.day)} {start.strftime('%B').upper()} {start.year}, "
		f"{_ordinal(end.day)} {end.strftime('%B').upper()} {end.year}"
	)
