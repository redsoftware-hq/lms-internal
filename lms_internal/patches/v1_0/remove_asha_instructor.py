"""Remove Asha (instructor1@qualityasia.test) from every course's instructors.

The demo seed originally listed Asha as the course instructor; the default
mentor is now Samarth (samarth@qualityasia.in, auto-assigned on new courses and
seeded onto the demo courses). This strips Asha from the ``instructors`` child
table on all LMS Courses, including stock/demo courses the seed doesn't manage.

Idempotent — safe to re-run; a course without Asha is left untouched.
"""

import frappe

OLD_INSTRUCTOR = "instructor1@qualityasia.test"


def execute():
	parents = frappe.get_all(
		"Course Instructor",
		filters={"instructor": OLD_INSTRUCTOR, "parenttype": "LMS Course"},
		pluck="parent",
		distinct=True,
	)
	for course_name in parents:
		doc = frappe.get_doc("LMS Course", course_name)
		kept = [row for row in doc.instructors if row.instructor != OLD_INSTRUCTOR]
		if len(kept) == len(doc.instructors):
			continue
		doc.set("instructors", kept)
		doc.save(ignore_permissions=True)

	if parents:
		frappe.db.commit()
	print(f"[lms_internal] remove_asha_instructor: cleaned {len(parents)} course(s)")
