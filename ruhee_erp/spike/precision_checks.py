"""Read-only M1-05 precision checks for scratch or explicitly named staging.

No setup, migration, DDL, rate creation, queue processing or document save occurs.
"""

import hashlib

import frappe

FIELDS = (
	("Sales Invoice", "conversion_rate"),
	("Currency Exchange", "exchange_rate"),
	("Sales Invoice Payment", "posa_exchange_rate"),
	("Sales Invoice Payment", "posa_company_exchange_rate"),
	("Payment Entry", "source_exchange_rate"),
	("Payment Entry", "target_exchange_rate"),
)


def run(expected_site, expected_precision=None, invoice=None):
	if expected_site != frappe.local.site or expected_site in ("dev.localhost", "cc.localhost"):
		raise ValueError("Use only the exact authorized scratch/staging site; never dev or cc")
	rows = []
	for doctype, fieldname in FIELDS:
		field = frappe.get_meta(doctype).get_field(fieldname)
		column = frappe.db.get_column_type(doctype, fieldname) if field else None
		row = {
			"doctype": doctype,
			"column": fieldname,
			"metadata_precision": field.precision if field else None,
			"database_type": column,
		}
		rows.append(row)
		if expected_precision is not None:
			assert field and str(field.precision) == str(expected_precision), row
			assert column == f"decimal(21,{int(expected_precision)})", row
	output = {
		"site": frappe.local.site,
		"fields": rows,
		"uses_mariadb_root_account": bool(
			frappe.db.sql("SELECT SUBSTRING_INDEX(CURRENT_USER(), '@', 1) = 'root'")[0][0]
		),
	}
	if invoice:
		doc = frappe.get_doc("Sales Invoice", invoice)
		if doc.company != "Ruhee Spike":
			raise ValueError("Use an invented Ruhee Spike invoice for this check")
		values = {
			key: doc.get(key)
			for key in (
				"currency",
				"conversion_rate",
				"grand_total",
				"rounded_total",
				"base_grand_total",
				"base_rounded_total",
				"rounding_adjustment",
				"base_rounding_adjustment",
				"paid_amount",
				"base_paid_amount",
				"outstanding_amount",
				"ruhee_spike_rate",
			)
		}
		values["items"] = [
			{key: row.get(key) for key in ("item_code", "qty", "rate", "amount", "base_amount")}
			for row in doc.items
		]
		values["gl"] = frappe.get_all(
			"GL Entry",
			filters={"voucher_type": "Sales Invoice", "voucher_no": doc.name},
			fields=[
				"name",
				"account",
				"debit",
				"credit",
				"debit_in_account_currency",
				"credit_in_account_currency",
				"is_cancelled",
			],
			order_by="name",
		)
		output["invoice"] = {
			"name": doc.name,
			"saved_conversion_rate": doc.conversion_rate,
			"grand_total": doc.grand_total,
			"base_grand_total": doc.base_grand_total,
			"accounting_sha256": hashlib.sha256(frappe.as_json(values).encode()).hexdigest(),
		}
	print(frappe.as_json(output, indent=2))
