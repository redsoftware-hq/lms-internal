"""One-time seed of Quality Asia customizations onto a fresh deployment.

Carries what NO installed app recreates on its own:
  - Files      (logo / favicon / footer)
  - Branding   (Website Settings + LMS Settings runtime values)  -> force-set
  - RBAC       (admin's manual Custom DocPerm changes + Property Setters)
  - Users      (one admin/instructor account)

The internal LMS ships a small demo catalogue of three ISO Internal Auditor
courses (ISO 9001 / 14001 / 27001), each with a graded final-exam quiz and an
ungraded feedback survey. These are seeded from setup/data/*_iso_auditor.json
by run_iso_auditor_courses() (further staff training content is authored
in-app). The full catalogue lives in the parent quality-asia-lms.

Invoked once by the patch `lms_internal.patches.v1_0.seed_initial_data`
(recorded in Patch Log -> never re-runs -> later admin UI edits persist).

Manual re-run / second environment:
  bench --site <site> execute lms_internal.setup.seed.run

Every step is idempotent, so the manual re-run is safe too.
"""

import json
import os
import shutil
from urllib.parse import unquote

import frappe

DATA = frappe.get_app_path("lms_internal", "setup", "data")
FILES = frappe.get_app_path("lms_internal", "setup", "files")


def _load(name):
	path = os.path.join(DATA, name)
	if not os.path.exists(path):
		return None
	with open(path, encoding="utf-8") as f:
		return json.load(f)


def _log(msg):
	print(f"[qa-seed] {msg}")


# Name of the private File holding the staff Training-Material course fixtures.
# Kept out of the (public) repo because it carries graded-exam answer keys and
# private YouTube ids — upload it in Desk instead: /app/file -> Add File -> Private.
TM_FIXTURE_FILE = "training_material_fixtures.json"


def _load_tm_bundle():
	"""Return the Training-Material fixture bundle, or None if unavailable.

	Looks for the private File first (how deployments get the data, since only
	patches/hooks run there), then falls back to the on-disk fixtures used in
	local development. Returns a dict of {courses, quizzes, questions}.
	"""
	# 1. private File uploaded via Desk — newest wins, so re-uploading updates content
	names = frappe.get_all(
		"File",
		filters={"file_name": TM_FIXTURE_FILE},
		pluck="name",
		order_by="creation desc",
		limit=1,
	)
	if names:
		try:
			content = frappe.get_doc("File", names[0]).get_content()
			if isinstance(content, bytes):
				content = content.decode("utf-8")
			bundle = json.loads(content)
			_log(f"training-material: loaded fixtures from private File {names[0]}")
			return bundle
		except Exception:
			frappe.log_error(title="lms_internal: unreadable training-material fixture File")
			_log(f"training-material: File {names[0]} could not be read, falling back to disk")

	# 2. on-disk fixtures (local dev; gitignored, so absent on deployments)
	courses = _load("courses_training_material.json")
	if courses:
		_log("training-material: loaded fixtures from setup/data")
		return {
			"courses": courses,
			"quizzes": _load("quizzes_training_material.json") or [],
			"questions": _load("questions_training_material.json") or [],
		}

	return None


# --------------------------------------------------------------------------- files
def _copy_files(manifest):
	"""Copy bundled files to the site and ensure a File record exists. Returns (copied, created)."""
	copied = created = 0
	for f in manifest:
		url = f["file_url"]
		folder = "private" if f.get("is_private") else "public"
		dest = frappe.get_site_path(folder, "files", unquote(url.split("/files/")[-1]))
		# Physical file is authoritative — /files/<x> renders from disk regardless of
		# whether a File record exists. This must succeed.
		if not os.path.exists(dest):
			os.makedirs(os.path.dirname(dest), exist_ok=True)
			src = os.path.join(FILES, f["stored_as"])
			if os.path.exists(src):
				shutil.copy(src, dest)
				copied += 1
		# File record is secondary (Files UI / attachment tracking) — best-effort,
		# never abort the deploy over it. The File doctype re-saves the on-disk file
		# on insert and can rewrite file_url with a content-hash suffix
		# (e.g. "logo.png" -> "logo<hash>.png"); branding reads (lms.lms.api.get_branding
		# -> get_file_info) look the File up by its EXACT url, so we pin it back to the
		# clean url the manifest/Website Settings reference, or the logo resolves to null.
		if not frappe.db.exists("File", {"file_url": url}):
			try:
				doc = frappe.get_doc({
					"doctype": "File",
					"file_url": url,
					"file_name": f.get("file_name"),
					"is_private": f.get("is_private") or 0,
				}).insert(ignore_permissions=True)
				if doc.file_url != url:
					frappe.db.set_value("File", doc.name,
						{"file_url": url, "file_name": f.get("file_name")})
				created += 1
			except Exception:
				frappe.log_error(title=f"qa-seed: File record skipped for {url}")
	return copied, created


def seed_files():
	manifest = _load("files.json") or []
	copied, created = _copy_files(manifest)
	_log(f"files: {len(manifest)} referenced, {copied} copied to disk, {created} File records created")


# ------------------------------------------------------------------------- branding
def seed_branding():
	b = _load("branding.json") or {}
	for single, vals in (("Website Settings", b.get("website_settings")),
						("LMS Settings", b.get("lms_settings"))):
		for k, v in (vals or {}).items():
			frappe.db.set_value(single, single, k, v)
	_log("branding: Website Settings + LMS Settings force-set")


# ----------------------------------------------------------------------------- rbac
def seed_rbac():
	d = _load("rbac.json") or {}
	touched = set()
	for p in d.get("custom_docperm", []):
		flt = {"parent": p["parent"], "role": p["role"], "permlevel": p["permlevel"]}
		name = frappe.db.exists("Custom DocPerm", flt)
		doc = frappe.get_doc("Custom DocPerm", name) if name else frappe.new_doc("Custom DocPerm")
		doc.update(p)
		doc.parenttype = "DocType"
		doc.parentfield = "permissions"
		doc.flags.ignore_permissions = True
		doc.save()
		touched.add(p["parent"])
	for ps in d.get("property_setter", []):
		flt = {"doc_type": ps["doc_type"], "property": ps["property"]}
		if ps.get("field_name"):
			flt["field_name"] = ps["field_name"]
		name = frappe.db.exists("Property Setter", flt)
		doc = frappe.get_doc("Property Setter", name) if name else frappe.new_doc("Property Setter")
		doc.update(ps)
		doc.flags.ignore_permissions = True
		doc.save()
		touched.add(ps["doc_type"])
	for dt in touched:
		frappe.clear_cache(doctype=dt)
	_log(f"rbac: {len(d.get('custom_docperm', []))} perms, "
		f"{len(d.get('property_setter', []))} property setters applied")


# ---------------------------------------------------------------------------- users
def seed_users():
	users = _load("users.json") or []
	for u in users:
		u = dict(u)
		roles = u.pop("roles", [])
		email = u["email"]
		if frappe.db.exists("User", email):
			doc = frappe.get_doc("User", email)
			doc.update({k: v for k, v in u.items() if k != "email"})
		else:
			doc = frappe.new_doc("User")
			doc.update(u)
			doc.flags.no_welcome_mail = True
		have = {r.role for r in doc.roles}
		for r in roles:
			if r not in have and frappe.db.exists("Role", r):
				doc.append("roles", {"role": r})
		doc.flags.ignore_permissions = True
		doc.save()
	_log(f"users: {len(users)} instructor user(s) ensured")


# --------------------------------------------------------------- courses / quizzes
def _upsert(dt, data):
	data = dict(data)
	data.pop("doctype", None)
	name = data.get("name")
	if name and frappe.db.exists(dt, name):
		doc = frappe.get_doc(dt, name)
		doc.update(data)
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.flags.ignore_mandatory = True
		doc.save()
	else:
		doc = frappe.get_doc({**data, "doctype": dt})
		doc.flags.ignore_permissions = True
		doc.flags.ignore_links = True
		doc.flags.ignore_mandatory = True
		doc.insert(set_name=name)
	return doc


def seed_iso_auditor_courses():
	"""The three demo ISO Internal Auditor courses (ISO 9001 / 14001 / 27001).
	Owns these course slugs end-to-end. Each course has a graded final-exam quiz
	and an ungraded feedback survey (4-point training-evaluation scales).

	Existing LMS Quiz/Question docs are never deleted, so nothing is lost on a
	re-run while content is edited in the UI.
	"""
	courses = _load("courses_iso_auditor.json") or []
	if not courses:
		_log("iso-auditor: no course data found, skipping")
		return

	_copy_files(_load("files_iso_auditor.json") or [])

	# reconcile structure: drop only the chapters/lessons of OUR courses that are
	# no longer part of the new definition. Quizzes and questions are left untouched.
	new_chapters, new_lessons = set(), set()
	for c in courses:
		for ch in c["chapters"]:
			new_chapters.add(ch["chapter"]["name"])
			for lesson in ch["lessons"]:
				new_lessons.add(lesson["name"])
	for c in courses:
		slug = c["course"]["name"]
		for ln in frappe.get_all("Course Lesson", filters={"course": slug}, pluck="name"):
			if ln not in new_lessons:
				frappe.delete_doc("Course Lesson", ln, force=True, ignore_permissions=True)
		for cn in frappe.get_all("Course Chapter", filters={"course": slug}, pluck="name"):
			if cn not in new_chapters:
				frappe.delete_doc("Course Chapter", cn, force=True, ignore_permissions=True)

	# questions before quizzes (quiz rows reference question names),
	# quizzes before lessons (Course Lesson.on_update validates embedded quizzes).
	for q in (_load("questions_iso_auditor.json") or []):
		_upsert("LMS Question", q)
	quizzes = _load("quizzes_iso_auditor.json") or []
	for quiz in quizzes:
		_upsert("LMS Quiz", quiz)

	# lessons -> chapters -> course
	for c in courses:
		for ch in c["chapters"]:
			for lesson in ch["lessons"]:
				_upsert("Course Lesson", lesson)
	for c in courses:
		for ch in c["chapters"]:
			_upsert("Course Chapter", ch["chapter"])
	for c in courses:
		_upsert("LMS Course", c["course"])

	pending = [q["name"] for q in quizzes if not q.get("questions")]
	_log(f"iso-auditor: {len(courses)} course(s) upserted")
	if pending:
		_log(f"iso-auditor: {len(pending)} quiz(zes) with no questions yet: {pending}")


# ------------------------------------------------------------------------------ run
def run(commit=True):
	_log("seeding Quality Asia customizations …")
	seed_files()
	seed_branding()
	seed_rbac()
	seed_users()
	if commit:
		frappe.db.commit()
	_log("done.")


def run_iso_auditor_courses(commit=True):
	"""Seed just the three demo ISO Internal Auditor courses. Invoked by the
	`seed_iso_auditor_courses` patch, and runnable manually:

	  bench --site <site> execute lms_internal.setup.seed.run_iso_auditor_courses
	"""
	_log("seeding ISO Internal Auditor demo courses …")
	seed_users()  # ensure the instructor User exists before linking courses
	seed_iso_auditor_courses()
	if commit:
		frappe.db.commit()
	_log("done.")


def seed_training_material_courses():
	"""Upsert the staff Training-Material courses (tm-* slugs) built by
	tools/build_fixtures.py from the tracker's seed-ready list.

	Deliberately PURE upsert — no chapter/lesson reconcile or delete of any kind.
	It can only create/update the tm-* docs named in its own fixtures, so it can
	never remove or overwrite other courses, the ISO seed, or UI edits elsewhere.
	"""
	bundle = _load_tm_bundle()
	courses = (bundle or {}).get("courses") or []
	if not courses:
		_log("training-material: no course data found, skipping")
		return

	# questions before quizzes (quiz rows reference question names),
	# quizzes before lessons (Course Lesson.on_update validates embedded quizzes).
	for q in bundle.get("questions") or []:
		_upsert("LMS Question", q)
	for quiz in bundle.get("quizzes") or []:
		_upsert("LMS Quiz", quiz)

	# lessons -> chapters -> course
	for c in courses:
		for ch in c["chapters"]:
			for lesson in ch["lessons"]:
				_upsert("Course Lesson", lesson)
	for c in courses:
		for ch in c["chapters"]:
			_upsert("Course Chapter", ch["chapter"])
	for c in courses:
		_upsert("LMS Course", c["course"])

	_log(f"training-material: {len(courses)} course(s) upserted")


def run_training_material_courses(commit=True):
	"""Seed the staff Training-Material courses. Invoked by the
	`seed_training_material_courses` patch, and runnable manually:

	  bench --site <site> execute lms_internal.setup.seed.run_training_material_courses
	"""
	_log("seeding Training-Material staff courses …")
	seed_users()  # ensure the instructor User exists before linking courses
	seed_training_material_courses()
	if commit:
		frappe.db.commit()
	_log("done.")
