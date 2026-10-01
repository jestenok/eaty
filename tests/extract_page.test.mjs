// node --test tests/extract_page.test.mjs — reading an order off the wolt.com order page.
// Runs extension/extract.js in Chromium via Playwright (NODE_PATH=$(npm root -g) for a global
// install); skipped when Playwright isn't there.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";
import { readFileSync } from "node:fs";

let chromium = null;
try {
  ({ chromium } = createRequire(import.meta.url)("playwright"));
} catch (_) { /* skipped below */ }
const skip = !chromium && "needs playwright";

const extract = readFileSync(new URL("../extension/extract.js", import.meta.url), "utf8");
const fixture = readFileSync(new URL("./fixtures/wolt_order_page.html", import.meta.url), "utf8");
const PATH = "/ru/me/order-history/6abe16f7eccfcf01484147c4";

async function readOrder(html, path = PATH) {
  const browser = await chromium.launch();
  try {
    const page = await (await browser.newContext({ timezoneId: "Asia/Tbilisi" })).newPage();
    await page.setContent(html);
    await page.waitForSelector("li");
    await page.addScriptTag({ content: extract });
    return await page.evaluate((p) => window.EatyExtract.findOrderInPage(document, p), path);
  } finally {
    await browser.close();
  }
}

test("reads the order off the order page", { skip }, async () => {
  const order = await readOrder(fixture);
  assert.equal(order.id, "6abe16f7eccfcf01484147c4");
  assert.equal(order.venue_name, "Wolt Market Batumi");
  assert.equal(order.ordered_at, "2026-10-01T08:16:00.000Z"); // 12:16 in Batumi
  assert.equal(order.items.length, 11);
  assert.deepEqual(order.items.slice(0, 2).map((i) => [i.name, i.count, i.price]), [
    ["მილა რძე 3.2% 1ლ", 1, 595],
    ["კუმისი კვერცხი მუყაოს მარკეტი I კატეგორია 15ც", 1, 859],
  ]);
  assert.deepEqual(order.items.filter((i) => i.count > 1).map((i) => [i.name, i.count, i.price]), [
    ["იმერი სტაფილო 500გრ (ქ)", 2, 660],
    ["კიკნოსი დაჭრილი პომიდორი 400გრ", 2, 900],
  ]);
  assert.ok(order.items.every((i) => i.id === null && i.grams === null));
});

test("skips cancelled orders and pages that aren't an order", { skip }, async () => {
  assert.equal(await readOrder(fixture.replace('STATUS = "Доставлен"', 'STATUS = "Отменён"')), null);
  assert.equal(await readOrder(fixture, "/ru/me/order-history"), null);
});
