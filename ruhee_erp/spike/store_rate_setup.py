"""C7 store-rate setup on a fresh disposable site (M1-05, PR #25). Spike code only.

Replaces the undocumented dependency on PR #20's "M1-05 Native" profile: every
prerequisite is created here, from the M1-03 baseline, in this order:

    bench --site <site> set-config ruhee_c7_spike 1
    bench --site <site> set-config pause_scheduler 1 --parse
    bench --site <site> execute ruhee_erp.spike.setup_spike.run          # M1-03 baseline
    (PR #24's tested precision revision, when Codex supplies it)
    bench --site <site> execute ruhee_erp.spike.store_rate_setup.run

All data is invented. Nothing here is referenced from hooks.py.

Site artifacts (inventory in store_rate_report.md, "Site artifacts"):
- POS Awesome's own per-payment currency fields (its installed patch, re-run);
- custom DocType "Ruhee C7 Store Rate" and the ruhee_c7_* custom fields;
- POS Profile "C7 New Depo", copied from M1-03's "New Depo";
- a company Currency Exchange pair at 9999 on the test date, created once and never
  edited (adversarial: proves the store record, not the company rate, drives amounts);
- store rate record 2300/2320 effective 00:00 on the test date;
- invented item C7-UNIT-3200 with a $3,200 USD Item Price (R1 boundary line);
- an invented Material Receipt (SPIKE-001 x 10,000, C7-UNIT-3200 x 200);
- a password and terminal PIN for the M1-03 facturier, and an open POS shift on the C7 profile.
"""

import json
import secrets
from pathlib import Path

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_field
from frappe.utils import flt, now_datetime, nowdate
from frappe.utils.password import update_password

from ruhee_erp.spike.store_rate_hooks import PROFILE_FLAG, RATE_TYPE, site_enabled

COMPANY = "Ruhee Spike"
SOURCE_PROFILE = "New Depo"  # created by setup_spike.setup_pos_profile (M1-03)
PROFILE = "C7 New Depo"
FACTURIER = "facturier.spike@example.com"  # created by setup_spike.setup_users (M1-03)
COMPANY_RATE = 9999
BOUNDARY_ITEM = "C7-UNIT-3200"

FIELDS = {
	"Sales Invoice": [
		("ruhee_c7_rate", "Taux magasin (essai C7)", "Link", RATE_TYPE),
		("ruhee_c7_base", "Taux de base facturé (essai C7)", "Float", ""),
		("ruhee_c7_higher", "Taux majoré facturé (essai C7)", "Float", ""),
		("ruhee_c7_issued_at", "Émise le, heure du poste (essai C7)", "Data", ""),
		("ruhee_c7_issued_at_local", "Émise le, heure du magasin (essai C7)", "Datetime", ""),
		("ruhee_c7_hold", "À traiter par le gérant (essai C7)", "Small Text", ""),
		("ruhee_c7_tender_cdf", "Espèces CDF reçues (essai C7)", "Float", ""),
		("ruhee_c7_allocation_usd", "Montant USD affecté (essai C7)", "Float", ""),
	],
	"Sales Invoice Item": [("ruhee_c7_usd_price", "Prix USD de base (essai C7)", "Float", "")],
	"Payment Entry": [
		("ruhee_c7_rate", "Taux magasin (essai C7)", "Link", RATE_TYPE),
		("ruhee_c7_tender_cdf", "Espèces CDF reçues (essai C7)", "Float", ""),
		("ruhee_c7_allocation_usd", "Montant USD affecté (essai C7)", "Float", ""),
	],
	"POS Profile": [(PROFILE_FLAG, "Taux magasin (essai C7)", "Check", "")],
}


def guard():
	if not site_enabled():
		raise ValueError(
			"C7 setup runs only on a disposable site with ruhee_c7_spike=1 and pause_scheduler=1"
		)
	if frappe.session.user != "Administrator":
		raise ValueError("Run with bench execute as Administrator")
	for doctype, name in (("Company", COMPANY), ("POS Profile", SOURCE_PROFILE), ("User", FACTURIER)):
		if not frappe.db.exists(doctype, name):
			raise ValueError(f"Missing M1-03 baseline {doctype} {name}: run setup_spike.run first")


def account(name):
	value = frappe.db.get_value("Account", {"company": COMPANY, "account_name": name})
	if not value:
		raise ValueError(f"Missing M1-03 account {name}")
	return value


def run(test_date=None):
	guard()
	test_date = test_date or nowdate()
	report = {"site": frappe.local.site, "test_date": test_date, "created": [], "existing": []}
	from posawesome.patches.add_per_payment_multi_currency_fields import execute

	execute()  # idempotent; a fresh install marks patches done without running them
	report["created"].append("POS Awesome per-payment currency fields (installed patch, re-run)")
	_rate_doctype(report)
	_custom_fields(report)
	_profile(report)
	_company_rate(report, test_date)
	_first_store_rate(report, test_date)
	_boundary_item(report)
	_stock(report)
	_facturier(report)
	frappe.clear_cache()
	print(json.dumps(report, indent=1, default=str))


def _rate_doctype(report):
	if frappe.db.exists("DocType", RATE_TYPE):
		report["existing"].append(f"DocType {RATE_TYPE}")
		return
	frappe.get_doc(
		{
			"doctype": "DocType",
			"name": RATE_TYPE,
			"module": "Ruhee ERP",
			"custom": 1,
			"autoname": "hash",
			"is_submittable": 1,
			"fields": [
				{
					"fieldname": "company",
					"label": "Société",
					"fieldtype": "Link",
					"options": "Company",
					"reqd": 1,
				},
				{"fieldname": "store", "label": "Magasin", "fieldtype": "Data", "reqd": 1},
				{
					"fieldname": "pos_profile",
					"label": "Profil de caisse",
					"fieldtype": "Link",
					"options": "POS Profile",
					"reqd": 1,
				},
				{
					"fieldname": "effective_from",
					"label": "Date et heure d'effet",
					"fieldtype": "Datetime",
					"reqd": 1,
				},
				{
					"fieldname": "base",
					"label": "Taux de base",
					"fieldtype": "Float",
					"precision": "9",
					"reqd": 1,
				},
				{
					"fieldname": "higher",
					"label": "Taux majoré",
					"fieldtype": "Float",
					"precision": "9",
					"reqd": 1,
				},
			],
			"permissions": [{"role": "System Manager", "read": 1, "write": 1, "create": 1, "submit": 1}],
		}
	).insert()
	report["created"].append(f"DocType {RATE_TYPE}")


def _custom_fields(report):
	for doctype, rows in FIELDS.items():
		previous = "company" if doctype != "Sales Invoice Item" else "rate"
		for fieldname, label, fieldtype, options in rows:
			if frappe.get_meta(doctype).has_field(fieldname):
				report["existing"].append(f"{doctype}.{fieldname}")
			else:
				create_custom_field(
					doctype,
					{
						"fieldname": fieldname,
						"label": label,
						"fieldtype": fieldtype,
						"options": options,
						"insert_after": previous,
						"read_only": 0 if doctype == "POS Profile" else 1,
						"no_copy": 0 if doctype == "POS Profile" else 1,
						"precision": "6" if fieldtype == "Float" else "",
					},
				)
				report["created"].append(f"{doctype}.{fieldname}")
			previous = fieldname


def _profile(report):
	"""PR #20's cross_currency.setup_native settings, made explicit here (no M1-05 Native copy)."""
	if frappe.db.exists("POS Profile", PROFILE):
		report["existing"].append(f"POS Profile {PROFILE}")
		return
	profile = frappe.copy_doc(frappe.get_doc("POS Profile", SOURCE_PROFILE))
	profile.name = PROFILE
	profile.update(
		{
			PROFILE_FLAG: 1,
			"create_pos_invoice_instead_of_sales_invoice": 0,
			"update_stock": 1,
			"posa_allow_multi_currency": 1,
			"posa_enable_multi_currency_payments": 1,
			"posa_allow_payment_currency_selection": 1,
			"posa_allow_manual_payment_exchange_rate": 0,
			"posa_allow_credit_sale": 1,
			"posa_allow_partial_payment": 1,
			"posa_block_sale_beyond_available_qty": 0,
			"posa_allow_submissions_in_background_job": 0,
			"account_for_change_amount": account("Cash USD - New Depo"),
		}
	)
	users = {row.user for row in profile.applicable_for_users}
	for user in ("Administrator", FACTURIER):
		if user not in users:
			profile.append("applicable_for_users", {"user": user})
	for currency in ("USD", "CDF"):
		profile.append(
			"posa_allowed_currencies",
			{"currency": currency, "allow_for_invoices": 1, "allow_for_payments": 1, "allow_for_change": 1},
		)
	for row in profile.payments:
		row.posa_default_payment_currency = "CDF" if row.mode_of_payment == "Cash CDF" else "USD"
	profile.insert()
	report["created"].append(f"POS Profile {PROFILE} (copy of {SOURCE_PROFILE})")


def _company_rate(report, test_date):
	"""9999 on the test date. Existing pairs are checked, never edited."""
	precision = frappe.get_meta("Currency Exchange").get_field("exchange_rate").precision or 9
	for source, target, quote in (
		("USD", "CDF", COMPANY_RATE),
		("CDF", "USD", flt(1 / COMPANY_RATE, int(precision))),
	):
		name = frappe.db.get_value(
			"Currency Exchange", {"date": test_date, "from_currency": source, "to_currency": target}
		)
		if name:
			stored = frappe.db.get_value("Currency Exchange", name, "exchange_rate")
			if flt(stored, int(precision)) != quote:
				raise ValueError(
					f"Currency Exchange {name} holds {stored}, not {quote}. Do not overwrite it:"
					" use another test date or a fresh site."
				)
			report["existing"].append(f"Currency Exchange {source}->{target} {test_date} = {stored}")
			continue
		frappe.get_doc(
			{
				"doctype": "Currency Exchange",
				"date": test_date,
				"from_currency": source,
				"to_currency": target,
				"exchange_rate": quote,
				"for_selling": 1,
				"for_buying": 1,
			}
		).insert()
		report["created"].append(
			f"Currency Exchange {source}->{target} {test_date} = {quote} ({precision} places)"
		)


def add_rate(base, higher, effective_from):
	"""A new store record. Earlier records and the documents that used them are never edited."""
	guard()
	doc = frappe.get_doc(
		{
			"doctype": RATE_TYPE,
			"company": COMPANY,
			"store": "New Depo",
			"pos_profile": PROFILE,
			"effective_from": effective_from,
			"base": base,
			"higher": higher,
		}
	).insert()
	doc.submit()
	print(
		json.dumps(
			{"name": doc.name, "effective_from": str(doc.effective_from), "base": base, "higher": higher}
		)
	)
	return doc.name


def add_rate_in(base, higher, seconds):
	"""Test arrangement: a replacement record effective ``seconds`` after the server's now."""
	from frappe.utils import add_to_date

	return add_rate(base, higher, str(add_to_date(now_datetime(), seconds=int(seconds))))


def inject_submit_failures(count=1):
	"""Test arrangement only: the next ``count`` C7 submits fail before anything is written."""
	from ruhee_erp.spike.store_rate_hooks import INJECT_KEY

	guard()
	frappe.cache.set_value(INJECT_KEY, {"remaining": int(count)})
	print(json.dumps({"inject_submit_failures": int(count)}))


def _first_store_rate(report, test_date):
	existing = frappe.get_all(RATE_TYPE, filters={"pos_profile": PROFILE, "docstatus": 1}, pluck="name")
	if existing:
		report["existing"].append(f"{RATE_TYPE} records {existing}")
		return
	name = add_rate(2300, 2320, f"{test_date} 00:00:00")
	report["created"].append(f"{RATE_TYPE} {name}: 2300/2320 from {test_date} 00:00")


def _boundary_item(report):
	"""Invented $3,200 item: R1 requires exactly 7,360,000 FC at 2300 (PR #24's limit case)."""
	price_list = frappe.get_value("POS Profile", PROFILE, "selling_price_list")
	if frappe.db.exists("Item", BOUNDARY_ITEM):
		report["existing"].append(f"Item {BOUNDARY_ITEM}")
	else:
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": BOUNDARY_ITEM,
				"item_name": "C7 Unit 3200 USD",
				"item_group": "Products",
				"stock_uom": "Nos",
				"is_stock_item": 1,
				"valuation_rate": 2500,
			}
		).insert()
		report["created"].append(f"Item {BOUNDARY_ITEM}")
	if frappe.db.exists("Item Price", {"item_code": BOUNDARY_ITEM, "price_list": price_list}):
		report["existing"].append(f"Item Price {BOUNDARY_ITEM}")
	else:
		frappe.get_doc(
			{
				"doctype": "Item Price",
				"item_code": BOUNDARY_ITEM,
				"price_list": price_list,
				"price_list_rate": 3200,
			}
		).insert()
		report["created"].append(f"Item Price {BOUNDARY_ITEM} {price_list} $3,200.00")


def _stock(report):
	"""Invented opening stock so the POS item list never shows negative quantities."""
	warehouse = frappe.get_value("POS Profile", PROFILE, "warehouse")
	wanted = {"SPIKE-001": (10000, 80), BOUNDARY_ITEM: (200, 2500)}
	rows = []
	for item_code, (qty, rate) in wanted.items():
		if frappe.db.exists("Stock Ledger Entry", {"item_code": item_code, "voucher_type": "Stock Entry"}):
			report["existing"].append(f"opening stock {item_code}")
			continue
		rows.append({"item_code": item_code, "qty": qty, "basic_rate": rate, "t_warehouse": warehouse})
	if not rows:
		return
	entry = frappe.get_doc(
		{"doctype": "Stock Entry", "stock_entry_type": "Material Receipt", "company": COMPANY, "items": rows}
	).insert()
	entry.submit()
	report["created"].append(
		f"Stock Entry {entry.name} (Material Receipt, invented): {[r['item_code'] for r in rows]}"
	)


def _facturier(report):
	"""Browser login for the M1-03 facturier; the password stays in the site's private folder."""
	from posawesome.posawesome.api.employees import save_cashier_pin

	path = Path(frappe.get_site_path("private", "c7_secrets.json"))
	stored = json.loads(path.read_text()) if path.exists() else {}
	if stored.get("password") and stored.get("pin"):
		report["existing"].append("facturier password and terminal PIN (site private/c7_secrets.json)")
	else:
		if not stored.get("password"):
			stored = {"user": FACTURIER, "password": secrets.token_urlsafe(18)}
			update_password(FACTURIER, stored["password"])
		stored["pin"] = str(100000 + secrets.randbelow(900000))
		save_cashier_pin(PROFILE, FACTURIER, stored["pin"])
		temporary = path.with_suffix(".tmp")
		temporary.touch(mode=0o600)
		temporary.chmod(0o600)
		temporary.write_text(json.dumps(stored))
		temporary.replace(path)
		report["created"].append(
			"facturier password and terminal PIN, in site private/c7_secrets.json (mode 600)"
		)
	open_shift = frappe.db.get_value(
		"POS Opening Shift", {"pos_profile": PROFILE, "user": FACTURIER, "status": "Open", "docstatus": 1}
	)
	if open_shift:
		report["existing"].append(f"POS Opening Shift {open_shift}")
		return
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": PROFILE,
			"user": FACTURIER,
			"period_start_date": now_datetime(),
			"posting_date": nowdate(),
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0, "currency": "USD"},
				{"mode_of_payment": "Cash CDF", "amount": 0, "currency": "CDF"},
			],
		}
	).insert()
	shift.submit()
	report["created"].append(f"POS Opening Shift {shift.name} for {FACTURIER}")
