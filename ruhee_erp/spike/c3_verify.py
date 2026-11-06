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
	("Payment Entry", "target_exchange_rate"),
)
OTHER_FIELDS = (
	("Sales Invoice", "plc_conversion_rate"),
	("Sales Invoice Payment", "posa_exchange_rate"),
	("Payment Entry", "source_exchange_rate"),
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


def full_record(doctype, name):
	"""Every stored parent/child column, including modified, without transient Doc flags."""
	parent = frappe.get_all(doctype, filters={"name": name}, fields=["*"])
	if len(parent) != 1:
		raise ValueError(f"Missing {doctype}: {name}")
	values = dict(parent[0])
	for df in frappe.get_meta(doctype).get_table_fields():
		values[df.fieldname] = frappe.get_all(
			df.options,
			filters={"parent": name, "parenttype": doctype, "parentfield": df.fieldname},
			fields=["*"],
			order_by="idx, name",
		)
	return values


def digest(values):
	return hashlib.sha256(frappe.as_json(values).encode()).hexdigest()


def snapshot(site, invoice=None, payment=None):
	guard(site)
	if bool(invoice) == bool(payment):
		raise ValueError("Choose exactly one Sales Invoice or Payment Entry")
	doctype, name = ("Payment Entry", payment) if payment else ("Sales Invoice", invoice)
	doc = frappe.get_doc(doctype, name)
	if doc.company != COMPANY:
		raise ValueError("Only invented Ruhee Spike invoices may be captured")
	rows = frappe.get_all(
		"GL Entry",
		filters={"voucher_type": doctype, "voucher_no": name},
		fields=["*"],
		order_by="name",
	)
	values = {"payment" if payment else "invoice": full_record(doctype, name), "gl": rows}
	store = None
	for field, rate_type in (
		("ruhee_c3_rate", "Ruhee C3 Spike Rate"),
		("ruhee_c7_rate", "Ruhee C7 Store Rate"),
	):
		if doc.get(field):
			store = full_record(rate_type, doc.get(field))
	source = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": "CDF", "to_currency": "USD", "date": ["<=", doc.posting_date]},
		fields=["*"],
		order_by="date desc, creation desc",
		limit=1,
	)
	return {
		**values,
		"rate_context": {"store": store, "source": source},
		"sha256": digest(values),
	}


def payment_check(values, usd=10000):
	"""Assert saved standard C4 Payment Entry and its own GL, never resubmit it."""
	doc, rows = values["payment"], values["gl"]
	errors = []

	def equal(label, actual, expected):
		if actual != expected:
			errors.append({"field": label, "actual": actual, "expected": expected})

	cdf = usd * 2320
	base = flt(cdf / 2300, 2)
	for field, expected in {
		"docstatus": 1,
		"source_exchange_rate": 1,
		"target_exchange_rate": flt(1 / 2300, 12),
		"paid_from_account_currency": "USD",
		"paid_to_account_currency": "CDF",
		"paid_amount": usd,
		"received_amount": cdf,
		"base_paid_amount": usd,
		"base_received_amount": base,
		"total_allocated_amount": usd,
		"difference_amount": 0,
	}.items():
		equal(field, doc.get(field), expected)
	equal("references.count", len(doc["references"]), 1)
	for row in doc["references"]:
		equal("reference.allocated_amount", row["allocated_amount"], usd)
		equal("reference.exchange_rate", row["exchange_rate"], 1)
	equal("deductions.count", len(doc["deductions"]), 1)
	for row in doc["deductions"]:
		equal("deduction.amount", row["amount"], flt(usd - base, 2))
		equal("deduction.is_exchange_gain_loss", row["is_exchange_gain_loss"], 1)
	cash = [r for r in rows if r["account"] == doc["paid_to"]]
	debtors = [r for r in rows if r["account"] == doc["paid_from"]]
	fx = [r for r in rows if r["account"] in {d["account"] for d in doc["deductions"]}]
	equal("GL.Cash.debit", sum(r["debit"] for r in cash), base)
	equal("GL.Cash.CDF", sum(r["debit_in_account_currency"] for r in cash), cdf)
	equal("GL.Debtors.credit", sum(r["credit"] for r in debtors), usd)
	equal("GL.Exchange_income.credit", sum(r["credit"] for r in fx), flt(base - usd, 2))
	equal("GL.balance", flt(sum(r["debit"] - r["credit"] for r in rows), 2), 0)
	equal("GL.row_count", len(rows), 3)
	for row in rows:
		equal(f"GL.{row['name']}.is_cancelled", row["is_cancelled"], 0)
	store = values["rate_context"]["store"]
	equal("store.base", store.get("base") if store else None, 2300)
	equal("store.higher", store.get("higher") if store else None, 2320)
	return errors


def payment(site, name, usd=10000):
	values = snapshot(site, payment=name)
	errors = payment_check(values, int(usd))
	print(frappe.as_json({"site": site, "commits": app_commits(), **values, "errors": errors}))
	assert not errors, errors
	return {"payment": name, "arithmetic_checks": "pass", "C3_acceptance": "not claimed"}


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


def audit(site, invoices, rates=None, payments=None):
	"""Stable read-only state for idempotence, old-data and update-survival comparisons."""
	guard(site)
	setters = frappe.get_all(
		"Property Setter",
		filters={"doc_type": ["in", [dt for dt, _ in FIELDS]]},
		fields=["*"],
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
		"setters": setters,
		"columns": {
			dt: sorted(
				(dict(c) for c in frappe.db.get_table_columns_description(f"tab{dt}")),
				key=lambda c: c["name"],
			)
			for dt in dict(FIELDS)
		},
		"snapshots": {name: snapshot(site, name) for name in invoices},
		"payments": {name: snapshot(site, payment=name) for name in payments or []},
		"rates": {name: full_record("Currency Exchange", name) for name in rates or []},
		"store_rates": {
			dt: {name: full_record(dt, name) for name in frappe.get_all(dt, pluck="name", order_by="name")}
			for dt in ("Ruhee C3 Spike Rate", "Ruhee C7 Store Rate")
			if frappe.db.exists("DocType", dt)
		},
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
		("Payment Entry", "base_received_amount"),
		("Payment Entry Reference", "allocated_amount"),
		("Payment Entry Deduction", "amount"),
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
	return output


def audit_all(site):
	"""Capture the complete invented submitted population and all its rate context."""
	guard(site)
	return audit(
		site,
		frappe.get_all(
			"Sales Invoice", filters={"company": COMPANY, "docstatus": 1}, pluck="name", order_by="name"
		),
		rates=frappe.get_all("Currency Exchange", pluck="name", order_by="name"),
		payments=frappe.get_all(
			"Payment Entry", filters={"company": COMPANY, "docstatus": 1}, pluck="name", order_by="name"
		),
	)
