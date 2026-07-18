import os
import re

import frappe

BRAND_CSS_HREF = "/assets/lms_internal/css/brand.css"
# Runtime enhancement of the LMS SPA that can't be done via config/fixtures
# (e.g. adding Mobile/Address/Resume + Change Password to the native Edit Profile
# modal — QA-15). Injected the same serve-time way as the brand skin.
PROFILE_JS_HREF = "/assets/lms_internal/js/profile_fields.js"
# Runtime DOM patches for the LMS SPA — currently the friendly confirmation
# message shown after an ungraded feedback quiz is submitted (replaces the
# confusing "0 out of 0" quiz summary). See public/js/qa_lms_ui.js.
LMS_UI_JS_HREF = "/assets/lms_internal/js/qa_lms_ui.js"
BRAND_LINK_TAG = (
	"\t\t<!-- Quality Asia brand skin + portal enhancements (injected by lms_internal.brand) -->\n"
	f'\t\t<link rel="stylesheet" href="{BRAND_CSS_HREF}">\n'
	f'\t\t<script defer src="{PROFILE_JS_HREF}"></script>\n'
	f'\t\t<script defer src="{LMS_UI_JS_HREF}"></script>\n'
)
# CSS-only variant for non-LMS pages (e.g. the desk /login page) — the profile
# and quiz-summary JS patches target LMS SPA DOM that doesn't exist there.
BRAND_CSS_ONLY_TAG = (
	"\t\t<!-- Quality Asia brand skin (injected by lms_internal.brand) -->\n"
	f'\t\t<link rel="stylesheet" href="{BRAND_CSS_HREF}">\n'
)

# Marker present only in the LMS SPA shell's rendered HTML.
_LMS_SHELL_MARKER = "/assets/lms/frontend/"
# Marker present on the desk login page (served at "/" and "/login" — this is
# what a Frappe Cloud site's bare domain actually resolves to, not the LMS SPA).
# Buttons like "Login with Frappe Cloud" live only here, so brand.css needs to
# reach this page too, not just the LMS shell.
_DESK_LOGIN_MARKER = 'data-path="login"'

# Matches a previously-injected QA block (comment + its following <link>/<script>
# lines) so we can strip-and-reinsert — keeps injection idempotent AND upgrade-safe
# (an older block that lacked the script gets replaced with the current one).
_QA_BLOCK_RE = re.compile(
	r"[ \t]*<!-- Quality Asia brand skin[^\n]*\n(?:[ \t]*<(?:link|script)\b[^\n]*\n)*"
)


def _inject_tags(html, tag=BRAND_LINK_TAG, require_js=True):
	"""Return `html` with the current QA tag block placed before </head>, or None
	if no change is needed. Strips any prior (possibly older) block first."""
	if "</head>" not in html:
		return None
	already_current = BRAND_CSS_HREF in html and (
		not require_js or (PROFILE_JS_HREF in html and LMS_UI_JS_HREF in html)
	)
	if already_current:
		return None  # already current — nothing to do
	html = _QA_BLOCK_RE.sub("", html)  # drop any stale block before reinserting
	return html.replace("</head>", tag + "\t</head>", 1)


def inject_brand_css_into_response(response=None, request=None, **kwargs):
	"""`after_request` hook — slip the brand <link> into the LMS page at SERVE time.

	This is the deploy-safe mechanism (works on Frappe Cloud). The file-edit
	approach below cannot work there: FC ships apps as a read-only image rebuilt
	on every deploy, so any edit to `lms/www/_lms.html` is either rejected or
	thrown away. Rewriting the response body instead writes nothing to disk, so
	it survives deploys and rebuilds and needs no manual bench command.

	Cheap by design: returns immediately for non-HTML responses (API/JSON/assets)
	and for any HTML that's neither the LMS SPA shell nor the desk login page
	(the latter is what a bare Frappe Cloud domain actually serves, and is where
	"Login with Frappe Cloud" / "Login with Email Link" actually live).
	"""
	try:
		if response is None:
			return
		ctype = response.headers.get("Content-Type", "") if response.headers else ""
		if "text/html" not in ctype:
			return
		html = response.get_data(as_text=True)
		if not html:
			return
		if _LMS_SHELL_MARKER in html:
			new_html = _inject_tags(html, tag=BRAND_LINK_TAG, require_js=True)
		elif _DESK_LOGIN_MARKER in html:
			new_html = _inject_tags(html, tag=BRAND_CSS_ONLY_TAG, require_js=False)
		else:
			return  # neither the LMS SPA shell nor the desk login page
		if new_html is not None:
			response.set_data(new_html)
	except Exception:
		# Branding must never break a page render — fail open.
		frappe.logger("lms_internal").debug("brand css response injection skipped", exc_info=True)


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
			f"[lms_internal] {path} not found (frontend not built yet); "
			"skipping brand CSS injection"
		)
		return

	with open(path, encoding="utf-8") as f:
		html = f.read()

	new_html = _inject_tags(html)
	if new_html is None:
		return  # already current, or no </head>

	try:
		with open(path, "w", encoding="utf-8") as f:
			f.write(new_html)
	except OSError as e:
		# Read-only filesystem (e.g. Frappe Cloud) — the request-time injector
		# handles skinning there. Never let this abort a migrate.
		print(f"[lms_internal] could not write brand link to {path} ({e}); "
			"request-time injector will handle it")
		return

	print(f"[lms_internal] injected brand CSS link into {path}")
