// Read the installed POS utility; no browser/site/cache mutation or app source edits.
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const source = new URL(
	"../../../posawesome/frontend/src/posapp/utils/erpnextCurrency.ts",
	import.meta.url,
);
const { priceListToSelectedCurrency } = await import(source.href);
const cases = [];
for (const conversion_rate of [0.000434783, 0.000434782609]) {
	for (const usd of [100, 3000, 3200]) {
		const raw = priceListToSelectedCurrency(
			{
				company: { default_currency: "USD" },
				selected_currency: "CDF",
				price_list_currency: "USD",
				conversion_rate,
				plc_conversion_rate: 1,
			},
			usd,
		);
		cases.push({
			conversion_rate,
			usd,
			raw,
			// These inputs are not ties: ordinary two-decimal rounding is unambiguous.
			line_at_two_decimals: Number(raw.toFixed(2)),
			exact_direct: usd * 2300,
		});
	}
}
assert.equal(cases[0].line_at_two_decimals, 229999.79);
assert.equal(cases[3].line_at_two_decimals, 230000);
assert.equal(cases[4].line_at_two_decimals, 6900000);
assert.equal(cases[5].line_at_two_decimals, 7359999.99);
const commits = Object.fromEntries(
	["frappe", "erpnext", "posawesome"].map((app) => [
		app,
		execFileSync("git", [
			"-C",
			fileURLToPath(new URL(`../../../${app}`, import.meta.url)),
			"rev-parse",
			"HEAD",
		])
			.toString()
			.trim(),
	]),
);
console.log(JSON.stringify({ browser_verified: false, commits, cases }, null, 2));
