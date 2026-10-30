"""M1-03: spike baseline configuration.

Creates the test configuration every later spike check (C1-C13) uses, on dev and on
staging. Spike code only: never referenced from hooks.py, never run on production.
All data here is invented (D-019).

Run it, twice to prove it is idempotent:

    bench --site <site> execute ruhee_erp.spike.setup_spike.run
    bench --site <site> execute ruhee_erp.spike.setup_spike.check_rate

The first run replaces the ERPNext setup wizard if it has not been completed. A second
run reports "nothing to create". Records that already exist are never modified; only
the single settings listed below are set when they differ.
"""

import frappe
from frappe.desk.page.setup_wizard.setup_wizard import setup_complete
from frappe.utils import flt

from erpnext.setup.utils import get_exchange_rate

COMPANY = "Ruhee Spike"
ABBR = "RS"
COUNTRY = "Congo, The Democratic Republic of the"
STORE = "New Depo"

# Standard ERPNext rate records for the spike date (card M1-03). The store-specific
# rate is M1-05. CDF->USD is 1/2300 at the exchange_rate field's precision (9).
SPIKE_DATE = "2026-10-30"
USD_TO_CDF = 2300
CDF_TO_USD = 0.000434783

WIZARD_ARGS = {
	"language": "English",
	"country": COUNTRY,
	"timezone": "Africa/Kinshasa",
	"currency": "USD",
	"company_name": COMPANY,
	"company_abbr": ABBR,
	"chart_of_accounts": "Standard",
	"fy_start_date": "2026-01-01",
	"fy_end_date": "2026-12-31",
}

# Invented catalogue: (suffix, item name, USD selling price, USD valuation rate).
# SPIKE-001 is the $100 item of examples A-D.
ITEMS = [
	("001", "Spike Item 100 USD", 100.00, 80.00),
	("002", "Spike Paint 4L", 25.00, 18.00),
	("003", "Spike Paint 20L", 95.00, 70.00),
	("004", "Spike Cement Bag", 12.50, 9.00),
	("005", "Spike Nails 1kg", 3.00, 2.00),
	("006", "Spike Screws Box", 4.50, 3.00),
	("007", "Spike Hammer", 8.00, 5.50),
	("008", "Spike Wheelbarrow", 65.00, 48.00),
	("009", "Spike PVC Pipe 3m", 6.00, 4.20),
	("010", "Spike Tap", 11.00, 7.50),
	("011", "Spike Cable 10m", 14.00, 10.00),
	("012", "Spike Switch", 2.50, 1.60),
	("013", "Spike Bulb", 1.50, 0.90),
	("014", "Spike Padlock", 7.00, 4.80),
	("015", "Spike Roofing Sheet", 18.00, 13.00),
	("016", "Spike Tile Box", 22.00, 16.00),
	("017", "Spike Glue 1L", 5.00, 3.40),
	("018", "Spike Brush", 2.00, 1.20),
	("019", "Spike Ladder", 45.00, 33.00),
	("020", "Spike Rope 20m", 6.50, 4.50),
]

# Invented customers: (suffix, name, credit limit in USD or None).
CUSTOMERS = [
	("01", "Client Credit 100", 100),
	("02", "Client A", None),
	("03", "Client B", None),
	("04", "Client C", None),
	("05", "Client D", None),
]

# Test users with standard roles; the real roles are P3. No password is set here.
USERS = [
	("facturier.spike@example.com", "Facturier", "Spike", ["Sales User", "Accounts User", "Stock User"]),
	(
		"manager.spike@example.com",
		"Manager",
		"Spike",
		["Sales User", "Sales Manager", "Accounts User", "Accounts Manager", "Stock User", "Stock Manager"],
	),
]


class Report:
	def __init__(self):
		self.created = []
		self.updated = []
		self.existing = []

	def print(self):
		for label, rows in (("created", self.created), ("updated", self.updated)):
			for row in rows:
				print(f"  {label}: {row}")
		print(f"existing, left unchanged: {len(self.existing)}")
		if not self.created and not self.updated:
			print("nothing to create")
		else:
			print(f"created {len(self.created)}, updated {len(self.updated)}")


def run():
	report = Report()
	frappe.flags.mute_emails = True

	setup_company(report)
	setup_currency(report)
	setup_settings(report)
	accounts = setup_accounts(report)
	warehouse, cost_center = setup_store(report)
	setup_payment_modes(report, accounts)
	setup_rates(report)
	setup_items(report)
	setup_customers(report)
	setup_users(report)
	setup_pos_profile(report, warehouse, cost_center)

	frappe.db.commit()
	report.print()


def setup_company(report):
	# The setup wizard, run programmatically through the same stages as the desk
	# (frappe/desk/page/setup_wizard/setup_wizard.py:setup_complete, erpnext
	# stages from erpnext/setup/setup_wizard/setup_wizard.py:get_setup_stages).
	if not frappe.is_setup_complete():
		setup_complete(WIZARD_ARGS)
		frappe.db.commit()
		frappe.clear_cache()
		report.created.append(f"setup wizard (company {COMPANY}, fiscal year 2026)")
	elif not frappe.db.exists("Company", COMPANY):
		# Wizard already completed on this site with another company: add ours.
		if not frappe.db.exists(
			"Fiscal Year", {"year_start_date": WIZARD_ARGS["fy_start_date"], "year_end_date": WIZARD_ARGS["fy_end_date"]}
		):
			frappe.get_doc(
				{
					"doctype": "Fiscal Year",
					"year": "2026",
					"year_start_date": WIZARD_ARGS["fy_start_date"],
					"year_end_date": WIZARD_ARGS["fy_end_date"],
				}
			).insert()
			report.created.append("Fiscal Year 2026")
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": COMPANY,
				"abbr": ABBR,
				"default_currency": "USD",
				"country": COUNTRY,
				"enable_perpetual_inventory": 1,
				"create_chart_of_accounts_based_on": "Standard Template",
				"chart_of_accounts": "Standard",
			}
		).insert()
		report.created.append(f"Company {COMPANY}")
	else:
		report.existing.append(f"Company {COMPANY}")

	company = frappe.get_doc("Company", COMPANY)
	if company.default_currency != "USD":
		frappe.throw(f"Company {COMPANY} exists with currency {company.default_currency}, expected USD")


def setup_currency(report):
	set_values(report, "Currency", "CDF", {"enabled": 1, "smallest_currency_fraction_value": 50})


def setup_settings(report):
	set_single(report, "Accounts Settings", "allow_multi_currency_invoices_against_single_party_account", 1)
	set_single(report, "Stock Settings", "allow_negative_stock", 1)

	# External exchange-rate provider off: erpnext/setup/utils.py:get_exchange_rate
	# returns 0 instead of calling the provider when "Currency Exchange Settings".disabled
	# is set. Set directly: CurrencyExchangeSettings.validate calls the provider's API on
	# save (erpnext/accounts/doctype/currency_exchange_settings/currency_exchange_settings.py).
	if set_single(report, "Currency Exchange Settings", "disabled", 1, save=False):
		frappe.cache.delete_keys("currency_exchange_rate_")


def setup_accounts(report):
	"""ACCOUNTING_RULES §3 accounts for the spike. Reuses the Standard chart's own
	Debtors, Exchange Gain/Loss and Round Off accounts."""
	debtors = existing_account("Debtors")
	if frappe.db.get_value("Account", debtors, "account_currency") != "USD":
		frappe.throw(f"{debtors} is not in USD")
	report.existing.append(f"Account {debtors} (USD)")

	fx = existing_account("Exchange Gain/Loss")
	round_off = existing_account("Round Off")
	report.existing.extend([f"Account {fx}", f"Account {round_off}"])

	cash_group = existing_account("Cash In Hand", is_group=1)
	income_group = existing_account("Indirect Income", is_group=1)
	expense_group = existing_account("Indirect Expenses", is_group=1)

	accounts = {
		"debtors": debtors,
		"fx": fx,
		"round_off": round_off,
		"cash_usd": ensure_account(report, f"Cash USD - {STORE}", cash_group, "USD", "Cash"),
		"cash_cdf": ensure_account(report, f"Cash CDF - {STORE}", cash_group, "CDF", "Cash"),
		"exchange_income": ensure_account(report, "Exchange income", income_group, "USD", "Income Account"),
		"remises": ensure_account(report, "Remises accordées", expense_group, "USD", "Expense Account"),
		"over_short": ensure_account(report, "Cash over/short", expense_group, "USD", "Expense Account"),
	}

	set_values(
		report,
		"Company",
		COMPANY,
		{
			"default_receivable_account": debtors,
			"exchange_gain_loss_account": fx,
			"round_off_account": round_off,
		},
	)
	return accounts


def setup_store(report):
	warehouse_parent = frappe.db.get_value("Warehouse", {"company": COMPANY, "is_group": 1, "parent_warehouse": ["is", "not set"]})
	warehouse = frappe.db.get_value("Warehouse", {"company": COMPANY, "warehouse_name": STORE})
	if warehouse:
		report.existing.append(f"Warehouse {warehouse}")
	else:
		warehouse = (
			frappe.get_doc(
				{
					"doctype": "Warehouse",
					"warehouse_name": STORE,
					"company": COMPANY,
					"parent_warehouse": warehouse_parent,
				}
			)
			.insert()
			.name
		)
		report.created.append(f"Warehouse {warehouse}")

	cost_center_parent = frappe.db.get_value("Cost Center", {"company": COMPANY, "is_group": 1, "parent_cost_center": ["is", "not set"]})
	cost_center = frappe.db.get_value("Cost Center", {"company": COMPANY, "cost_center_name": STORE})
	if cost_center:
		report.existing.append(f"Cost Center {cost_center}")
	else:
		cost_center = (
			frappe.get_doc(
				{
					"doctype": "Cost Center",
					"cost_center_name": STORE,
					"company": COMPANY,
					"parent_cost_center": cost_center_parent,
				}
			)
			.insert()
			.name
		)
		report.created.append(f"Cost Center {cost_center}")
	return warehouse, cost_center


def setup_payment_modes(report, accounts):
	for mode, account in (("Cash USD", accounts["cash_usd"]), ("Cash CDF", accounts["cash_cdf"])):
		if not frappe.db.exists("Mode of Payment", mode):
			frappe.get_doc(
				{
					"doctype": "Mode of Payment",
					"mode_of_payment": mode,
					"type": "Cash",
					"enabled": 1,
					"accounts": [{"company": COMPANY, "default_account": account}],
				}
			).insert()
			report.created.append(f"Mode of Payment {mode} -> {account}")
			continue

		doc = frappe.get_doc("Mode of Payment", mode)
		if not any(row.company == COMPANY for row in doc.accounts):
			doc.append("accounts", {"company": COMPANY, "default_account": account})
			doc.save()
			report.updated.append(f"Mode of Payment {mode}: account {account}")
		else:
			report.existing.append(f"Mode of Payment {mode}")


def setup_rates(report):
	for from_currency, to_currency, rate in (("USD", "CDF", USD_TO_CDF), ("CDF", "USD", CDF_TO_USD)):
		filters = {"date": SPIKE_DATE, "from_currency": from_currency, "to_currency": to_currency}
		if frappe.db.exists("Currency Exchange", filters):
			report.existing.append(f"Currency Exchange {SPIKE_DATE} {from_currency}->{to_currency}")
			continue
		doc = frappe.get_doc(
			{"doctype": "Currency Exchange", **filters, "exchange_rate": rate, "for_buying": 1, "for_selling": 1}
		).insert()
		report.created.append(f"Currency Exchange {doc.name} = {rate}")


def setup_items(report):
	price_list = frappe.db.get_value("Price List", {"selling": 1, "currency": "USD", "enabled": 1})
	if not price_list:
		frappe.throw("No enabled USD selling price list")

	for suffix, item_name, price, valuation_rate in ITEMS:
		item_code = f"SPIKE-{suffix}"
		if frappe.db.exists("Item", item_code):
			report.existing.append(f"Item {item_code}")
		else:
			frappe.get_doc(
				{
					"doctype": "Item",
					"item_code": item_code,
					"item_name": item_name,
					"item_group": "Products",
					"stock_uom": "Nos",
					"is_stock_item": 1,
					"valuation_rate": valuation_rate,
				}
			).insert()
			report.created.append(f"Item {item_code}")

		if frappe.db.exists("Item Price", {"item_code": item_code, "price_list": price_list}):
			report.existing.append(f"Item Price {item_code}")
		else:
			frappe.get_doc(
				{
					"doctype": "Item Price",
					"item_code": item_code,
					"price_list": price_list,
					"price_list_rate": price,
				}
			).insert()
			report.created.append(f"Item Price {item_code} {price_list} ${price:.2f}")


def setup_customers(report):
	for suffix, customer_name, credit_limit in CUSTOMERS:
		full_name = f"SPIKE-{suffix} {customer_name}"
		if frappe.db.exists("Customer", {"customer_name": full_name}):
			report.existing.append(f"Customer {full_name}")
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Customer",
				"customer_name": full_name,
				"customer_type": "Individual",
				"customer_group": "Individual",
				"territory": "All Territories",
				"default_currency": "USD",
			}
		)
		if credit_limit:
			doc.append("credit_limits", {"company": COMPANY, "credit_limit": credit_limit})
		doc.insert()
		report.created.append(f"Customer {doc.name}" + (f" (credit limit ${credit_limit})" if credit_limit else ""))


def setup_users(report):
	for email, first_name, last_name, roles in USERS:
		if frappe.db.exists("User", email):
			report.existing.append(f"User {email}")
			continue
		user = frappe.get_doc(
			{
				"doctype": "User",
				"email": email,
				"first_name": first_name,
				"last_name": last_name,
				"send_welcome_email": 0,
			}
		)
		user.flags.no_welcome_mail = True
		user.append_roles(*roles)
		user.insert()
		report.created.append(f"User {email} ({', '.join(roles)})")


def setup_pos_profile(report, warehouse, cost_center):
	if frappe.db.exists("POS Profile", STORE):
		report.existing.append(f"POS Profile {STORE}")
		return

	company = frappe.get_doc("Company", COMPANY)
	price_list = frappe.db.get_value("Price List", {"selling": 1, "currency": "USD", "enabled": 1})
	doc = frappe.get_doc(
		{
			"doctype": "POS Profile",
			"__newname": STORE,
			"company": COMPANY,
			"currency": "USD",
			"warehouse": warehouse,
			"cost_center": cost_center,
			"selling_price_list": price_list,
			"update_stock": 1,
			"write_off_account": company.write_off_account,
			"write_off_cost_center": cost_center,
			"write_off_limit": 1,
			"payments": [
				{"mode_of_payment": "Cash USD", "default": 1},
				{"mode_of_payment": "Cash CDF"},
			],
			"applicable_for_users": [{"user": email} for email, *_ in USERS],
		}
	)
	doc.insert()
	report.created.append(f"POS Profile {doc.name} (warehouse {warehouse}, users {len(USERS)})")


def check_rate():
	"""Acceptance check: with the provider disabled, ERPNext returns the stored
	CDF->USD rate, and 232,000 FC converts to $100.87."""
	disabled = frappe.db.get_single_value("Currency Exchange Settings", "disabled")
	allow_stale = frappe.db.get_single_value("Accounts Settings", "allow_stale")
	rate = get_exchange_rate("CDF", "USD", SPIKE_DATE)
	reverse = get_exchange_rate("USD", "CDF", SPIKE_DATE)
	usd = flt(232000 * rate, frappe.get_precision("Sales Invoice", "grand_total") or 2)
	print(f"Currency Exchange Settings.disabled = {disabled}")
	print(f"Accounts Settings.allow_stale = {allow_stale}")
	print(f"get_exchange_rate('USD', 'CDF', '{SPIKE_DATE}') = {reverse}")
	print(f"get_exchange_rate('CDF', 'USD', '{SPIKE_DATE}') = {rate}")
	print(f"232,000 FC x {rate} = ${usd:.2f}")
	ok = disabled == 1 and rate == CDF_TO_USD and usd == 100.87
	print("PASS" if ok else "FAIL")


def existing_account(account_name, is_group=0):
	name = frappe.db.get_value("Account", {"company": COMPANY, "account_name": account_name, "is_group": is_group})
	if not name:
		frappe.throw(f"Account {account_name} not found for {COMPANY}; is the Standard chart installed?")
	return name


def ensure_account(report, account_name, parent, currency, account_type):
	name = frappe.db.get_value("Account", {"company": COMPANY, "account_name": account_name})
	if name:
		report.existing.append(f"Account {name}")
		return name
	doc = frappe.get_doc(
		{
			"doctype": "Account",
			"account_name": account_name,
			"company": COMPANY,
			"parent_account": parent,
			"account_currency": currency,
			"account_type": account_type,
		}
	).insert()
	report.created.append(f"Account {doc.name} ({currency})")
	return doc.name


def set_values(report, doctype, name, values):
	current = frappe.db.get_value(doctype, name, list(values), as_dict=True)
	changes = {k: v for k, v in values.items() if current.get(k) != v}
	if not changes:
		report.existing.append(f"{doctype} {name}")
		return
	doc = frappe.get_doc(doctype, name)
	doc.update(changes)
	doc.save()
	report.updated.append(f"{doctype} {name}: {changes}")


def set_single(report, doctype, field, value, save=True):
	if frappe.db.get_single_value(doctype, field) == value:
		report.existing.append(f"{doctype}.{field}")
		return False
	if save:
		doc = frappe.get_single(doctype)
		doc.set(field, value)
		doc.save()
	else:
		frappe.db.set_single_value(doctype, field, value)
	report.updated.append(f"{doctype}.{field} = {value}")
	return True
