// Finds orders in JSON that wolt.com loads for itself (order history, order details).
// Wolt's internal format isn't documented, so this looks for the shape of an order
// instead of exact field names: an object with an id, a status/payment time and a list
// of items that have names and quantities. Personal fields are dropped before sending.
(function (root) {
  "use strict";

  const ITEM_LISTS = ["items", "order_items", "basket_items", "purchase_items", "products"];
  const ORDER_MARKERS = ["status", "order_status", "delivery_status", "payment_time", "payment_status"];
  const CANCELLED = /cancel|reject|refund|fail/i;
  const PRIVATE = /address|phone|email|courier|location|coordinates|token|card|payment_method|user|customer|comment/i;

  function text(value) {
    if (value == null) return "";
    if (typeof value === "string" || typeof value === "number") return String(value);
    if (Array.isArray(value)) { // translations: [{lang: "ru", value: "…"}]
      const ru = value.find((v) => v && v.lang === "ru") || value[0];
      return ru ? text(ru.value != null ? ru.value : ru) : "";
    }
    if (typeof value === "object") return text(value.value || value.name || value.text || value.$oid);
    return "";
  }

  function first(obj, keys) {
    for (const k of keys) if (obj[k] != null && obj[k] !== "") return obj[k];
    return undefined;
  }

  function toNumber(value) {
    if (value && typeof value === "object") value = first(value, ["amount", "value", "grams"]);
    const n = Number(value);
    return Number.isFinite(n) ? n : null;
  }

  function parseItem(raw) {
    if (!raw || typeof raw !== "object") return null;
    const name = text(first(raw, ["name", "title", "item_name", "product_name"])).trim();
    if (!name) return null;
    const count = toNumber(first(raw, ["count", "quantity", "amount", "qty"]));
    return {
      id: text(first(raw, ["id", "item_id", "menu_item_id", "product_id"])) || null,
      name,
      count: count != null && count > 0 ? count : 1,
      grams: toNumber(first(raw, ["weight_in_grams", "grams", "weight", "selected_weight"])),
      price: toNumber(first(raw, ["end_amount", "total_price", "price", "total"])),
    };
  }

  function stripPrivate(node) {
    const out = {};
    for (const [k, v] of Object.entries(node)) if (!PRIVATE.test(k)) out[k] = v;
    return out;
  }

  function parseOrder(node) {
    const list = ITEM_LISTS.map((k) => node[k]).find((v) => Array.isArray(v) && v.length && typeof v[0] === "object");
    if (!list) return null;
    if (!ORDER_MARKERS.some((k) => k in node)) return null; // a basket, not an order
    const status = text(first(node, ["status", "order_status", "delivery_status"]));
    if (CANCELLED.test(status)) return null;
    const id = text(first(node, ["order_id", "purchase_id", "id", "_id"]));
    const items = list.map(parseItem).filter(Boolean);
    if (!id || !items.length) return null;
    const venue = node.venue || node.venue_info || {};
    return {
      id,
      venue_name: text(first(node, ["venue_name"]) || first(venue, ["name"])),
      ordered_at: first(node, ["payment_time", "creation_time", "created_at", "order_time", "delivery_time"]) || null,
      total: toNumber(first(node, ["total_price", "end_amount", "total", "price"])),
      status,
      items,
      raw: stripPrivate(node),
    };
  }

  function findOrders(json, limit = 50) {
    const found = new Map();
    const seen = new Set();
    (function walk(node, depth) {
      if (!node || typeof node !== "object" || depth > 14 || seen.has(node) || found.size >= limit) return;
      seen.add(node);
      if (Array.isArray(node)) { node.forEach((v) => walk(v, depth + 1)); return; }
      const order = parseOrder(node);
      if (order) { found.set(order.id, order); return; }
      Object.values(node).forEach((v) => walk(v, depth + 1));
    })(json, 0);
    return [...found.values()];
  }

  const api = { findOrders, parseOrder, parseItem };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.EatyExtract = api;
})(globalThis);
