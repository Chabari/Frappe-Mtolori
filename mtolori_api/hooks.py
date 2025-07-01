app_name = "mtolori_api"
app_title = "Mtolori Api"
app_publisher = "Geetab Technologies Limited"
app_description = "Mtolori Api"
app_email = "geetabtechnologiesltd@gmail.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/mtolori_api/css/mtolori_api.css"
# app_include_js = "/assets/mtolori_api/js/mtolori_api.js"

# include js, css files in header of web template
# web_include_css = "/assets/mtolori_api/css/mtolori_api.css"
# web_include_js = "/assets/mtolori_api/js/mtolori_api.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "mtolori_api/public/scss/website"

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
# jinja = {
# 	"methods": "mtolori_api.utils.jinja_methods",
# 	"filters": "mtolori_api.utils.jinja_filters"
# }

# Installation
# ------------

# before_install = "mtolori_api.install.before_install"
# after_install = "mtolori_api.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "mtolori_api.uninstall.before_uninstall"
# after_uninstall = "mtolori_api.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "mtolori_api.utils.before_app_install"
# after_app_install = "mtolori_api.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "mtolori_api.utils.before_app_uninstall"
# after_app_uninstall = "mtolori_api.utils.after_app_uninstall"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "mtolori_api.notifications.get_notification_config"

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

# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
    "Price List": {
        "before_save": "mtolori_api.pricing.before_save"
    },
    "Item Price": {
        "before_save": "mtolori_api.pricing.before_save_price"
    },
    "Item": {
        "before_save": "mtolori_api.utils.before_save_item"
    },
}


fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                (
                    "Item-mtolori_customization",
                    # "Item-category",
                    "Item-sub_category",
                    "Item-pack_size",
                    "Item-weight_grams",
                    "Item-column_break_ad4gl",
                    "Item-phl_days",
                    "Item-rate_of_use",
                    "Item-extended_description",
                    "Item-the_extended_description",
                    "Item-active_ingredient",
                    "Item-target_pests",
                    "Item-target_crops",
                    "Item-item_id",
                    "Company-mtolori_api_key",
                    "Company-mtolori_host_url",
                    "Company-organization_id",
                    "Warehouse-is_virtual_store",
                    "Warehouse-shop_id",
                    "Sales Invoice-mtolori_data",
                    "Sales Invoice-order_id",
                    "Sales Invoice-order_type",
                    "Sales Invoice-order_number",
                    "Sales Invoice-delivery_method",
                    "Price List-price_list_id"
                ),
            ]
        ],
    },
    
]

# Scheduled Tasks
# ---------------

scheduler_events = {
	
	"daily": [
		"mtolori_api.utils.sync_items",
		"mtolori_api.pricing.price_group",
		"mtolori_api.pricing.item_pricing",
		"mtolori_api.pricing.sync_customers",
		"mtolori_api.utils.sync_images",
	],
}

# Testing
# -------

# before_tests = "mtolori_api.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "mtolori_api.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "mtolori_api.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["mtolori_api.utils.before_request"]
# after_request = ["mtolori_api.utils.after_request"]

# Job Events
# ----------
# before_job = ["mtolori_api.utils.before_job"]
# after_job = ["mtolori_api.utils.after_job"]

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
# 	"mtolori_api.auth.validate"
# ]
