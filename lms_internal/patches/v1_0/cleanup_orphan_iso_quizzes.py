"""Delete LMS Quiz rows whose linked course no longer exists.

This site was originally migrated from the full parent quality-asia-lms
catalogue (10 ISO courses). The internal LMS only seeds three demo courses
(ISO 9001 / 14001 / 27001), so the quizzes of the dropped courses (ISO 13485 /
22000 / 26000 / 27701 / 42001 / 45001 / 50001) linger as orphans pointing at
courses that were never seeded here.

Delete only quizzes whose `course` is set AND that course does not exist — a
quiz with no course, or one belonging to a real course, is never touched.
Idempotent: a fresh deploy (which never had the dropped courses) is a no-op.
"""

import frappe


def execute():
	orphans = []
	for q in frappe.get_all("LMS Quiz", fields=["name", "course"]):
		course = q.get("course")
		if course and not frappe.db.exists("LMS Course", course):
			orphans.append(q["name"])

	for name in orphans:
		frappe.delete_doc("LMS Quiz", name, force=True, ignore_permissions=True)

	frappe.db.commit()
	print(f"[lms_internal] cleanup_orphan_iso_quizzes: deleted {len(orphans)} orphan quiz(zes): {orphans}")
