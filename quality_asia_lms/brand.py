import os

import frappe

BRAND_CSS_HREF = "/assets/quality_asia_lms/css/brand.css"
BRAND_LINK_TAG = (
	"\t\t<!-- Quality Asia brand skin (injected by quality_asia_lms.brand) -->\n"
	f'\t\t<link rel="stylesheet" href="{BRAND_CSS_HREF}">\n'
)

# Marker present only in the LMS SPA shell's rendered HTML — lets the
# request-time injector target that page without touching desk/other web pages.
_LMS_SHELL_MARKER = "/assets/lms/frontend/"


def inject_brand_css_into_response(response=None, request=None, **kwargs):
	"""`after_request` hook — slip the brand <link> into the LMS page at SERVE time.

	This is the deploy-safe mechanism (works on Frappe Cloud). The file-edit
	approach below cannot work there: FC ships apps as a read-only image rebuilt
	on every deploy, so any edit to `lms/www/_lms.html` is either rejected or
	thrown away. Rewriting the response body instead writes nothing to disk, so
	it survives deploys and rebuilds and needs no manual bench command.

	Cheap by design: returns immediately for non-HTML responses (API/JSON/assets)
	and for any HTML that isn't the LMS shell.
	"""
	try:
		if response is None:
			return
		ctype = response.headers.get("Content-Type", "") if response.headers else ""
		if "text/html" not in ctype:
			return
		html = response.get_data(as_text=True)
		if (
			not html
			or BRAND_CSS_HREF in html  # already present
			or "</head>" not in html
			or _LMS_SHELL_MARKER not in html  # not the LMS SPA shell
		):
			return
		response.set_data(html.replace("</head>", BRAND_LINK_TAG + "\t</head>", 1))
	except Exception:
		# Branding must never break a page render — fail open.
		frappe.logger("quality_asia_lms").debug("brand css response injection skipped", exc_info=True)


def inject_brand_css():
	"""Idempotently inject the brand stylesheet into the LMS SPA shell ON DISK.

	Kept for local/dev benches where app files are writable: after a bare
	`bench build` this re-adds the <link> so a plain page fetch carries it.
	On Frappe Cloud the filesystem is read-only, so the write is wrapped and
	failure is ignored — the `after_request` injector above is what actually
	skins the page there. Wired to `after_migrate`/`after_install`.
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

	try:
		with open(path, "w", encoding="utf-8") as f:
			f.write(html)
	except OSError as e:
		# Read-only filesystem (e.g. Frappe Cloud) — the request-time injector
		# handles skinning there. Never let this abort a migrate.
		print(f"[quality_asia_lms] could not write brand link to {path} ({e}); "
			"request-time injector will handle it")
		return

	print(f"[quality_asia_lms] injected brand CSS link into {path}")
