"""Supported-hook C7 feasibility prototype, NOT production money code.

Only m105.localhost / the dedicated C7 profile are affected. Explicit record
binding only: no choice of Q1/Q2/Q5, rate-selection workflow or general replay
guarantee. No framework/POS function is replaced at runtime.
"""

import frappe
from frappe.utils import flt, get_datetime

SITE = "m105.localhost"
PROFILE = "C7 New Depo"
RATE_TYPE = "Ruhee C7 Store Rate"
SUBMIT = "posawesome.posawesome.api.invoices.submit_invoice"


def enabled(doc):
	return frappe.local.site == SITE and doc.get("pos_profile") == PROFILE


def record_for(doc):
	rate = frappe.get_doc(RATE_TYPE, doc.get("ruhee_c7_rate"))
	if rate.docstatus != 1 or rate.pos_profile != PROFILE or rate.company != doc.company:
		raise ValueError("C7 requires the explicit submitted record for this company/profile")
	if rate.base <= 0 or rate.higher <= 0:
		raise ValueError("C7 requires positive direct quotes")
	stamp = get_datetime(f"{doc.posting_date} {doc.get('posting_time') or '23:59:59'}")
	if get_datetime(rate.effective_from) > stamp:
		raise ValueError("C7 record is not effective at the document's posting time")
	return rate


def bind_rate(doc, method=None):
	"""After creation.update_invoice's overwrite, before controller validation."""
	if not enabled(doc):
		return
	if doc.is_return or doc.currency not in ("USD", "CDF"):
		raise ValueError("C7 probe covers A/C/D sales only")
	rate = record_for(doc)
	old = doc.get_doc_before_save()
	if old and old.ruhee_c7_rate and old.ruhee_c7_rate != rate.name:
		raise ValueError("C7 draft is already bound; do not replace its rate record")
	doc.conversion_rate = flt(1 / rate.base, doc.precision("conversion_rate")) if doc.currency == "CDF" else 1
	doc.plc_conversion_rate = 1
	doc.price_list_currency = "USD"
	# AccountsController.validate recalculates dependent totals next. POS Awesome
	# normalizes CDF-on-CDF tender from this rate in before_save/before_submit.


@frappe.whitelist()
def submit_invoice(invoice: str, data: str, submit_in_background: bool = False):
	"""HTTP override for online / default 'off' replay; native submit still runs."""
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice as native_submit

	payload = frappe.parse_json(invoice)
	context = frappe.parse_json(data)
	if enabled(payload):
		cdf = [p for p in payload.get("payments", []) if p.get("posa_payment_currency") == "CDF"]
		if payload.get("currency") == "USD" and cdf:
			if len(cdf) != 1 or len(payload["payments"]) != 1:
				raise ValueError("C7 prototype covers one CDF tender only; F is P2")
			rate = record_for(frappe._dict(payload))
			tender = flt(cdf[0].get("posa_original_amount"), 2)
			# Direct quotes are authoritative; only A/C/D's exact tender is in scope.
			allocation = flt(tender / rate.higher, 2)
			payload.update(ruhee_c7_tender_cdf=tender, ruhee_c7_allocation_usd=allocation)
			payload["payments"] = [
				{
					"mode_of_payment": "Cash USD",
					"amount": 0,
					"posa_original_amount": 0,
					"posa_payment_currency": "USD",
				}
			]
			context["is_credit_sale"] = 1
		result = native_submit(frappe.as_json(payload), frappe.as_json(context), submit_in_background)
		# A queued draft is never represented as a completed payment by this probe.
		return result
	return native_submit(invoice, data, submit_in_background)


def bind_payment_rate(doc, method=None):
	if frappe.local.site != SITE or not doc.get("ruhee_c7_rate"):
		return
	rate = frappe.get_doc(RATE_TYPE, doc.ruhee_c7_rate)
	if rate.docstatus != 1 or rate.pos_profile != PROFILE or doc.company != rate.company:
		raise ValueError("Wrong C7 payment rate")
	doc.source_exchange_rate = 1
	doc.target_exchange_rate = flt(1 / rate.base, doc.precision("target_exchange_rate"))


def settle_cdf_tender(doc, method=None):
	"""Document hook runs AFTER SalesInvoice.on_submit has written invoice GL."""
	if not enabled(doc) or not doc.get("ruhee_c7_tender_cdf"):
		return
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	rate = record_for(doc)
	cash = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Cash CDF - New Depo"})
	exchange = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Exchange income"})
	allocation = doc.ruhee_c7_allocation_usd
	pe = get_payment_entry(
		"Sales Invoice",
		doc.name,
		bank_account=cash,
		party_amount=allocation,
		bank_amount=doc.ruhee_c7_tender_cdf,
	)
	pe.ruhee_c7_rate = rate.name
	pe.paid_amount = allocation
	pe.received_amount = doc.ruhee_c7_tender_cdf
	pe.mode_of_payment = "Cash CDF"
	pe.reference_no = doc.posa_pos_opening_shift
	pe.reference_date = doc.posting_date
	pe.posting_date = doc.posting_date
	bind_payment_rate(pe)
	for row in pe.references:
		row.allocated_amount = allocation
		row.exchange_rate = 1
	pe.set(
		"deductions",
		[
			{
				"account": exchange,
				"cost_center": doc.cost_center,
				"amount": flt(allocation - flt(pe.received_amount / rate.base, 2), 2),
				"is_exchange_gain_loss": 1,
			}
		],
	)
	pe.insert()
	pe.submit()
	# No commit or submitted-document correction. The returned SI response may
	# still have a stale outstanding field; the probe explicitly reloads it.
