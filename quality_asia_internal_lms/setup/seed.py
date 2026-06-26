"""One-time seed of Quality Asia customizations onto a fresh deployment.

Carries what NO installed app recreates on its own:
  - Files      (logo / favicon / footer)
  - Branding   (Website Settings + LMS Settings runtime values)  -> force-set
  - RBAC       (admin's manual Custom DocPerm changes + Property Setters)
  - Users      (one admin/instructor account)

The internal LMS ships with NO course catalog — staff training content is
authored in-app — so there is no course / quiz / question seeding here.

Invoked once by the patch `quality_asia_internal_lms.patches.v1_0.seed_initial_data`
(recorded in Patch Log -> never re-runs -> later admin UI edits persist).

Manual re-run / second environment:
  bench --site <site> execute quality_asia_internal_lms.setup.seed.run

Every step is idempotent, so the manual re-run is safe too.
"""

import json
import os
import shutil
from urllib.parse import unquote

import frappe

DATA = frappe.get_app_path("quality_asia_internal_lms", "setup", "data")
FILES = frappe.get_app_path("quality_asia_internal_lms", "setup", "files")


def _load(name):
	path = os.path.join(DATA, name)
	if not os.path.exists(path):
		return None
	with open(path, encoding="utf-8") as f:
		return json.load(f)


def _log(msg):
	print(f"[qa-seed] {msg}")


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
		# never abort the deploy over it.
		if not frappe.db.exists("File", {"file_url": url}):
			try:
				frappe.get_doc({
					"doctype": "File",
					"file_url": url,
					"file_name": f.get("file_name"),
					"is_private": f.get("is_private") or 0,
				}).insert(ignore_permissions=True)
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
