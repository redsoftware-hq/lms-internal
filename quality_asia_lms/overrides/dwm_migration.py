import csv
import re

import frappe

TEMPLATE = "QA Certificate"
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def setup():
	from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

	create_custom_fields(
		{
			"LMS Certificate": [
				dict(fieldname="training_dates", label="Training Dates", fieldtype="Data", insert_after="expiry_date"),
				dict(
					fieldname="candidate_name_as_printed",
					label="Candidate Name (as printed)",
					fieldtype="Data",
					insert_after="member_name",
					read_only=1,
				),
			]
		}
	)
	frappe.db.commit()


def _course(program, cache={}):
	if program not in cache:
		name = frappe.db.get_value("LMS Course", {"title": program})
		if not name:
			doc = frappe.get_doc(
				{
					"doctype": "LMS Course",
					"title": program,
					"short_introduction": f"{program} Internal Auditor Training",
					"description": program,
					"published": 1,
				}
			)
			doc.flags.ignore_permissions = True
			doc.flags.ignore_mandatory = True
			name = doc.insert().name
		cache[program] = name
	return cache[program]


def _clean_mobile(raw):
	if not raw:
		return None
	digits = re.sub(r"[^\d+]", "", raw.strip())
	# keep leading + for international; strip if nothing else useful
	digits = re.sub(r"^\++", "+", digits)
	pure = digits.lstrip("+")
	return digits if 7 <= len(pure) <= 15 else None


def _is_valid_email(addr):
	try:
		from frappe.utils import validate_email_address
		validate_email_address(addr, throw=True)
		return True
	except Exception:
		return False


def _user(name, email, mobile, placeholder_log, cache={}):
	email = (email or "").strip().lower()
	clean_mobile = _clean_mobile(mobile)
	if not EMAIL_RE.match(email) or not _is_valid_email(email):
		suffix = re.sub(r"\D", "", mobile or "")[-4:] or "0000"
		local = frappe.scrub(name).replace("_", ".")
		local = re.sub(r"\.{2,}", ".", local).strip(".")  # remove consecutive/leading/trailing dots
		email = f"{local or 'candidate'}.{suffix}@placeholder.qualityasia.in"
		placeholder_log.append((name, mobile, email))
	if email not in cache:
		if not frappe.db.exists("User", email):
			parts = (name or "").strip().split(" ", 1)
			# skip mobile if it's already taken by another user (unique index on mobile_no)
			if clean_mobile and frappe.db.exists("User", {"mobile_no": clean_mobile}):
				clean_mobile = None
			frappe.get_doc(
				{
					"doctype": "User",
					"email": email,
					"first_name": parts[0] or "Candidate",
					"last_name": parts[1] if len(parts) > 1 else "",
					"mobile_no": clean_mobile,
					"user_type": "Website User",
					"send_welcome_email": 0,
					"roles": [{"role": "LMS Student"}],
				}
			).insert(ignore_permissions=True)
		cache[email] = True
	return email


def run(path, template=None):
	template = template or TEMPLATE
	placeholder_log = []
	# bypass user-creation throttle, queue size check, and other import-unfriendly validations
	frappe.flags.in_import = True
	frappe.flags.in_install = True  # makes User.on_update run create_contact synchronously (bypasses queue size check)
	with open(path) as f:
		rows = list(csv.DictReader(f, delimiter="\t"))

	created = skipped = failed = 0
	for row in rows:
		old_id = row["name"]
		if frappe.db.exists("LMS Certificate", old_id):
			skipped += 1
			continue
		try:
			member = _user(row["candidate_name"], row.get("email_id"), row.get("contact_number"), placeholder_log)
			course = _course(row["training_program_name"])

			# Enrollment must exist before inserting the certificate (LMS validates it)
			enrollment_name = frappe.db.get_value("LMS Enrollment", {"member": member, "course": course})
			if not enrollment_name:
				enrollment = frappe.get_doc(
					{
						"doctype": "LMS Enrollment",
						"member": member,
						"course": course,
						"progress": 100,
					}
				)
				enrollment.flags.ignore_permissions = True
				enrollment.flags.ignore_mandatory = True
				enrollment.insert()
				enrollment_name = enrollment.name

			cert = frappe.get_doc(
				{
					"doctype": "LMS Certificate",
					"member": member,
					"course": course,
					"issue_date": row["date_of_issue"],
					"template": template,
					"published": 1,
					"training_dates": row.get("training_dates"),
					"candidate_name_as_printed": row["candidate_name"],
				}
			)
			cert.flags.ignore_permissions = True
			cert.flags.ignore_validate = True  # bypass duplicate-cert-per-course check; historical data may have multiple
			cert.insert(set_name=old_id)

			frappe.db.set_value(
				"LMS Certificate",
				old_id,
				{"creation": row["creation"], "modified": row["modified"]},
				update_modified=False,
			)

			# Link the certificate back to the enrollment
			frappe.db.set_value("LMS Enrollment", enrollment_name, "certificate", old_id, update_modified=False)

			created += 1
			if created % 500 == 0:
				frappe.db.commit()
				print(created, "done")
		except Exception:
			frappe.log_error(title=f"Cert migration failed: {old_id}")
			failed += 1

	frappe.db.commit()
	if placeholder_log:
		with open("/tmp/placeholder_users.csv", "w") as f:
			csv.writer(f).writerows([("candidate_name", "mobile", "placeholder_email")] + placeholder_log)
	print(f"created={created} skipped={skipped} failed={failed} placeholders={len(placeholder_log)}")


def validate():
	certs = frappe.db.count("LMS Certificate")
	courses = frappe.db.count("LMS Course")
	students = frappe.db.count("User", {"user_type": "Website User"})
	orphans = frappe.db.sql("""
		SELECT c.name FROM `tabLMS Certificate` c
		LEFT JOIN `tabLMS Enrollment` e
		  ON e.member = c.member AND e.course = c.course
		WHERE e.name IS NULL AND c.course IS NOT NULL
	""")
	unpublished = frappe.db.count("LMS Certificate", {"published": 0})
	print(
		f"certificates={certs} courses={courses} website_users={students} "
		f"orphan_certs={len(orphans)} unpublished={unpublished}"
	)
	if orphans:
		print("ORPHANS:", [o[0] for o in orphans][:20])
