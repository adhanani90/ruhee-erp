"""Isolated native Payment Entry precision control; no C7 hooks or fork required."""

import frappe
from frappe.utils import flt

from ruhee_erp.spike import c3_probe, c3_verify


def run(label):
	c3_probe.guard()
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	date = {"baseline": "2026-11-05", "revised": "2026-11-06"}[label]
	if frappe.db.exists("Currency Exchange", {"date": date, "from_currency": "CDF", "to_currency": "USD"}):
		raise ValueError("Use a fresh dated control; never replace a used exchange rate")
	rate = frappe.get_doc(
		{
			"doctype": c3_probe.RATE_TYPE,
			"store": "New Depo",
			"date": date,
			"base": 2300,
			"higher": 2320,
		}
	).insert()
	rate.submit()
	source = frappe.get_doc(
		{
			"doctype": "Currency Exchange",
			"date": date,
			"from_currency": "CDF",
			"to_currency": "USD",
			"exchange_rate": flt(
				1 / rate.base, int(frappe.get_meta("Currency Exchange").get_field("exchange_rate").precision)
			),
			"for_selling": 1,
			"for_buying": 1,
			"ruhee_c3_rate": rate.name,
		}
	).insert()
	profile = frappe.get_doc("POS Profile", c3_probe.PROFILE)
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"company": c3_verify.COMPANY,
			"customer": frappe.db.get_value("Customer", {"customer_name": "SPIKE-02 Client A"}),
			"currency": "USD",
			"conversion_rate": 1,
			"selling_price_list": profile.selling_price_list,
			"price_list_currency": "USD",
			"plc_conversion_rate": 1,
			"posting_date": date,
			"set_posting_time": 1,
			"due_date": date,
			"cost_center": profile.cost_center,
			"ruhee_c3_rate": rate.name,
			"is_pos": 0,
			"update_stock": 0,
			"items": [{"item_code": "SPIKE-001", "qty": 100, "rate": 100, "price_list_rate": 100}],
		}
	).insert()
	si.submit()
	pe = get_payment_entry(
		"Sales Invoice",
		si.name,
		bank_account=c3_probe.account("Cash CDF - New Depo"),
		party_amount=10000,
		bank_amount=23200000,
	)
	pe.update(
		{
			"ruhee_c3_rate": rate.name,
			"paid_amount": 10000,
			"received_amount": 23200000,
			"mode_of_payment": "Cash CDF",
			"reference_no": f"C3-PE-{label}",
			"reference_date": date,
			"posting_date": date,
			"source_exchange_rate": 1,
			"target_exchange_rate": flt(1 / rate.base, pe.precision("target_exchange_rate")),
		}
	)
	for row in pe.references:
		row.allocated_amount = 10000
		row.exchange_rate = 1
	pe.set(
		"deductions",
		[
			{
				"account": c3_probe.account("Exchange income"),
				"cost_center": profile.cost_center,
				"amount": flt(10000 - flt(pe.received_amount / rate.base, 2), 2),
				"is_exchange_gain_loss": 1,
			}
		],
	)
	# Real insert/validate and submit. No patched methods, ignore flags, or GL corrections.
	pe.insert()
	pe.submit()
	pe.reload()
	si.reload()
	assert si.outstanding_amount == 0
	values = c3_verify.snapshot(c3_verify.DISPOSABLE, payment=pe.name)
	errors = c3_verify.payment_check(values)
	if label == "baseline":
		assert pe.target_exchange_rate == 0.000434783
		assert pe.base_received_amount == 10086.97 and pe.deductions[0].amount == -86.97
		assert errors, "The nine-place failure must remain visible"
	else:
		assert not errors, errors
	print(
		frappe.as_json(
			{
				"label": label,
				"commits": c3_verify.app_commits(),
				"trace": c3_verify.field_trace(),
				"invoice": c3_verify.snapshot(c3_verify.DISPOSABLE, si.name),
				"payment": values,
				"source": c3_verify.full_record("Currency Exchange", source.name),
				"errors": errors,
				"C7_acceptance": "not claimed",
				"source_exchange_rate_reason": "USD Debtors to USD company: exactly 1",
			}
		)
	)
