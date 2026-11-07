"""C7 store-rate spike hooks (M1-05, PR #25). NOT production money code.

Active only when BOTH hold:
- the site's site_config sets ``ruhee_c7_spike: 1`` and ``pause_scheduler: 1`` (a
  disposable test site; staging needs Sam's explicit approval first);
- the document's POS Profile has the custom check ``ruhee_c7_store_rate`` set.

What the hooks do (spike scope only; Q1, Q2 and Q5 are not decided here):
- ``get_store_rate`` gives the POS client the store record's identity and direct
  quotes, so the client prices CDF lines as USD price x base (R1) and computes CDF
  due on a USD bill as USD x higher (R3).
- ``bind_rate`` (Sales Invoice before_validate) requires that binding on every CDF
  bill and every USD bill paid in CDF (I6), checks it against the bill's issue time,
  and sets the bill's rate from the bound record, never from Currency Exchange.
- ``check_lines`` (Sales Invoice validate) rejects CDF line prices that are not the
  billed USD basis x the bound base quote. It never reprices.
- ``submit_invoice`` (POS Awesome submit override) and ``bind_rate`` move a USD
  bill's net CDF tender into a separate Payment Entry made by ``settle_cdf_tender``,
  valued at the base quote by ``value_cdf_received`` (R7).
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import frappe
from frappe import _
from frappe.utils import cint, flt, get_datetime, get_system_timezone, now_datetime

RATE_TYPE = "Ruhee C7 Store Rate"
SUBMIT = "posawesome.posawesome.api.invoices.submit_invoice"
PROFILE_FLAG = "ruhee_c7_store_rate"
# Tolerance for client clocks. A bill issued more than this after the server's
# "now", or before its rate record existed, is held: a client timestamp alone does
# not prove chronology (see store_rate_report.md, "Bill-issued time").
CLOCK_TOLERANCE = timedelta(minutes=5)
# Test-only failure injection, read from the site cache on disposable sites.
INJECT_KEY = "ruhee_c7_inject_submit_failure"
TITLE = _("Taux magasin (essai C7)")


def site_enabled():
	return cint(frappe.conf.get("ruhee_c7_spike")) == 1 and cint(frappe.conf.get("pause_scheduler")) == 1


def profile_enabled(profile):
	return (
		bool(profile)
		and site_enabled()
		and bool(cint(frappe.get_cached_value("POS Profile", profile, PROFILE_FLAG)))
	)


def enabled(doc):
	return profile_enabled(doc.get("pos_profile"))


def fail(message):
	frappe.throw(message, frappe.ValidationError, title=TITLE)


def _records(company, profile):
	return frappe.get_all(
		RATE_TYPE,
		filters={"docstatus": 1, "company": company, "pos_profile": profile},
		fields=["name", "store", "effective_from", "base", "higher", "creation"],
		order_by="effective_from desc, creation desc",
	)


def applicable_record(company, profile, at):
	"""Latest submitted record effective at ``at`` (naive, system timezone).

	Returns (record, problem). Two records with the same effective time are a
	conflict, never resolved by picking the last one.
	"""
	rows = [r for r in _records(company, profile) if get_datetime(r.effective_from) <= at]
	if not rows:
		return None, "no_record"
	if len(rows) > 1 and get_datetime(rows[0].effective_from) == get_datetime(rows[1].effective_from):
		return None, "conflict"
	return rows[0], None


def issued_local(value):
	"""Client ISO-8601 time with an offset -> naive datetime in the system timezone."""
	if not value:
		return None
	try:
		stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
	except ValueError:
		fail(_("Heure d'émission illisible : {0}").format(value))
	if stamp.tzinfo is None:
		fail(_("Heure d'émission sans fuseau horaire : {0}").format(value))
	return stamp.astimezone(ZoneInfo(get_system_timezone())).replace(tzinfo=None)


def bound_record(doc):
	"""The store record named by the bill, checked against the bill's company and store."""
	name = doc.get("ruhee_c7_rate")
	if not name:
		fail(_("Taux magasin manquant : la facture n'indique aucun enregistrement de taux (I6)."))
	if not frappe.db.exists(RATE_TYPE, name):
		fail(_("Enregistrement de taux {0} introuvable.").format(name))
	record = frappe.get_doc(RATE_TYPE, name)
	if record.docstatus != 1:
		fail(_("L'enregistrement de taux {0} n'est pas validé.").format(name))
	if record.company != doc.get("company") or record.pos_profile != doc.get("pos_profile"):
		fail(
			_("L'enregistrement de taux {0} appartient à une autre société ou un autre magasin.").format(name)
		)
	if flt(record.base) <= 0 or flt(record.higher) <= 0:
		fail(_("L'enregistrement de taux {0} n'a pas de taux positifs.").format(name))
	if flt(doc.get("ruhee_c7_base")) != flt(record.base) or flt(doc.get("ruhee_c7_higher")) != flt(
		record.higher
	):
		fail(
			_("Les taux facturés ({0}/{1}) ne sont pas ceux de l'enregistrement {2} ({3}/{4}).").format(
				doc.get("ruhee_c7_base"), doc.get("ruhee_c7_higher"), name, record.base, record.higher
			)
		)
	return record


def _paid_rows(rows):
	return [p for p in rows or [] if flt(p.get("posa_original_amount")) or flt(p.get("amount"))]


def _cdf_rows(rows):
	return [p for p in _paid_rows(rows) if p.get("posa_payment_currency") == "CDF"]


def _needs_binding(doc):
	return (
		doc.get("currency") == "CDF"
		or bool(_cdf_rows(doc.get("payments")))
		or bool(flt(doc.get("ruhee_c7_tender_cdf")))
	)


def _submitting(doc):
	return doc.get("_action") == "submit" or doc.docstatus == 1


def _hold_reason(doc, record, issued):
	"""Why a bill issued at ``issued`` may not post with ``record``; None if it may."""
	if issued > now_datetime() + CLOCK_TOLERANCE:
		return _("heure d'émission dans le futur (horloge du poste ?)")
	if get_datetime(record.creation) > issued + CLOCK_TOLERANCE:
		return _("émise avant la création de l'enregistrement {0} (horloge du poste ?)").format(record.name)
	current, problem = applicable_record(doc.company, doc.pos_profile, issued)
	if problem == "conflict":
		return _("deux enregistrements de taux ont la même heure d'effet")
	if problem:
		return _("aucun enregistrement de taux en vigueur à l'heure d'émission")
	if current.name != record.name:
		return _("taux {0} remplacé par {1} ({2}/{3}) à l'heure d'émission").format(
			record.name, current.name, current.base, current.higher
		)
	return None


def bind_rate(doc, method=None):
	"""Sales Invoice before_validate: after POS Awesome's update_invoice overwrite."""
	if not enabled(doc) or doc.docstatus == 2:
		return
	if doc.get("is_return"):
		fail(_("Les retours ne sont pas couverts par l'essai C7."))
	if doc.currency not in ("USD", "CDF"):
		fail(_("L'essai C7 ne couvre que les factures en USD ou en CDF."))
	if not doc.get("ruhee_c7_rate") and not _needs_binding(doc):
		return  # USD bill paid in USD: no rate is involved (I6 covers CDF and cross-currency only)
	record = bound_record(doc)
	previous = doc.get_doc_before_save()
	if previous and previous.get("ruhee_c7_rate") and previous.ruhee_c7_rate != record.name:
		fail(_("Cette facture est déjà liée à {0} ; son taux ne change pas.").format(previous.ruhee_c7_rate))

	issued = issued_local(doc.get("ruhee_c7_issued_at"))
	if issued:
		doc.ruhee_c7_issued_at_local = issued
		hold = _hold_reason(doc, record, issued)
		if hold and _submitting(doc):
			fail(_("Facture non validée, à traiter par le gérant : {0}.").format(hold))
		# A draft is kept exactly as billed, never repriced; the reason is visible.
		doc.ruhee_c7_hold = hold
	elif _submitting(doc):
		fail(_("Heure d'émission manquante : la facture ne peut pas être validée."))
	elif get_datetime(record.effective_from) > now_datetime():
		fail(_("L'enregistrement de taux {0} n'est pas encore en vigueur.").format(record.name))

	doc.conversion_rate = (
		flt(1 / flt(record.base), doc.precision("conversion_rate")) if doc.currency == "CDF" else 1
	)
	doc.plc_conversion_rate = 1
	doc.price_list_currency = "USD"
	if doc.currency == "USD" and _cdf_rows(doc.get("payments")):
		_fold_cdf_tender_into_doc(doc, record)


def _fold(payments, record):
	"""Net CDF tender on a USD bill -> (tender, allocation). One CDF tender only."""
	paid = _paid_rows(payments)
	cdf = _cdf_rows(payments)
	if len(cdf) != 1 or len(paid) != 1:
		fail(_("L'essai C7 couvre un seul paiement en CDF sur une facture USD (le paiement mixte F est P2)."))
	tender = flt(cdf[0].get("posa_original_amount"), 2)
	if tender <= 0:
		fail(_("Montant CDF reçu manquant."))
	return tender, flt(tender / flt(record.higher), 2)


def _fold_cdf_tender_into_doc(doc, record):
	"""Draft fallback path: keep the net CDF tender, not an inline row valued by Currency Exchange."""
	tender, allocation = _fold(doc.get("payments"), record)
	doc.ruhee_c7_tender_cdf = tender
	doc.ruhee_c7_allocation_usd = allocation
	doc.set("payments", [])
	doc.append("payments", {"mode_of_payment": "Cash USD", "amount": 0, "base_amount": 0})


def check_lines(doc, method=None):
	"""Sales Invoice validate (after ERPNext totals): reject, never reprice."""
	if not enabled(doc) or doc.docstatus == 2 or not doc.get("ruhee_c7_rate"):
		return
	record = frappe.get_doc(RATE_TYPE, doc.ruhee_c7_rate)
	if flt(doc.get("discount_amount")) or flt(doc.get("additional_discount_percentage")):
		fail(_("Remise sur facture non couverte par l'essai C7."))
	for item in doc.items:
		if (
			flt(item.get("discount_percentage"))
			or flt(item.get("discount_amount"))
			or flt(item.get("margin_rate_or_amount"))
			or item.get("pricing_rules")
			or cint(item.get("is_free_item"))
		):
			fail(
				_("Ligne {0} : remise, marge ou règle de prix non couverte par l'essai C7.").format(item.idx)
			)
		usd = flt(item.get("ruhee_c7_usd_price"))
		if usd <= 0:
			fail(_("Ligne {0} : prix USD de base manquant.").format(item.idx))
		expected = flt(usd * flt(record.base), item.precision("rate")) if doc.currency == "CDF" else usd
		for fieldname in ("price_list_rate", "rate"):
			if flt(item.get(fieldname), item.precision("rate")) != expected:
				fail(
					_("Ligne {0} : {1} {2} au lieu de {3} USD x {4} = {5}.").format(
						item.idx, fieldname, item.get(fieldname), usd, record.base, expected
					)
				)
	if doc.currency == "USD" and flt(doc.get("ruhee_c7_tender_cdf")):
		allocation = flt(flt(doc.ruhee_c7_tender_cdf) / flt(record.higher), 2)
		if allocation != flt(doc.ruhee_c7_allocation_usd):
			fail(_("Montant USD affecté incohérent avec le montant CDF reçu."))
		due = flt(doc.get("rounded_total") or doc.grand_total, doc.precision("grand_total"))
		if allocation > due:
			fail(
				_(
					"{0} FC couvrent {1} USD, plus que les {2} USD dus. Enregistrer le montant net ;"
					" la monnaie rendue se gère à la main."
				).format(doc.ruhee_c7_tender_cdf, allocation, due)
			)


def _inject_failure():
	"""Test-only: fail the next N submits on a disposable site, before anything is written."""
	spec = frappe.cache.get_value(INJECT_KEY)
	if spec and cint(spec.get("remaining")) > 0:
		spec["remaining"] = cint(spec["remaining"]) - 1
		frappe.cache.set_value(INJECT_KEY, spec)
		frappe.throw(_("Essai C7 : échec de validation provoqué (récupérable)."), title=TITLE)


@frappe.whitelist()
def submit_invoice(invoice: str, data: str, submit_in_background: bool = False):
	"""HTTP override for online and default 'off' replay; native submit still runs."""
	from posawesome.posawesome.api.invoice_processing.creation import submit_invoice as native_submit

	payload = frappe.parse_json(invoice)
	if not enabled(payload):
		return native_submit(invoice, data, submit_in_background)
	context = frappe.parse_json(data)
	_inject_failure()
	if payload.get("currency") == "USD" and _cdf_rows(payload.get("payments")):
		record = bound_record(frappe._dict(payload))
		tender, allocation = _fold(payload.get("payments"), record)
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
	return native_submit(frappe.as_json(payload), frappe.as_json(context), submit_in_background)


@frappe.whitelist()
def get_store_rate(pos_profile: str) -> dict:
	"""The store record in force now for this profile, with its identity and direct quotes."""
	if not profile_enabled(pos_profile):
		frappe.throw(_("Ce profil de caisse n'utilise pas le taux magasin (essai C7)."), title=TITLE)
	profile = frappe.get_doc("POS Profile", pos_profile)
	profile.check_permission("read")
	record, problem = applicable_record(profile.company, profile.name, now_datetime())
	if problem:
		# Q5 (no rate) is not decided: the client gets no binding and the server
		# rejects CDF bills without one.
		return {"found": False, "reason": problem, "server_time": str(now_datetime())}
	return {
		"found": True,
		"name": record.name,
		"company": profile.company,
		"pos_profile": profile.name,
		"store": record.store,
		"effective_from": str(record.effective_from),
		"base": flt(record.base),
		"higher": flt(record.higher),
		"server_time": str(now_datetime()),
		"timezone": get_system_timezone(),
	}


def _payment_record(doc):
	record = frappe.get_doc(RATE_TYPE, doc.ruhee_c7_rate)
	if record.docstatus != 1 or doc.company != record.company:
		fail(_("Enregistrement de taux du paiement invalide."))
	return record


def bind_payment_rate(doc, method=None):
	"""Payment Entry before_validate."""
	if not site_enabled() or not doc.get("ruhee_c7_rate"):
		return
	record = _payment_record(doc)
	doc.source_exchange_rate = 1
	doc.target_exchange_rate = flt(1 / flt(record.base), doc.precision("target_exchange_rate"))


def value_cdf_received(doc, method=None):
	"""Payment Entry validate, after ERPNext's set_amounts: CDF received = CDF / base (R7).

	ERPNext multiplies by the stored reciprocal (9 places by default), which is a
	cent off from about 10,000 USD. The direct quote is used instead.
	"""
	if not site_enabled() or not doc.get("ruhee_c7_rate"):
		return
	record = _payment_record(doc)
	received = flt(flt(doc.received_amount) / flt(record.base), doc.precision("base_received_amount"))
	doc.base_received_amount = received
	doc.base_received_amount_after_tax = received
	rows = [d for d in doc.deductions if d.is_exchange_gain_loss]
	if len(rows) != 1:
		fail(_("Le paiement C7 attend une seule ligne d'écart de change."))
	rows[0].amount = flt(flt(doc.base_paid_amount) - received, rows[0].precision("amount"))
	doc.set_difference_amount()
	if flt(doc.difference_amount):
		fail(_("Écart non soldé sur le paiement C7 : {0}.").format(doc.difference_amount))


def settle_cdf_tender(doc, method=None):
	"""Sales Invoice on_submit, after its GL is written: one Payment Entry for the CDF tender."""
	if not enabled(doc) or not flt(doc.get("ruhee_c7_tender_cdf")):
		return
	from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry

	record = bound_record(doc)
	cash = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Cash CDF - New Depo"})
	exchange = frappe.db.get_value("Account", {"company": doc.company, "account_name": "Exchange income"})
	allocation = flt(doc.ruhee_c7_allocation_usd)
	pe = get_payment_entry(
		"Sales Invoice",
		doc.name,
		bank_account=cash,
		party_amount=allocation,
		bank_amount=doc.ruhee_c7_tender_cdf,
	)
	pe.ruhee_c7_rate = record.name
	pe.ruhee_c7_tender_cdf = doc.ruhee_c7_tender_cdf
	pe.ruhee_c7_allocation_usd = allocation
	pe.paid_amount = allocation
	pe.received_amount = doc.ruhee_c7_tender_cdf
	pe.mode_of_payment = "Cash CDF"
	pe.reference_no = doc.posa_pos_opening_shift or doc.name
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
				"amount": flt(allocation - flt(pe.received_amount) / flt(record.base), 2),
				"is_exchange_gain_loss": 1,
			}
		],
	)
	pe.insert()
	pe.submit()
