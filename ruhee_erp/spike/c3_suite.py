"""Run from an isolated bench root with the revised app importable; fresh site only.

Usage: python apps/ruhee_erp/ruhee_erp/spike/c3_suite.py --output /tmp/c3-evidence
The installed bench CLI supplies every database operation. No shared services start.
"""

import argparse
import gzip
import hashlib
import json
import subprocess
from pathlib import Path

SITE = "c3-precision-review.localhost"


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--output", type=Path, required=True)
	parser.add_argument("--resume-after-customize", action="store_true")
	parser.add_argument("--resume-after-reload", action="store_true")
	parser.add_argument("--resume-after-migrate", action="store_true")
	args = parser.parse_args()
	resume = args.resume_after_customize or args.resume_after_reload or args.resume_after_migrate
	args.output.mkdir(parents=True, exist_ok=resume)
	summary = (
		json.loads((args.output / "summary.json").read_text())
		if resume
		else {"site": SITE, "commands": [], "preservation": [], "C3_acceptance": "not claimed"}
	)

	def read(label):
		return json.loads(gzip.decompress((args.output / f"{label}.json.gz").read_bytes()))

	def execute(label, method=None, kwargs=None, command=None):
		cmd = ["bench", "--site", SITE]
		cmd += command or ["execute", f"ruhee_erp.spike.{method}", "--kwargs", json.dumps(kwargs or {})]
		result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
		(args.output / f"{label}.log").write_text(result.stdout)
		summary["commands"].append({"label": label, "argv": cmd, "exit_code": result.returncode})
		if result.returncode:
			print(result.stdout[-8000:], flush=True)
			raise RuntimeError(f"{label} failed; see {args.output}")
		values = []
		decoder = json.JSONDecoder()
		i = 0
		while i < len(result.stdout):
			if result.stdout[i] == "{":
				try:
					value, length = decoder.raw_decode(result.stdout[i:])
					values.append(value)
					i += length
					continue
				except ValueError:
					pass
			i += 1
		# Some methods print a preliminary trace and bench prints a small return receipt.
		value = max(values, key=lambda v: len(json.dumps(v))) if values else None
		if value is not None:
			content = json.dumps(value, indent=2, sort_keys=True).encode()
			with (args.output / f"{label}.json.gz").open("wb") as stream:
				with gzip.GzipFile(fileobj=stream, mode="wb", mtime=0) as archive:
					archive.write(content)
		print(f"{label}: pass", flush=True)
		return value

	def audit(label):
		return execute(label, "c3_verify.audit_all", {"site": SITE})

	def compare(label, before, after, schema_unchanged=False):
		keys = ("snapshots", "payments", "rates", "store_rates")
		metadata_added = []
		metadata_changed = []
		if schema_unchanged:
			keys += ("columns", "trace", "amount_trace")
			if label in ("customize", "reload", "migrate"):
				old, new = ({r["name"]: r for r in state["setters"]} for state in (before, after))
				for name, row in old.items():
					assert name in new, f"Setter removed: {name}"
					if row != new[name]:
						assert label == "migrate" and name in (
							"Sales Invoice-posa_pos_opening_shift-no_copy",
							"Sales Invoice-update_outstanding_for_self-default",
						), f"Unexpected setter change: {name}"
						changed = {k for k in row.keys() | new[name].keys() if row.get(k) != new[name].get(k)}
						assert changed == {"creation"}, f"Unexpected fixture changes: {name}: {changed}"
						metadata_changed.append({"before": row, "after": new[name]})
				metadata_added = [new[name] for name in sorted(new.keys() - old.keys())]
				allowed = (
					{(dt, None, "field_order") for dt in before["columns"]}
					if label == "customize"
					else (
						{(dt, "naming_series", "options") for dt in ("Sales Invoice", "Payment Entry")}
						if label == "reload"
						else set()
					)
				)
				assert all((r["doc_type"], r["field_name"], r["property"]) in allowed for r in metadata_added)
			else:
				keys += ("setters",)
		hashes = {}
		for key in keys:
			assert before[key] == after[key], f"{label}: changed complete {key}"
			hashes[key] = hashlib.sha256(json.dumps(before[key], sort_keys=True).encode()).hexdigest()
		summary["preservation"] = [row for row in summary["preservation"] if row["stage"] != label]
		summary["preservation"].append(
			{
				"stage": label,
				"full_records_equal": True,
				"sha256": hashes,
				"metadata_added": metadata_added,
				"metadata_changed": metadata_changed,
			}
		)

	try:
		if resume:
			stable = read("lifecycle_before")
			after = read("after_customize")
			compare("customize", stable, after, True)
			stable = after
			if args.resume_after_reload or args.resume_after_migrate:
				after = read("after_reload")
				compare("reload", stable, after, True)
				stable = after
			if args.resume_after_migrate:
				after = read("after_migrate")
				compare("migrate", stable, after, True)
				stable = after
			label = (
				"resume_after_migrate"
				if args.resume_after_migrate
				else ("resume_after_reload" if args.resume_after_reload else "resume_readback")
			)
			compare(label, stable, audit(label), True)
		else:
			execute("prepare", "c3_probe.prepare")
			initial = audit("default")
			assert all(r["column"] == "decimal(21,9)" for r in initial["trace"][:5]), (
				"Fresh default precision required"
			)
			execute("preflight_control", "c3_probe.preflight_control")
			for index, phase in enumerate(("baseline", "source", "invoice", "payment", "ledger"), start=1):
				result = execute(f"phase_{phase}", "c3_probe.phase", {"label": phase})
				if phase == "baseline":
					assert result["cases"][0]["calculated_unit_price"] == 229999.79
					execute("payment_baseline", "c3_payment_probe.run", {"label": "baseline"})
				if phase == "ledger":
					assert not any(case["errors"] for case in result["cases"])
					assert result["cases"][3]["calculated_unit_price"] == 7359999.99
				before = audit(f"before_{index}")  # All native closes completed before capture.
				execute(f"precision_{index}", "c3_precision.run", {"site": SITE, "through": index})
				after = audit(f"after_{index}")  # No intervening business operation.
				compare(f"precision_{index}", before, after)
			execute("payment_revised", "c3_payment_probe.run", {"label": "revised"})
			stable = audit("lifecycle_before")
			for index in (1, 2):
				result = execute(f"idempotence_{index}", "c3_precision.run", {"site": SITE})
				assert result["changes"] == []
				after = audit(f"idempotence_after_{index}")
				compare(f"idempotence_{index}", stable, after, True)
		for label, method, command in (
			("customize", "c3_probe.customize", None),
			("reload", "c3_probe.resync", None),
			("migrate", None, ["migrate", "--skip-search-index"]),
		):
			if resume and (
				label == "customize"
				or (label == "reload" and (args.resume_after_reload or args.resume_after_migrate))
				or (label == "migrate" and args.resume_after_migrate)
			):
				continue
			execute(label, method, command=command)
			after = audit(f"after_{label}")
			compare(label, stable, after, True)
			stable = after
		execute("inspect_final", "c3_precision.inspect", {"site": SITE})
		for name, values in stable["snapshots"].items():
			doc = values["invoice"]
			if doc["posting_date"] == "2026-11-04" and doc["items"][0]["item_code"] == "SPIKE-001":
				execute(
					f"verify_{name}",
					"c3_verify.run",
					{"site": SITE, "invoice": name, "qty": doc["items"][0]["qty"]},
				)
		for name, values in stable["payments"].items():
			if values["payment"]["posting_date"] == "2026-11-06":
				execute("verify_payment", "c3_verify.payment", {"site": SITE, "name": name})
		summary["result"] = "local precision/lifecycle checks pass; C3 remains unaccepted"
	finally:
		(args.output / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
	main()
