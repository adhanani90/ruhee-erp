"""Explicit, idempotent C3 lab/staging schema experiment; never an app hook/patch."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.utils import nowdate

from ruhee_erp.spike.c3_verify import DISPOSABLE, FIELDS, STAGING, field_trace, guard


def run(site, through=4):
	"""Widen traced fields in order. Partial stages are disposable-site experiments."""
	guard(site)
	through = int(through)
	if through not in (1, 2, 3, 4) or (site == STAGING and through != 4):
		raise ValueError("Partial field isolation is allowed only on the disposable site")
	if site == STAGING and "2026-11-04" <= nowdate() <= "2026-11-06":
		raise ValueError("D-021 staging freeze: no schema changes")
	if site == DISPOSABLE and not frappe.conf.get("pause_scheduler"):
		raise ValueError("Pause the disposable site's scheduler first")
	if frappe.session.user != "Administrator":
		raise ValueError("Use bench execute as Administrator for this schema experiment")
	changes = []
	for doctype, field in FIELDS[:through]:
		df = frappe.get_meta(doctype, cached=False).get_field(field)
		if not df or df.fieldtype != "Float":
			raise ValueError(f"Unexpected schema: {doctype}.{field}")
		setter = frappe.db.get_value(
			"Property Setter",
			{"doc_type": doctype, "field_name": field, "property": "precision"},
			["name", "value"],
			as_dict=True,
		)
		if setter and setter.value != "12":
			raise ValueError(f"Conflicting existing precision setter for {doctype}.{field}")
		if not setter:
			make_property_setter(doctype, field, "precision", "12", "Data")
			changes.append(f"Property Setter: {doctype}.{field}")
		frappe.clear_cache(doctype=doctype)
		meta = frappe.get_meta(doctype, cached=False)
		if frappe.db.get_column_type(doctype, field) != "decimal(21,12)":
			frappe.db.updatedb(doctype, meta)
			changes.append(f"Schema sync: {doctype}")
		assert str(meta.get_field(field).precision) == "12"
		assert frappe.db.get_column_type(doctype, field) == "decimal(21,12)"
	output = {"site": site, "changes": changes, "trace": field_trace(), "production_migration": False}
	print(frappe.as_json(output))
	return output


def inspect(site, through=4):
	"""No repair: fail if any selected column reverted during update or form save."""
	guard(site)
	rows = field_trace()
	print(frappe.as_json({"site": site, "trace": rows}))
	for row in rows[: int(through)]:
		assert str(row["precision"]) == "12" and row["column"] == "decimal(21,12)", row
