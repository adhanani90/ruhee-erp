import frappe
from frappe.tests import IntegrationTestCase


class TestSmoke(IntegrationTestCase):
	"""M1-01: the site has the apps the pilot is built on."""

	def test_required_apps_installed(self):
		installed = frappe.get_installed_apps()
		for app in ("erpnext", "posawesome", "ruhee_erp"):
			self.assertIn(app, installed)
