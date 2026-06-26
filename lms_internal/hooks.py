app_name = "lms_internal"
app_title = "Quality Asia Internal LMS"
app_publisher = "Red Software"
app_description = "Custom Frappe app for Quality Asia Internal LMS"
app_email = "kirtan.tank@redsoftware.in"
app_license = "mit"

# Apps
# ------------------

# required_apps = []

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "lms_internal",
# 		"logo": "/assets/lms_internal/logo.png",
# 		"title": "Quality Asia Internal LMS",
# 		"route": "/lms_internal",
# 		"has_permission": "lms_internal.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/lms_internal/css/lms_internal.css"
# app_include_js = "/assets/lms_internal/js/lms_internal.js"

# include js, css files in header of web template
# web_include_css = "/assets/lms_internal/css/lms_internal.css"
# web_include_js = "/assets/lms_internal/js/lms_internal.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "lms_internal/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "lms_internal/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

# add methods and filters to jinja environment
# Exposes format_training_dates() to the QA Certificate print format.
jinja = {
	"methods": [
		"lms_internal.overrides.certificate.format_training_dates",
		"lms_internal.overrides.certificate.qa_cert_image",
	],
}

# Invite-only product: no public self-signup form. Sign-up is disabled via
# LMS Settings (disable_signup=1, seeded in branding.json) and employees are
# registered from the back end (see lms_internal.setup.invite).

# Installation
# ------------

# before_install = "lms_internal.install.before_install"
after_install = "lms_internal.brand.inject_brand_css"

# Re-inject the brand skin <link> into the (build-generated) LMS SPA shell.
# bench update runs build -> migrate, so after_migrate self-heals the link.
# Also re-point existing certificates onto the QA print format (runs after the
# fixtures that create that print format are synced).
after_migrate = [
	"lms_internal.brand.inject_brand_css",
	"lms_internal.overrides.certificate.enforce_qa_certificate_template",
]

# Uninstallation
# ------------

# before_uninstall = "lms_internal.uninstall.before_uninstall"
# after_uninstall = "lms_internal.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "lms_internal.utils.before_app_install"
# after_app_install = "lms_internal.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "lms_internal.utils.before_app_uninstall"
# after_app_uninstall = "lms_internal.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "lms_internal.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes

# override_doctype_class = {
# 	"ToDo": "custom_app.overrides.CustomToDo"
# }

override_doctype_class = {
	# Attach the certificate PDF to the certification email (in-memory, no File stored).
	"LMS Certificate": "lms_internal.overrides.certificate.QALMSCertificate",
}

# Document Events
# ---------------
# Hook on document methods and events

# Force every generated certificate onto the QA print format and auto-fill the
# two training dates from the issue date.
doc_events = {
	"LMS Certificate": {
		"before_insert": "lms_internal.overrides.certificate.prepare_certificate",
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"lms_internal.tasks.all"
# 	],
# 	"daily": [
# 		"lms_internal.tasks.daily"
# 	],
# 	"hourly": [
# 		"lms_internal.tasks.hourly"
# 	],
# 	"weekly": [
# 		"lms_internal.tasks.weekly"
# 	],
# 	"monthly": [
# 		"lms_internal.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "lms_internal.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "lms_internal.event.get_events"
# }
# No payment overrides — the internal LMS is free (no Razorpay / GST).
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "lms_internal.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["lms_internal.utils.before_request"]
# Inject the brand skin <link> into the LMS SPA shell at SERVE time. This is the
# deploy-safe path: Frappe Cloud ships apps read-only, so editing _lms.html on
# disk (after_migrate, below) can't stick there — rewriting the response can.
after_request = ["lms_internal.brand.inject_brand_css_into_response"]

# Job Events
# ----------
# before_job = ["lms_internal.utils.before_job"]
# after_job = ["lms_internal.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"lms_internal.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

# Fixtures
# --------
# Shipped-as-code customizations re-applied on every `bench migrate`:
#   - the two training-date Custom Fields on LMS Certificate
#   - the Property Setter that makes "QA Certificate" the default print format
#   - the "QA Certificate" print format itself
# Order matters: the print format is imported before the Property Setter that names it.
fixtures = [
	{
		"dt": "Custom Field",
		"filters": [["name", "in", [
			"LMS Certificate-training_start_date",
			"LMS Certificate-training_end_date",
			"LMS Certificate-training_dates",
			"LMS Certificate-candidate_name_as_printed",
		]]],
	},
	{
		"dt": "Print Format",
		"filters": [["name", "in", ["QA Certificate"]]],
	},
	{
		"dt": "Property Setter",
		"filters": [["name", "in", ["LMS Certificate-main-default_print_format"]]],
	},
]

