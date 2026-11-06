"""Read-only C3 capture/assertions. No document or SQL writes, never production."""

import hashlib
import subprocess
from pathlib import Path

import frappe
from frappe.utils import flt

DISPOSABLE = "c3-precision.localhost"
STAGING = "ruhee-staging.c.frappe.cloud"
ALLOWED_SITES = frozenset((DISPOSABLE, STAGING))
COMPANY = "Ruhee Spike"
FIELDS = (
	("Currency Exchange", "exchange_rate"),
	("Sales Invoice", "conversion_rate"),
	("Sales Invoice Payment", "posa_company_exchange_rate"),
	("GL Entry", "transaction_exchange_rate"),
)
OTHER_FIELDS = (
	("Sales Invoice", "plc_conversion_rate"),
	("Sales Invoice Payment", "posa_exchange_rate"),
	("Payment Entry", "source_exchange_rate"),
	("Payment Entry", "target_exchange_rate"),
	("Sales Invoice Advance", "exchange_rate"),
	("GL Entry", "reporting_currency_exchange_rate"),
)


def guard(site):
	if site not in ALLOWED_SITES or frappe.local.site != site:
		raise ValueError("Exact allow-listed disposable/staging site required; production refused")


def app_commits():
	result = {}
	for app in frappe.get_installed_apps():
		path = Path(frappe.get_app_path(app)).resolve().parent
		try:
			root = (
				subprocess.check_output(
					["git", "-C", str(path), "rev-parse", "--show-toplevel"], stderr=subprocess.DEVNULL
				)
				.decode()
				.strip()
			)
			if Path(root).resolve() != path:
				raise ValueError("App checkout root mismatch")
			result[app] = (
				subprocess.check_output(
					["git", "-C", str(path), "rev-parse", "HEAD"], stderr=subprocess.DEVNULL
				)
				.decode()
				.strip()
			)
		except (OSError, ValueError, subprocess.CalledProcessError):
			result[app] = "unverified: no readable app Git checkout; obtain deploy SHA"
	return result


def field_trace():
	rows = []
	for doctype, field in (*FIELDS, *OTHER_FIELDS):
		df = frappe.get_meta(doctype, cached=False).get_field(field)
		rows.append(
			{
				"doctype": doctype,
				"field": field,
				"precision": df.precision if df else None,
				"column": frappe.db.get_column_type(doctype, field) if df else None,
			}
		)
	return rows


def snapshot(site, invoice):
	guard(site)
	doc = frappe.get_doc("Sales Invoice", invoice)
	if doc.company != COMPANY:
		raise ValueError("Only invented Ruhee Spike invoices may be captured")
	rows = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": "Sales Invoice", "voucher_no": invoice},
		fields=["*"],
		order_by="name",
	)
	values = {"invoice": doc.as_dict(), "gl": rows}
	store = (
		frappe.get_doc("Ruhee C3 Spike Rate", doc.ruhee_c3_rate).as_dict()
		if doc.get("ruhee_c3_rate")
		else None
	)
	source_fields = ["name", "date", "exchange_rate"]
	if frappe.get_meta("Currency Exchange").has_field("ruhee_c3_rate"):
		source_fields.append("ruhee_c3_rate")
	source = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": "CDF", "to_currency": "USD", "date": ["<=", doc.posting_date]},
		fields=source_fields,
		order_by="date desc, creation desc",
		limit=1,
	)
	return {
		**values,
		"rate_context": {"store": store, "source": source},
		"sha256": hashlib.sha256(frappe.as_json(values).encode()).hexdigest(),
	}


def check(values, usd=100, qty=1):
	"""Return all discrepancies, so failed controls remain inspectable."""
	doc, rows = values["invoice"], values["gl"]
	errors = []

	def equal(label, actual, expected):
		if actual != expected:
			errors.append({"field": label, "actual": actual, "expected": expected})

	if (usd, qty) not in ((100, 1), (100, 100)):
		raise ValueError("Checker supports only example A and its 100-unit large control")
	amount = usd * qty
	cdf = amount * 2300
	rate = flt(1 / 2300, 12)
	context = values["rate_context"]
	if not doc.get("ruhee_c3_rate") or not context["store"]:
		errors.append({"field": "ruhee_c3_rate", "actual": "missing store record"})
	else:
		equal("store.docstatus", context["store"]["docstatus"], 1)
		equal("store.base", context["store"]["base"], 2300)
		equal("store.name", context["store"]["name"], doc["ruhee_c3_rate"])
	equal("source.count", len(context["source"]), 1)
	if context["source"]:
		equal(
			"source.exchange_rate (old nine-place value is insufficient)",
			context["source"][0]["exchange_rate"],
			rate,
		)
		equal("source.store_link", context["source"][0].get("ruhee_c3_rate"), doc.get("ruhee_c3_rate"))
	for field, expected in {
		"docstatus": 1,
		"currency": "CDF",
		"conversion_rate": rate,
		"grand_total": cdf,
		"rounded_total": cdf,
		"base_grand_total": amount,
		"base_rounded_total": amount,
		"paid_amount": cdf,
		"base_paid_amount": amount,
		"outstanding_amount": 0,
		"rounding_adjustment": 0,
		"base_rounding_adjustment": 0,
		"change_amount": 0,
	}.items():
		equal(field, doc.get(field), expected)
	equal("items.count", len(doc["items"]), 1)
	for item in doc["items"]:
		for field, expected in {"qty": qty, "rate": 230000, "amount": cdf, "base_amount": amount}.items():
			equal(f"items.{field}", item.get(field), expected)
	equal("payments.count", len(doc["payments"]), 1)
	for row in doc["payments"]:
		for field, expected in {
			"amount": cdf,
			"base_amount": amount,
			"posa_original_amount": cdf,
			"posa_account_amount": cdf,
			"posa_payment_currency": "CDF",
			"posa_exchange_rate": 1,
			"posa_company_exchange_rate": rate,
		}.items():
			equal(f"payments.{field}", row.get(field), expected)
	debtors = [r for r in rows if r["account"] == doc["debit_to"]]
	cash = [r for r in rows if r["account"] == doc["payments"][0]["account"]]
	equal("GL.Debtors.debit", sum(r["debit"] for r in debtors), amount)
	equal("GL.Debtors.credit", sum(r["credit"] for r in debtors), amount)
	equal("GL.Cash.debit", sum(r["debit"] for r in cash), amount)
	equal("GL.Cash.CDF", sum(r["debit_in_account_currency"] for r in cash), cdf)
	sales = [r for r in rows if r["account"] == doc["items"][0]["income_account"]]
	equal("GL.Sales.credit", sum(r["credit"] for r in sales), amount)
	equal("GL.Debtors.currency", sorted({r["account_currency"] for r in debtors}), ["USD"])
	equal("GL.Cash.currency", sorted({r["account_currency"] for r in cash}), ["CDF"])
	equal("GL.balance", flt(sum(r["debit"] - r["credit"] for r in rows), 2), 0)
	for row in rows:
		equal(f"GL.{row['name']}.is_cancelled", row["is_cancelled"], 0)
		equal(f"GL.{row['name']}.transaction_currency", row["transaction_currency"], "CDF")
		equal(f"GL.{row['name']}.transaction_exchange_rate", row["transaction_exchange_rate"], rate)
		if any(s in row["account"] for s in ("Round Off", "Exchange income", "Exchange Gain")):
			errors.append({"field": "GL.unexpected_account", "actual": row["account"]})
	return errors


def run(site, invoice, qty=1):
	guard(site)
	commits = app_commits()
	values = snapshot(site, invoice)
	errors = check(values, qty=int(qty))
	print(
		frappe.as_json({"site": site, "commits": commits, "trace": field_trace(), **values, "errors": errors})
	)
	assert not errors, errors
	return {"invoice": invoice, "arithmetic_checks": "pass", "C3_acceptance": "not claimed"}


def audit(site, invoices, rates=None):
	"""Stable read-only state for idempotence, old-data and update-survival comparisons."""
	guard(site)
	setters = frappe.get_all(
		"Property Setter",
		filters={"property": "precision", "doc_type": ["in", [dt for dt, _ in FIELDS]]},
		fields=["name", "doc_type", "field_name", "value", "creation", "modified"],
		order_by="name",
	)
	output = {
		"site": site,
		"commits": app_commits(),
		"spike_sha256": {
			name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
			for name in ("c3_precision.py", "c3_probe.py", "c3_verify.py")
		},
		"trace": field_trace(),
		"setters": [s for s in setters if (s.doc_type, s.field_name) in FIELDS],
		"snapshots": {name: snapshot(site, name) for name in invoices},
		"rates": {name: frappe.get_doc("Currency Exchange", name).as_dict() for name in rates or []},
	}
	amount_fields = (
		("Sales Invoice Item", "rate"),
		("Sales Invoice Item", "amount"),
		("Sales Invoice Item", "base_amount"),
		("Sales Invoice", "grand_total"),
		("Sales Invoice", "rounded_total"),
		("Sales Invoice", "base_grand_total"),
		("Sales Invoice", "outstanding_amount"),
		("Sales Invoice Payment", "amount"),
		("Sales Invoice Payment", "base_amount"),
		("Sales Invoice Payment", "posa_original_amount"),
		("Sales Invoice Payment", "posa_account_amount"),
		("GL Entry", "debit"),
		("GL Entry", "credit"),
		("GL Entry", "debit_in_account_currency"),
		("GL Entry", "debit_in_transaction_currency"),
		("Ruhee C3 Spike Rate", "base"),
		("Ruhee C3 Spike Rate", "higher"),
	)
	output["amount_trace"] = []
	for doctype, field in amount_fields:
		if not frappe.db.exists("DocType", doctype):
			continue
		df = frappe.get_meta(doctype).get_field(field)
		output["amount_trace"].append(
			{
				"doctype": doctype,
				"field": field,
				"fieldtype": df.fieldtype,
				"declared_precision": df.precision,
				"column": frappe.db.get_column_type(doctype, field),
			}
		)
	print(frappe.as_json(output))
