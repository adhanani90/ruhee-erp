// C7 browser evidence harness (M1-05, PR #25). Spike code only; never deployed.
//
// Drives the real POS Awesome client (fork m1-c7-client-rate, built bundle) in
// headless Chromium: clicks, typed amounts, the client's own pricing, payment and
// submission code. It records what the screen shows, the outbound submit payload
// exactly as the client sent it, and the server's response. It never builds a
// payload itself. Saved documents and GL are read afterwards by the separate
// read-only verifier, store_rate_verify.py.
//
// Run (see store_rate_report.md, "Reproduce"):
//   PW_MODULE=<frontend>/node_modules/playwright/index.mjs SITE=<site> PORT=8021 \
//   OUT=<dir> node c7_browser.mjs <scenario> [...]
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";

const { chromium } = await import(process.env.PW_MODULE);
const SITE = process.env.SITE;
const PORT = process.env.PORT || "8021";
const BASE = `http://${SITE}:${PORT}`;
const OUT = process.env.OUT;
const PROFILE_DIR = process.env.PROFILE_DIR || `${OUT}/browser-profile`;
const SECRETS = JSON.parse(readFileSync(process.env.SECRETS, "utf8"));
mkdirSync(OUT, { recursive: true });

const log = (...args) => console.log(new Date().toISOString(), ...args);

export async function open(profileDir = PROFILE_DIR) {
  const ctx = await chromium.launchPersistentContext(profileDir, {
    headless: true,
    timezoneId: "Africa/Kinshasa",
    locale: "en-US",
    viewport: { width: 1600, height: 1000 },
    baseURL: BASE,
  });
  const page = ctx.pages()[0] || (await ctx.newPage());
  const trace = { http: [], console: [] };
  page.on("console", (m) => {
    if (m.type() === "error" && !/socket|404/.test(m.text()))
      trace.console.push(m.text().slice(0, 500));
  });
  page.on("request", (r) => {
    const url = r.url();
    if (!url.includes("/api/method/")) return;
    const method = url.split("/api/method/")[1].split("?")[0];
    if (
      !/submit_invoice|update_invoice|get_store_rate|resolve_exchange_rate/.test(
        method
      )
    )
      return;
    trace.http.push({
      at: new Date().toISOString(),
      kind: "request",
      method,
      body: decodeBody(r),
    });
  });
  page.on("response", async (r) => {
    const url = r.url();
    if (!url.includes("/api/method/")) return;
    const method = url.split("/api/method/")[1].split("?")[0];
    if (
      !/submit_invoice|update_invoice|get_store_rate|resolve_exchange_rate/.test(
        method
      ) &&
      r.status() < 400
    )
      return;
    let body = null;
    try {
      body = await r.json();
    } catch {
      body = null;
    }
    trace.http.push({
      at: new Date().toISOString(),
      kind: "response",
      method,
      status: r.status(),
      body: summarize(body),
    });
  });
  return { ctx, page, trace };
}

function decodeBody(request) {
  const raw = request.postData() || "";
  let fields = {};
  try {
    fields = JSON.parse(raw);
  } catch {
    fields = Object.fromEntries(new URLSearchParams(raw));
  }
  const out = {};
  for (const [key, value] of Object.entries(fields)) {
    try {
      out[key] = typeof value === "string" ? JSON.parse(value) : value;
    } catch {
      out[key] = value;
    }
  }
  return out;
}

function summarize(body) {
  if (!body) return body;
  const msg = body.message;
  const server = body._server_messages
    ? JSON.parse(body._server_messages).map((m) => JSON.parse(m).message)
    : undefined;
  if (msg && typeof msg === "object") {
    return {
      message: {
        name: msg.name,
        docstatus: msg.docstatus,
        status: msg.status,
        replayed: msg.replayed,
        conversion_rate: msg.conversion_rate,
        grand_total: msg.grand_total,
        ruhee_c7_rate: msg.ruhee_c7_rate,
        found: msg.found,
        base: msg.base,
        higher: msg.higher,
        exchange_rate: msg.exchange_rate,
      },
      server_messages: server,
    };
  }
  return { message: msg, exc_type: body.exc_type, server_messages: server };
}

export async function closeModals(page) {
  for (let i = 0; i < 5; i++) {
    const modal = page.locator(".modal.show");
    if (!(await modal.count())) return;
    await page.keyboard.press("Escape");
    await page.waitForTimeout(400);
    if (await modal.count()) {
      await modal
        .first()
        .locator(".btn-modal-close, button.btn-close")
        .first()
        .click({ force: true })
        .catch(() => {});
      await page.waitForTimeout(400);
    }
  }
}

export async function login(page) {
  await page.goto("/login", { waitUntil: "domcontentloaded" });
  return page.evaluate(
    async ({ usr, pwd }) =>
      fetch("/api/method/login", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ usr, pwd }),
      }).then((r) => r.status),
    { usr: SECRETS.user, pwd: SECRETS.password }
  );
}

export async function unlock(page) {
  await page.goto("/app/posapp", { waitUntil: "domcontentloaded" });
  await page.waitForFunction(
    () =>
      document.body.innerText.includes("TERMINAL LOCKED") ||
      document.body.innerText.includes("Invoice Items"),
    null,
    { timeout: 90000 }
  );
  await page.waitForTimeout(2500);
  await closeModals(page);
  if (
    !(await page.evaluate(() =>
      document.body.innerText.includes("TERMINAL LOCKED")
    ))
  )
    return;
  const who = page.getByText(SECRETS.user, { exact: true }).first();
  await who.waitFor({ timeout: 30000 });
  await who.click();
  const pin = page.locator("input[name=pos-terminal-unlock-pin]");
  await pin.waitFor({ timeout: 30000 });
  await page.waitForTimeout(500);
  await pin.click();
  await pin.fill("");
  await pin.pressSequentially(SECRETS.pin, { delay: 30 }); // auto-submits at the PIN's length
  await page.waitForTimeout(1000);
  await closeModals(page);
  await page.waitForFunction(
    () => !document.body.innerText.includes("TERMINAL LOCKED"),
    null,
    { timeout: 30000 }
  );
  await page.waitForTimeout(1500);
}

async function field(page, label) {
  return page.locator(`.v-field:has(label:text-is('${label}'))`).first();
}

export async function setCustomer(page, name) {
  const input = (await field(page, "Customer")).locator("input").first();
  await input.click({ force: true });
  await input.fill("");
  await input.pressSequentially(name, { delay: 30 });
  await page.waitForTimeout(2000);
  const option = page.getByRole("option").filter({ hasText: name }).first();
  await option.click();
  await page.waitForTimeout(1200);
}

export async function resetSale(page) {
  // Leftovers from an earlier failed sale are cancelled through the UI first.
  const empty = await page.evaluate(() =>
    document.body.innerText.includes("No items in cart")
  );
  if (empty) return;
  await page
    .getByRole("button", { name: /cancel sale/i })
    .first()
    .click();
  await page.waitForTimeout(1000);
  await confirmDialogs(page);
  await page.waitForFunction(
    () => document.body.innerText.includes("No items in cart"),
    null,
    { timeout: 15000 }
  );
}

export async function setCurrency(page, currency) {
  await (await field(page, "Currency")).click();
  await page.getByRole("option", { name: currency, exact: true }).click();
  await page.waitForTimeout(2500);
}

export async function addItem(page, code, label, qty = 1) {
  const search = (await field(page, "Search, scan or browse item"))
    .locator("input")
    .first();
  const row = page.getByText(label, { exact: true }).first();
  for (let attempt = 0; attempt < 6; attempt++) {
    // Empty search lists the whole (small) catalogue; typed search is the fallback.
    await search.click({ force: true });
    await search.fill("");
    await search.press("Escape").catch(() => {});
    if (attempt % 2) await search.pressSequentially(code, { delay: 20 });
    try {
      await row.waitFor({ timeout: 10000 });
      break;
    } catch {
      log("item not listed yet, retrying", code, attempt);
    }
  }
  await row.click();
  await page.waitForTimeout(2000);
  if (qty !== 1) {
    const qtyInput = page.locator("input[aria-label=Quantity]").last();
    await qtyInput.click();
    await qtyInput.fill(String(qty));
    await qtyInput.press("Tab");
    await page.waitForTimeout(2500);
  }
}

export async function readScreen(page) {
  return page.evaluate(() => {
    const fields = {};
    for (const f of document.querySelectorAll(".v-field")) {
      if (!f.offsetParent) continue;
      const label = f.querySelector("label")?.textContent?.trim();
      const input = f.querySelector("input");
      if (label && input) fields[label] = input.value;
    }
    const tables = [...document.querySelectorAll("table")]
      .filter((t) => t.offsetParent && t.innerText.includes("QTY"))
      .map((t) => t.innerText.replace(/\s+/g, " ").trim());
    const active = document.body.innerText.match(/ACTIVE SALE\s+([^\n]+)/);
    return {
      fields,
      cart: tables,
      active_sale_total: active ? active[1] : null,
    };
  });
}

export async function openPayment(page) {
  await page
    .getByRole("button", { name: /^\s*pay\s*$/i })
    .first()
    .click();
  await page.getByText("Payment Methods").first().waitFor({ timeout: 30000 });
  await page.waitForTimeout(3000);
  await closeModals(page);
}

function methodCard(page, mode) {
  return page
    .locator("div")
    .filter({ has: page.locator(`text="${mode}"`) })
    .filter({ hasText: "METHOD" })
    .filter({ hasText: "Tender Currency" })
    .last();
}

export async function pay(page, mode, tenderCurrency, amount) {
  // The method button puts the remaining amount on that method (client logic).
  await page.getByRole("button", { name: mode, exact: true }).first().click();
  await page.waitForTimeout(2500);
  const card = methodCard(page, mode);
  if (tenderCurrency) {
    const select = card
      .locator(".v-field:has(label:text-is('Tender Currency'))")
      .first();
    const shown = await select
      .locator("input")
      .first()
      .inputValue()
      .catch(() => "");
    if (shown !== tenderCurrency) {
      await select.click();
      await page
        .getByRole("option", { name: tenderCurrency, exact: true })
        .last()
        .click();
      await page.waitForTimeout(2500);
    }
  }
  if (amount !== undefined) {
    const input = card
      .locator(".v-field:has(label:text-is('Amount')) input")
      .first();
    await input.click();
    await input.fill("");
    await input.pressSequentially(String(amount), { delay: 20 });
    await input.press("Tab");
    await page.waitForTimeout(2500);
  }
}

export async function readPayment(page) {
  return page.evaluate(() => {
    const dialog =
      [...document.querySelectorAll(".v-overlay--active, .v-dialog")].find(
        (d) => d.innerText.includes("Payment Methods")
      ) || document.body;
    const pairs = (root) => {
      const out = {};
      for (const f of root.querySelectorAll(".v-field")) {
        const label = f.querySelector("label")?.textContent?.trim();
        const input = f.querySelector("input");
        if (label && input && !(label in out)) out[label] = input.value;
      }
      return out;
    };
    const methods = [];
    for (const card of dialog.querySelectorAll("div")) {
      const t = card.innerText || "";
      if (
        !/^METHOD\b/.test(t) ||
        !t.includes("Tender Currency") ||
        (t.match(/METHOD/g) || []).length > 1
      )
        continue;
      const equivalent = t.match(/Invoice equivalent:\s*([^\n]+)/);
      const lines = t
        .split("\n")
        .map((x) => x.trim())
        .filter(Boolean);
      methods.push({
        name: lines[1],
        ...pairs(card),
        invoice_equivalent: equivalent ? equivalent[1].trim() : null,
      });
    }
    const text = dialog.innerText;
    return {
      fields: pairs(dialog),
      base_difference:
        (text.match(/Base Difference[\s\S]*?(\$\s*[-\d.,]+)/) || [])[1] || null,
      methods: methods.filter(
        (m, i, all) => all.findIndex((x) => x.name === m.name) === i
      ),
    };
  });
}

export async function submit(page, trace) {
  const before = trace.http.length;
  await page
    .getByRole("button", { name: /^\s*submit\s*$/i })
    .first()
    .click();
  const deadline = Date.now() + 60000;
  while (Date.now() < deadline) {
    const done = trace.http
      .slice(before)
      .find(
        (h) => h.kind === "response" && h.method.endsWith("submit_invoice")
      );
    if (done) break;
    await page.waitForTimeout(500);
    await confirmDialogs(page);
  }
  await page.waitForTimeout(2500);
  const toasts = await page.evaluate(() =>
    [
      ...document.querySelectorAll(
        ".v-snackbar, .v-alert, .toast, [role=alert], [role=status]"
      ),
    ]
      .filter((e) => e.offsetParent)
      .map((e) => e.innerText.trim())
      .filter(Boolean)
  );
  const calls = trace.http.slice(before);
  const request = calls.find(
    (h) => h.kind === "request" && h.method.endsWith("submit_invoice")
  );
  const response = calls.find(
    (h) => h.kind === "response" && h.method.endsWith("submit_invoice")
  );
  return { request: request?.body || null, response: response || null, toasts };
}

async function confirmDialogs(page) {
  // Partial payment / credit confirmations raised by the client itself.
  for (const label of [
    /^\s*yes\s*$/i,
    /^\s*confirm\s*$/i,
    /^\s*continue\s*$/i,
    /^\s*ok\s*$/i,
  ]) {
    const button = page
      .locator(".v-overlay--active .v-card")
      .getByRole("button", { name: label });
    if (await button.count()) {
      await button
        .first()
        .click()
        .catch(() => {});
      await page.waitForTimeout(800);
    }
  }
}

export async function offlineQueue(page) {
  return page.evaluate(async () => {
    const open = (name) =>
      new Promise((resolve, reject) => {
        const req = indexedDB.open(name);
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => reject(req.error);
      });
    const out = {
      databases: (await indexedDB.databases?.()) || [],
      tables: {},
    };
    for (const meta of out.databases) {
      const db = await open(meta.name);
      for (const table of ["write_queue", "invoice_outbox"]) {
        if (!db.objectStoreNames.contains(table)) continue;
        out.tables[`${meta.name}.${table}`] = await new Promise((resolve) => {
          const tx = db.transaction(table, "readonly");
          const req = tx.objectStore(table).getAll();
          req.onsuccess = () =>
            resolve(
              req.result.map((row) => ({
                queue_id: row.queue_id,
                outbox_id: row.outbox_id,
                status: row.status,
                retry_count: row.retry_count,
                last_error: row.last_error,
                created_at: row.created_at,
                request_id:
                  row.idempotency_key ||
                  row.client_request_id ||
                  row.payload?.invoice?.posa_client_request_id,
                invoice:
                  row.payload?.invoice || row.invoice
                    ? (({
                        currency,
                        grand_total,
                        rounded_total,
                        ruhee_c7_rate,
                        ruhee_c7_base,
                        ruhee_c7_higher,
                        ruhee_c7_issued_at,
                        payments,
                        items,
                      }) => ({
                        currency,
                        grand_total,
                        rounded_total,
                        ruhee_c7_rate,
                        ruhee_c7_base,
                        ruhee_c7_higher,
                        ruhee_c7_issued_at,
                        items: (items || []).map((i) => ({
                          item_code: i.item_code,
                          qty: i.qty,
                          rate: i.rate,
                          ruhee_c7_usd_price: i.ruhee_c7_usd_price,
                        })),
                        payments: (payments || [])
                          .filter((p) => p.amount || p.posa_original_amount)
                          .map((p) => ({
                            mode_of_payment: p.mode_of_payment,
                            amount: p.amount,
                            posa_payment_currency: p.posa_payment_currency,
                            posa_original_amount: p.posa_original_amount,
                          })),
                      }))(row.payload?.invoice || row.invoice)
                    : null,
              }))
            );
          req.onerror = () => resolve([]);
        });
      }
      db.close();
    }
    out.local_storage_journal = Object.keys(localStorage).filter((k) =>
      k.startsWith("posa_invoice_intent_")
    );
    out.store_rate_cache = Object.keys(localStorage)
      .filter((k) => k.startsWith("posa_c7_store_rate::"))
      .map((k) => JSON.parse(localStorage.getItem(k)));
    return out;
  });
}

export function payloadSummary(body) {
  const inv = body?.invoice || body?.data || {};
  return {
    currency: inv.currency,
    pos_profile: inv.pos_profile,
    conversion_rate: inv.conversion_rate,
    posa_client_request_id: inv.posa_client_request_id,
    ruhee_c7_rate: inv.ruhee_c7_rate,
    ruhee_c7_base: inv.ruhee_c7_base,
    ruhee_c7_higher: inv.ruhee_c7_higher,
    ruhee_c7_issued_at: inv.ruhee_c7_issued_at,
    grand_total: inv.grand_total,
    rounded_total: inv.rounded_total,
    items: (inv.items || []).map((i) => ({
      item_code: i.item_code,
      qty: i.qty,
      price_list_rate: i.price_list_rate,
      rate: i.rate,
      amount: i.amount,
      ruhee_c7_usd_price: i.ruhee_c7_usd_price,
    })),
    payments: (inv.payments || [])
      .filter((p) => Number(p.amount) || Number(p.posa_original_amount))
      .map((p) => ({
        mode_of_payment: p.mode_of_payment,
        amount: p.amount,
        base_amount: p.base_amount,
        posa_payment_currency: p.posa_payment_currency,
        posa_original_amount: p.posa_original_amount,
        posa_exchange_rate: p.posa_exchange_rate,
        posa_rate_source: p.posa_rate_source,
      })),
  };
}

// ---------------------------------------------------------------- scenarios

const SALES = {
  // [bill currency, item code, item label, qty, method, tender currency, typed tender or undefined]
  c3_01: [
    "CDF",
    "SPIKE-001",
    "Spike Item 100 USD",
    1,
    "Cash CDF",
    "CDF",
    undefined,
  ],
  c3_02: [
    "CDF",
    "SPIKE-001",
    "Spike Item 100 USD",
    100,
    "Cash CDF",
    "CDF",
    undefined,
  ],
  c4: [
    "USD",
    "SPIKE-001",
    "Spike Item 100 USD",
    1,
    "Cash CDF",
    "CDF",
    undefined,
  ],
  c4_large: [
    "USD",
    "SPIKE-001",
    "Spike Item 100 USD",
    100,
    "Cash CDF",
    "CDF",
    undefined,
  ],
  c5: ["CDF", "SPIKE-001", "Spike Item 100 USD", 1, "Cash CDF", "CDF", 115000],
  line_3200: [
    "CDF",
    "C7-UNIT-3200",
    "C7 Unit 3200 USD",
    1,
    "Cash CDF",
    "CDF",
    undefined,
  ],
  diag_240k: [
    "USD",
    "SPIKE-001",
    "Spike Item 100 USD",
    1,
    "Cash CDF",
    "CDF",
    240000,
  ],
  b_cdf_bill_usd_tender: [
    "CDF",
    "SPIKE-001",
    "Spike Item 100 USD",
    1,
    "Cash USD",
    "USD",
    undefined,
  ],
};

export async function sale(session, name) {
  const [currency, code, label, qty, mode, tenderCurrency, amount] =
    SALES[name];
  const { page, trace } = session;
  await resetSale(page);
  await setCustomer(page, "Client A");
  await setCurrency(page, currency);
  await addItem(page, code, label, qty);
  const cart = await readScreen(page);
  await openPayment(page);
  await pay(page, mode, tenderCurrency, amount);
  const payment = await readPayment(page);
  await page.screenshot({ path: `${OUT}/${name}-payment.png` });
  const result = await submit(page, trace);
  await page.screenshot({ path: `${OUT}/${name}-after-submit.png` });
  return {
    scenario: name,
    inputs: {
      currency,
      item: code,
      qty,
      method: mode,
      tender_currency: tenderCurrency,
      typed_tender: amount ?? "client default",
    },
    displayed: { cart, payment },
    outbound: payloadSummary(result.request),
    outbound_raw_keys: result.request ? Object.keys(result.request) : null,
    response: result.response,
    toasts: result.toasts,
  };
}

async function main() {
  const scenarios = process.argv.slice(2);
  const session = await open();
  log("login", await login(session.page));
  await unlock(session.page);
  const results = [];
  for (const name of scenarios) {
    log("scenario", name);
    try {
      results.push(await sale(session, name));
    } catch (error) {
      await session.page
        .screenshot({ path: `${OUT}/${name}-error.png` })
        .catch(() => {});
      results.push({
        scenario: name,
        harness_error: String(error).slice(0, 800),
      });
    }
    results.at(-1).queue = await offlineQueue(session.page);
    writeFileSync(
      `${OUT}/${name}.json`,
      JSON.stringify(
        {
          ...results.at(-1),
          http: session.trace.http,
          console: session.trace.console,
        },
        null,
        1
      )
    );
    session.trace.http.length = 0;
    session.trace.console.length = 0;
    await unlock(session.page); // fresh screen for the next sale
  }
  await session.ctx.close();
  console.log(
    JSON.stringify(
      results.map((r) => ({
        scenario: r.scenario,
        error: r.harness_error,
        response: r.response?.body,
        payload: r.outbound,
      })),
      null,
      1
    )
  );
}

if (import.meta.url === `file://${process.argv[1]}`) {
  await main();
}
