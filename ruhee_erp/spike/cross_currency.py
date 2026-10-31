"""M1-05 experiments. Only run against the restored m105.localhost scratch site.

Never invoke against dev.localhost, cc.localhost, staging or production. No hooks
are installed by importing this module. No queued browser invoice is read/retried.
"""

import secrets

import frappe
from frappe.utils import flt, now_datetime, nowdate

SCRATCH = "m105.localhost"
COMPANY = "Ruhee Spike"


def guard():
	if frappe.local.site != SCRATCH:
		raise ValueError(f"Scratch-only experiment; expected {SCRATCH}")
	if not frappe.conf.get("pause_scheduler"):
		raise ValueError("Scratch scheduler must remain paused")
	if not frappe.db.exists("Company", COMPANY):
		raise ValueError("Restore the dev.localhost backup before running experiments")


def inspect():
	"""Read the restored prerequisites before changing any scratch configuration."""
	guard()
	profiles = []
	profile_fields = (
		"company",
		"currency",
		"selling_price_list",
		"update_stock",
		"create_pos_invoice_instead_of_sales_invoice",
		"posa_allow_multi_currency",
		"posa_enable_multi_currency_payments",
		"posa_allow_payment_currency_selection",
		"posa_default_payment_currency",
		"posa_allow_manual_payment_exchange_rate",
		"account_for_change_amount",
		"posa_use_pos_awesome_payments",
	)
	profile_meta = frappe.get_meta("POS Profile")
	for name in ("New Depo", "M1-04 New Depo"):
		if not frappe.db.exists("POS Profile", name):
			continue
		doc = frappe.get_doc("POS Profile", name)
		row = {key: doc.get(key) for key in profile_fields}
		row.update(
			name=name,
			missing_schema_fields=[key for key in profile_fields if not profile_meta.has_field(key)],
		)
		row["allowed_currencies"] = [r.as_dict() for r in doc.get("posa_allowed_currencies") or []]
		row["payments"] = [r.as_dict() for r in doc.payments]
		profiles.append(row)
	modes = []
	for name in ("Cash USD", "Cash CDF"):
		if frappe.db.exists("Mode of Payment", name):
			doc = frappe.get_doc("Mode of Payment", name)
			modes.append(
				{
					"name": name,
					"enabled": doc.enabled,
					"type": doc.type,
					"accounts": [
						{
							"company": r.company,
							"default_account": r.default_account,
							"currency": frappe.db.get_value("Account", r.default_account, "account_currency"),
						}
						for r in doc.accounts
						if r.company == COMPANY
					],
				}
			)
	settings = {}
	for doctype in ("Accounts Settings", "POS Settings", "Currency Exchange Settings"):
		meta = frappe.get_meta(doctype)
		doc = frappe.get_single(doctype)
		settings[doctype] = {
			f.fieldname: doc.get(f.fieldname)
			for f in meta.fields
			if any(s in f.fieldname for s in ("currency", "exchange", "round", "payment", "disabled"))
			and f.fieldtype in ("Check", "Select", "Int", "Float", "Link")
		}
	evidence = {
		"site": SCRATCH,
		"captured_at": str(now_datetime()),
		"profiles": profiles,
		"modes": modes,
		"settings": settings,
		"rates": frappe.get_all(
			"Currency Exchange",
			filters={"from_currency": ["in", ["CDF", "USD"]], "to_currency": ["in", ["CDF", "USD"]]},
			fields=["name", "date", "from_currency", "to_currency", "exchange_rate", "for_selling"],
			order_by="date",
		),
		"currencies": frappe.get_all(
			"Currency",
			filters={"name": ["in", ["USD", "CDF"]]},
			fields=["name", "enabled", "smallest_currency_fraction_value"],
		),
	}
	print(frappe.as_json(evidence, indent=2))


def setup_native():
	"""Configure a dedicated scratch profile, recording missing schema explicitly."""
	guard()
	from posawesome.patches.add_per_payment_multi_currency_fields import execute

	# Use the installed patch's own field definitions, on scratch only. This also
	# makes an unmigrated backup's missing prerequisites reproducible in code.
	execute()
	name = "M1-05 Native"
	if frappe.db.exists("POS Profile", name):
		return
	profile = frappe.copy_doc(frappe.get_doc("POS Profile", "New Depo"))
	profile.name = name
	profile.update(
		{
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
	profile.append("applicable_for_users", {"user": "Administrator"})
	for currency in ("USD", "CDF"):
		profile.append(
			"posa_allowed_currencies",
			{"currency": currency, "allow_for_invoices": 1, "allow_for_payments": 1, "allow_for_change": 1},
		)
	for row in profile.payments:
		row.posa_default_payment_currency = "CDF" if row.mode_of_payment == "Cash CDF" else "USD"
	profile.insert()
	print("Created scratch-only M1-05 Native profile; no rates or precision changed")


def account(name):
	value = frappe.db.get_value("Account", {"company": COMPANY, "account_name": name})
	if not value:
		raise ValueError(f"Missing invented baseline account: {name}")
	return value


def run_native(label="native_9"):
	"""Submit new server-side bills through POS Awesome; never retries an old bill."""
	guard()
	from posawesome.posawesome.api.employees import (
		lock_terminal,
		save_cashier_pin,
		verify_terminal_employee_pin,
	)
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice, update_invoice

	profile = frappe.get_doc("POS Profile", "M1-05 Native")
	cashier = f"m105-{frappe.generate_hash(length=10).lower()}@example.com"
	frappe.get_doc(
		{
			"doctype": "User",
			"email": cashier,
			"first_name": "M1-05",
			"last_name": "Scratch",
			"send_welcome_email": 0,
			"roles": [{"role": "Sales User"}],
		}
	).insert()
	profile.append("applicable_for_users", {"user": cashier})
	profile.save()
	pin = str(100000 + secrets.randbelow(900000))
	save_cashier_pin(profile.name, cashier, pin)
	verify_terminal_employee_pin(profile.name, cashier, pin)
	open_shift = frappe.db.get_value(
		"POS Opening Shift",
		{"pos_profile": profile.name, "user": "Administrator", "status": "Open", "docstatus": 1},
	)
	if open_shift:
		raise ValueError(f"Existing scratch shift {open_shift}; inspect before creating another")
	shift = frappe.get_doc(
		{
			"doctype": "POS Opening Shift",
			"company": COMPANY,
			"pos_profile": profile.name,
			"user": "Administrator",
			"period_start_date": now_datetime(),
			"posting_date": nowdate(),
			"balance_details": [
				{"mode_of_payment": "Cash USD", "amount": 0, "currency": "USD"},
				{"mode_of_payment": "Cash CDF", "amount": 0, "currency": "CDF"},
			],
		}
	).insert()
	shift.submit()
	customer = frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"})
	rates = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": "CDF", "to_currency": "USD", "date": ["<=", nowdate()]},
		fields=["exchange_rate"],
		order_by="date desc",
		limit=1,
	)
	if not rates:
		raise ValueError("Missing CDF->USD rate in restored baseline")
	reciprocal = rates[0].exchange_rate
	price = flt(100 / reciprocal, int(profile.posa_decimal_precision or 2))
	cases = (
		("C3", "CDF", price, 1, 230000),
		("CDF-large", "CDF", 230000, 100, 23000000),
		("C4", "USD", 100, 1, 232000),
		("C4-large", "USD", 100, 100, 23200000),
		("O-unrounded-tender", "USD", 1, 1, 2320),
	)
	rows = []
	for case, currency, rate, qty, tender in cases:
		payload = {
			"doctype": "Sales Invoice",
			"company": COMPANY,
			"pos_profile": profile.name,
			"posa_pos_opening_shift": shift.name,
			"customer": customer,
			"currency": currency,
			"price_list_currency": "USD",
			"selling_price_list": profile.selling_price_list,
			"posting_date": nowdate(),
			"due_date": nowdate(),
			"is_pos": 1,
			"update_stock": 1,
			"set_warehouse": profile.warehouse,
			"cost_center": profile.cost_center,
			"account_for_change_amount": profile.account_for_change_amount,
			"items": [
				{
					"item_code": "SPIKE-001",
					"qty": qty,
					"rate": rate,
					"price_list_rate": rate,
					"warehouse": profile.warehouse,
				}
			],
			"payments": [
				{
					"mode_of_payment": "Cash CDF",
					"account": account("Cash CDF - New Depo"),
					"amount": tender if currency == "CDF" else flt(tender * reciprocal, 2),
					"posa_payment_currency": "CDF",
					"posa_original_amount": tender,
				}
			],
		}
		frappe.db.savepoint("m105_case")
		try:
			draft = update_invoice(frappe.as_json(payload))
			result = submit_invoice(
				frappe.as_json(draft),
				frappe.as_json(
					{"pos_profile": profile.name, "posa_pos_opening_shift": shift.name, "due_date": nowdate()}
				),
			)
			doc = frappe.get_doc(result["doctype"], result["name"])
			rows.append({"case": case, "input_tender_cdf": tender, **invoice_evidence(doc)})
		except Exception as exc:
			frappe.db.rollback(save_point="m105_case")
			rows.append({"case": case, "error_type": type(exc).__name__, "error": str(exc)})
	from posawesome.posawesome.doctype.pos_closing_shift.closing_processing.creation import (
		make_closing_shift_from_opening,
		submit_closing_shift,
	)

	closing = make_closing_shift_from_opening(frappe.as_json(shift.as_dict()))["closing_shift"].as_dict()
	for row in closing.get("payment_reconciliation", []):
		row["closing_amount"] = row.get("expected_amount", 0)
		row["closing_amount_in_currency"] = row.get("expected_amount_in_currency", 0)
	close_name = submit_closing_shift(frappe.as_json(closing))
	lock_terminal(profile.name)
	frappe.get_doc("User", cashier).update({"enabled": 0}).save()
	print(
		frappe.as_json(
			{
				"label": label,
				"site": SCRATCH,
				"captured_at": str(now_datetime()),
				"rate": reciprocal,
				"cdf_unit_price": price,
				"opening_shift": shift.name,
				"closing_shift": close_name,
				"cases": rows,
			},
			indent=2,
		)
	)


def invoice_evidence(doc):
	fields = (
		"name",
		"docstatus",
		"currency",
		"conversion_rate",
		"grand_total",
		"rounded_total",
		"rounding_adjustment",
		"base_grand_total",
		"paid_amount",
		"base_paid_amount",
		"change_amount",
		"base_change_amount",
		"outstanding_amount",
		"account_for_change_amount",
	)
	return {
		**{k: doc.get(k) for k in fields},
		"items": [
			{k: i.get(k) for k in ("item_code", "qty", "rate", "amount", "base_rate", "base_amount")}
			for i in doc.items
		],
		"payments": [
			{
				k: p.get(k)
				for k in (
					"mode_of_payment",
					"account",
					"amount",
					"base_amount",
					"posa_payment_currency",
					"posa_original_amount",
					"posa_exchange_rate",
					"posa_company_exchange_rate",
					"posa_account_amount",
				)
			}
			for p in doc.payments
		],
		"gl": frappe.get_all(
			"GL Entry",
			filters={"voucher_type": doc.doctype, "voucher_no": doc.name},
			fields=[
				"name",
				"account",
				"account_currency",
				"debit",
				"credit",
				"debit_in_account_currency",
				"credit_in_account_currency",
				"is_cancelled",
			],
			order_by="name",
		),
	}


def set_precision(scope="invoice"):
	"""Scratch-only precision experiment; caller must run scratch migrate next.

	Invoice-only isolates whether changing conversion_rate alone is sufficient.
	Full-chain is a separate experiment; it must not be described as config-only.
	"""
	guard()
	from frappe.custom.doctype.property_setter.property_setter import make_property_setter

	fields = [("Sales Invoice", "conversion_rate")]
	if scope == "chain":
		fields += [
			("Currency Exchange", "exchange_rate"),
			("Sales Invoice Payment", "posa_exchange_rate"),
			("Sales Invoice Payment", "posa_company_exchange_rate"),
			("Payment Entry", "source_exchange_rate"),
			("Payment Entry", "target_exchange_rate"),
		]
	elif scope != "invoice":
		raise ValueError("scope must be invoice or chain")
	for doctype, fieldname in fields:
		if not frappe.get_meta(doctype).has_field(fieldname):
			raise ValueError(f"Missing scratch schema prerequisite: {doctype}.{fieldname}")
		make_property_setter(doctype, fieldname, "precision", "12", "Data")
	print("Saved scratch Property Setters. Run bench --site m105.localhost migrate, then inspect_precision.")


def inspect_precision(old_invoice=None):
	"""Read the actual post-migrate columns, resolved precision and optional old GL."""
	guard()
	fields = [
		("Sales Invoice", "conversion_rate"),
		("Currency Exchange", "exchange_rate"),
		("Sales Invoice Payment", "posa_exchange_rate"),
		("Sales Invoice Payment", "posa_company_exchange_rate"),
		("Payment Entry", "source_exchange_rate"),
		("Payment Entry", "target_exchange_rate"),
	]
	evidence = {"site": SCRATCH, "captured_at": str(now_datetime()), "fields": []}
	for doctype, fieldname in fields:
		field = frappe.get_meta(doctype).get_field(fieldname)
		evidence["fields"].append(
			{
				"doctype": doctype,
				"fieldname": fieldname,
				"metadata_precision": field.precision if field else None,
				"column_type": frappe.db.get_column_type(doctype, fieldname) if field else None,
			}
		)
	if old_invoice:
		doc = frappe.get_doc("Sales Invoice", old_invoice)
		if doc.company != COMPANY:
			raise ValueError("Only invented baseline company invoices can be inspected")
		evidence["old_invoice"] = invoice_evidence(doc)
	print(frappe.as_json(evidence, indent=2))


def refresh_scratch_reciprocal():
	"""Recompute the scratch source rate only after full-chain precision/migrate.

	No submitted invoice/payment is edited. This is an experiment on a disposable
	restore, not the production R11 store-record mechanism.
	"""
	guard()
	if frappe.get_meta("Currency Exchange").get_field("exchange_rate").precision != "12":
		raise ValueError("Run full-chain precision setup and migrate before this experiment")
	direct = frappe.get_all(
		"Currency Exchange",
		filters={"from_currency": "USD", "to_currency": "CDF", "date": ["<=", nowdate()]},
		fields=["exchange_rate"],
		order_by="date desc",
		limit=1,
	)

	if not direct:
		raise ValueError("Missing direct USD->CDF base rate")
	name = frappe.db.get_value("Currency Exchange", {"from_currency": "CDF", "to_currency": "USD"})
	if not name:
		raise ValueError("Missing scratch reciprocal rate record")
	doc = frappe.get_doc("Currency Exchange", name)
	doc.exchange_rate = flt(1 / direct[0].exchange_rate, 12)
	doc.save()
	frappe.cache.delete_keys("currency_exchange_rate_")
	print(
		frappe.as_json(
			{
				"scratch_source_rate_record": doc.name,
				"direct_base": direct[0].exchange_rate,
				"new_reciprocal": doc.exchange_rate,
				"submitted_documents_edited": False,
			}
		)
	)


def payment_rounding_probe():
	"""Exercise native tender normalization at 2320 without deciding Q1.

	The manual-rate permission is on a copied profile only, not a changed stored
	profile. This isolates the native normalizer; USD/CDF submission is blocked by
	the separately reported account-currency validator.
	"""
	guard()
	from posawesome.posawesome.api.payment_currency import normalize_invoice_payment_currencies

	profile = frappe.copy_doc(frappe.get_doc("POS Profile", "M1-05 Native"))
	profile.posa_allow_manual_payment_exchange_rate = 1
	results = []
	for source in ("currency_exchange", "manual"):
		doc = frappe.get_doc(
			{
				"doctype": "Sales Invoice",
				"company": COMPANY,
				"currency": "USD",
				"conversion_rate": 1,
				"posting_date": nowdate(),
				"pos_profile": "M1-05 Native",
				"payments": [
					{
						"mode_of_payment": "Cash CDF",
						"account": account("Cash CDF - New Depo"),
						"amount": 1,
						"posa_payment_currency": "CDF",
						"posa_original_amount": 2320,
						"posa_exchange_rate": 1 / 2320,
						"posa_rate_source": source,
					}
				],
			}
		)
		normalize_invoice_payment_currencies(doc, profile_doc=profile)
		row = doc.payments[0]
		results.append(
			{
				"input_rate_source": source,
				"input_tender_cdf": 2320,
				"output_tender_cdf": row.posa_original_amount,
				"invoice_amount_usd": row.amount,
				"base_amount_usd": row.base_amount,
				"invoice_rate": row.posa_exchange_rate,
				"account_amount_cdf": row.posa_account_amount,
				"saved_invoice": False,
			}
		)
	assert all(r["output_tender_cdf"] == 2320 for r in results)
	print(
		frappe.as_json(
			{
				"site": SCRATCH,
				"native_normalization": results,
				"rounds_to_50_fc": False,
				"q1_policy_selected": False,
			},
			indent=2,
		)
	)


def synchronize_precision_columns():
	"""Scratch-only explicit schema sync after metadata/fixture processing.

	The observed migrate left some columns at 9 despite live metadata=12. Use
	Frappe's own schema sync with explicitly fetched final metadata, not raw SQL.
	"""
	guard()
	for doctype in ("Sales Invoice", "Currency Exchange", "Sales Invoice Payment", "Payment Entry"):
		frappe.clear_cache(doctype=doctype)
		frappe.db.updatedb(doctype, meta=frappe.get_meta(doctype, cached=False))
	print("Synchronized scratch columns from final app-owned precision metadata")
