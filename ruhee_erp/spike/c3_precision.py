"""Explicit, idempotent C3 lab/staging schema experiment; never an app hook/patch."""

import frappe
from frappe.custom.doctype.property_setter.property_setter import make_property_setter
from frappe.database.mariadb.schema import MariaDBTable
from frappe.utils import nowdate

from ruhee_erp.spike.c3_verify import DISPOSABLE, FIELDS, STAGING, field_trace, guard


def schema_plan(doctype, meta):
	"""Read Frappe's complete MariaDB column/index plan without running its DDL."""
	if frappe.db.db_type != "mariadb":
		raise ValueError("Only the inspected MariaDB schema implementation is supported")
	table = MariaDBTable(doctype, meta)
	if table.is_new():
		raise ValueError(f"Missing existing table: {doctype}")
	table.setup_table_columns()
	for col in table.columns.values():
		col.build_for_alter_table(table.current_columns.get(col.fieldname.lower()))
	operations = []
	for action in ("add_column", "change_type", "set_default", "change_nullability", "add_unique"):
		operations.extend({"action": action, "field": c.fieldname} for c in getattr(table, action))
	for col in table.add_index:
		if not frappe.db.get_column_index(table.table_name, col.fieldname, unique=False):
			operations.append({"action": "add_index", "field": col.fieldname})
	for col in {*table.drop_index, *table.drop_unique}:
		if col.fieldname == "name":
			continue
		current = table.current_columns[col.fieldname.lower()]
		for flag, expected, unique in (("unique", col.unique, True), ("index", col.set_index, False)):
			if current[flag] != expected and not expected:
				if frappe.db.get_column_index(table.table_name, col.fieldname, unique=unique):
					operations.append({"action": f"drop_{flag}", "field": col.fieldname})
	for name, col in table.current_columns.items():
		if name not in table.columns and name not in (
			*frappe.db.DEFAULT_COLUMNS,
			*frappe.db.OPTIONAL_COLUMNS,
		):
			if not col.is_generated and frappe.db.get_column_index(table.table_name, name, unique=True):
				operations.append({"action": "drop_orphan_unique", "field": name})
	if table.alter_primary_key():
		operations.append({"action": "alter_primary_key", "field": "name"})
	if meta.sort_field == "modified" and not frappe.db.get_column_index(
		table.table_name, "modified", unique=False
	):
		operations.append({"action": "add_index", "field": "modified"})
	return {
		"doctype": doctype,
		"columns": {name: dict(col) for name, col in sorted(table.current_columns.items())},
		"operations": sorted(operations, key=lambda op: (op["field"], op["action"])),
	}


def preflight(through=5):
	"""Check every affected table before the first setter or implicit DDL commit."""
	selected = FIELDS[:through]
	setters = {}
	for doctype, field in selected:
		df = frappe.get_meta(doctype, cached=False).get_field(field)
		if not df or df.fieldtype != "Float":
			raise ValueError(f"Unexpected schema: {doctype}.{field}")
		existing = frappe.get_all(
			"Property Setter",
			filters={"doc_type": doctype, "field_name": field, "property": "precision"},
			fields=["name", "value"],
		)
		if len(existing) > 1 or any(s.value != "12" for s in existing):
			raise ValueError(f"Conflicting existing precision setter for {doctype}.{field}")
		column = frappe.db.get_column_type(doctype, field)
		if column not in ("decimal(21,9)", "decimal(21,12)") or str(df.precision) not in (
			"",
			"None",
			"9",
			"12",
		):
			raise ValueError(
				f"Untested precision/column for {doctype}.{field}; refusing a possible narrowing"
			)
		setters[(doctype, field)] = existing[0] if existing else None
	plans = []
	for doctype in dict(selected):
		meta = frappe.get_meta(doctype, cached=False)
		for dt, field in selected:
			if dt == doctype:
				meta.get_field(field).precision = "12"  # In-memory proposal only.
		plan = schema_plan(doctype, meta)
		assert_plan(plan, selected)
		plans.append(plan)
	return setters, plans


def assert_plan(plan, selected):
	for op in plan["operations"]:
		if op["action"] != "change_type" or (plan["doctype"], op["field"]) not in selected:
			raise ValueError(f"Unrelated schema change; stop without repair: {plan['doctype']}: {op}")


def run(site, through=5):
	"""Widen traced fields in order. Partial stages are disposable-site experiments."""
	guard(site)
	through = int(through)
	if through not in range(1, len(FIELDS) + 1) or (site == STAGING and through != len(FIELDS)):
		raise ValueError("Partial field isolation is allowed only on the disposable site")
	if site == STAGING and "2026-11-04" <= nowdate() <= "2026-11-06":
		raise ValueError("D-021 staging freeze: no schema changes")
	if site == DISPOSABLE and not frappe.conf.get("pause_scheduler"):
		raise ValueError("Pause the disposable site's scheduler first")
	if frappe.session.user != "Administrator":
		raise ValueError("Use bench execute as Administrator for this schema experiment")
	setters, plans = preflight(through)
	changes = []
	for doctype, field in FIELDS[:through]:
		setter = setters[(doctype, field)]
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
	output = {
		"site": site,
		"changes": changes,
		"preflight": plans,
		"trace": field_trace(),
		"production_migration": False,
	}
	print(frappe.as_json(output))
	return output


def inspect(site, through=5):
	"""No repair: fail if any selected column reverted during update or form save."""
	guard(site)
	rows = field_trace()
	print(frappe.as_json({"site": site, "trace": rows}))
	for row in rows[: int(through)]:
		assert str(row["precision"]) == "12" and row["column"] == "decimal(21,12)", row
