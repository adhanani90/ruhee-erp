app_name = "ruhee_erp"
app_title = "Ruhee ERP"
app_publisher = "Ruhee Pharma"
app_description = "ERPNext customisations for Ruhee Pharma"
app_email = "dhananialim07@gmail.com"
app_license = "gpl-3.0"

# Apps
# ------------------

required_apps = ["erpnext", "posawesome"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "ruhee_erp",
# 		"logo": "/assets/ruhee_erp/logo.png",
# 		"title": "Ruhee ERP",
# 		"route": "/ruhee_erp",
# 		"has_permission": "ruhee_erp.api.permission.has_app_permission",
# 	}
# ]

# The dock, the rail down the left of the desk, is a document rather than a hook. Author it in
# Manage Dock on a developer-mode site and press Export to App, and it is written to
# `ruhee_erp/dock/ruhee_erp/ruhee_erp.json` for git to carry. An app that ships none has no
# rail: its sidebar gets a switcher in the header instead.
#
# A companion app, one that extends a host app rather than standing on its own, says so with
# `mount_on` on that same record, and its entries are appended to the host's rail. Mounting keeps
# the companion off the apps screen, so it takes precedence over any add_to_apps_screen above.

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/ruhee_erp/css/ruhee_erp.css"
# app_include_js = "/assets/ruhee_erp/js/ruhee_erp.js"

# include js, css files in header of web template
# web_include_css = "/assets/ruhee_erp/css/ruhee_erp.css"
# web_include_js = "/assets/ruhee_erp/js/ruhee_erp.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "ruhee_erp/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_kanban_js = {"doctype" : "public/js/doctype_kanban.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "ruhee_erp/public/icons.svg"

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

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "ruhee_erp.utils.jinja_methods",
# 	"filters": "ruhee_erp.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "ruhee_erp.install.before_install"
# after_install = "ruhee_erp.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "ruhee_erp.uninstall.before_uninstall"
# after_uninstall = "ruhee_erp.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "ruhee_erp.utils.before_app_install"
# after_app_install = "ruhee_erp.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "ruhee_erp.utils.before_app_uninstall"
# after_app_uninstall = "ruhee_erp.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "ruhee_erp.build.after_build"

# To hook into the build process of other apps
# The list of apps being built is passed as an argument

# after_app_build = "ruhee_erp.build.after_app_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "ruhee_erp.notifications.get_notification_config"

# Awesome Bar
# -----------
# Extra search results: list of dicts with label, description, route, index.
# route: ["List", "ToDo"], "/desk/docs/some/page", or "https://example.com"
# awesomebar_search = ["ruhee_erp.search.awesomebar_results"]

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

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"ruhee_erp.tasks.all"
# 	],
# 	"daily": [
# 		"ruhee_erp.tasks.daily"
# 	],
# 	"hourly": [
# 		"ruhee_erp.tasks.hourly"
# 	],
# 	"weekly": [
# 		"ruhee_erp.tasks.weekly"
# 	],
# 	"monthly": [
# 		"ruhee_erp.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "ruhee_erp.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "ruhee_erp.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "ruhee_erp.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "ruhee_erp.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["ruhee_erp.utils.before_request"]
# after_request = ["ruhee_erp.utils.after_request"]

# Job Events
# ----------
# before_job = ["ruhee_erp.utils.before_job"]
# after_job = ["ruhee_erp.utils.after_job"]

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
# 	"ruhee_erp.auth.validate"
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
