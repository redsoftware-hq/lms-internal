import os

import frappe

BRAND_CSS_HREF = "/assets/quality_asia_lms/css/brand.css"
BRAND_LINK_TAG = (
	"\t\t<!-- Quality Asia brand skin (injected by quality_asia_lms.brand) -->\n"
	f'\t\t<link rel="stylesheet" href="{BRAND_CSS_HREF}">\n'
)


def inject_brand_css():
	"""Idempotently inject the Quality Asia brand stylesheet into the LMS SPA shell.

	`lms/www/_lms.html` is generated from the frontend build (see the lms
	frontend's `copy-html-entry` script) and is git-ignored, so any `bench build`
	overwrites manual edits to it. Running this on `after_migrate`/`after_install`
	re-adds our <link>. `bench update` runs build then migrate, so wiring this to
	`after_migrate` makes it self-heal after every rebuild.

	The brand stylesheet itself lives in this app and is loaded after the
	frappe-ui bundle (we insert just before </head>) so its :root tokens win.
	"""
	try:
		path = frappe.get_app_path("lms", "www", "_lms.html")
	except Exception:
		# lms app not installed / path unavailable — nothing to skin
		return

	if not os.path.exists(path):
		print(
			f"[quality_asia_lms] {path} not found (frontend not built yet); "
			"skipping brand CSS injection"
		)
		return

	with open(path, encoding="utf-8") as f:
		html = f.read()

	if BRAND_CSS_HREF in html:
		return  # already injected

	if "</head>" not in html:
		print("[quality_asia_lms] no </head> found in _lms.html; skipping brand CSS injection")
		return

	html = html.replace("</head>", BRAND_LINK_TAG + "\t</head>", 1)

	with open(path, "w", encoding="utf-8") as f:
		f.write(html)

	print(f"[quality_asia_lms] injected brand CSS link into {path}")
