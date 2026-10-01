// node --test tests/extract.test.mjs — the order finder of the Chrome extension.
import { test } from "node:test";
import assert from "node:assert/strict";
import { createRequire } from "node:module";

const { findOrders } = createRequire(import.meta.url)("../extension/extract.js");

const order = {
  order_id: "abc123",
  status: "delivered",
  payment_time: { $date: 1790848000000 },
  venue_name: "Wolt Market Batumi",
  total_price: 7244,
  delivery_address: "41a Angisa Street",
  phone_number: "+995 000",
  items: [
    { id: "66a0dd8b9dfb545d3cc3f96f", name: "Яйца 15 шт.", count: 1, end_amount: 895 },
    { id: "67c58479c847018e6542e6c5", name: [{ lang: "ru", value: "Картофель" }], count: 2, end_amount: 330 },
  ],
};

test("finds an order nested anywhere and normalizes it", () => {
  const [found] = findOrders({ data: { page: [{ widgets: [order] }] } });
  assert.equal(found.id, "abc123");
  assert.equal(found.venue_name, "Wolt Market Batumi");
  assert.deepEqual(found.items.map((i) => [i.name, i.count, i.price]), [["Яйца 15 шт.", 1, 895], ["Картофель", 2, 330]]);
});

test("drops personal fields from the raw copy", () => {
  const [found] = findOrders(order);
  assert.ok(!("delivery_address" in found.raw));
  assert.ok(!("phone_number" in found.raw));
  assert.ok("items" in found.raw);
});

test("ignores baskets and cancelled orders", () => {
  const basket = { id: "b1", items: order.items };
  assert.deepEqual(findOrders(basket), []);
  assert.deepEqual(findOrders({ ...order, status: "cancelled" }), []);
});

test("deduplicates the same order seen twice", () => {
  assert.equal(findOrders([order, { copy: order }]).length, 1);
});

test("keeps what tells a store from a restaurant", () => {
  const [found] = findOrders({ ...order, venue: { name: "Wolt Market Batumi", url: "https://wolt.com/ru/geo/batumi/venue/wolt-market-batumi", product_line: "grocery" } });
  assert.equal(found.venue_url, "https://wolt.com/ru/geo/batumi/venue/wolt-market-batumi");
  assert.equal(found.product_line, "grocery");
});
