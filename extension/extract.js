// Finds orders in JSON that wolt.com loads for itself (order history, order details).
// Wolt's internal format isn't documented, so this looks for the shape of an order
// instead of exact field names: an object with an id, a status/payment time and a list
// of items that have names and quantities. Personal fields are dropped before sending.
// When that finds nothing, findOrderInPage reads the order off the order page itself.
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

  // Keys and value types of a JSON response, without the values: what the popup copies for
  // debugging when a response about orders came in but no order was recognized in it.
  function shapeOf(value, depth = 0) {
    if (Array.isArray(value)) return value.length ? [shapeOf(value[0], depth + 1), `×${value.length}`] : [];
    if (value && typeof value === "object") {
      if (depth > 8) return "{…}";
      const out = {};
      for (const [k, v] of Object.entries(value).slice(0, 60)) out[k] = shapeOf(v, depth + 1);
      return out;
    }
    return value === null ? "null" : typeof value;
  }

  // ---- The order page itself: wolt.com/<lang>/me/order-history/<id> ----
  // For when the order isn't in any JSON the page loads (or it's in a shape findOrders doesn't
  // know). Wolt's class names are generated, so rows are found by their text instead: an item
  // row is the smallest block around a "×N" count that also has a name, e.g.
  // "Молоко 3,2% 1л | 5,95 | ×1 | 5,95". Prices are in lari on the page and in tetri in the order.

  const ORDER_PAGE = /\/order-history\/([0-9a-z]{16,64})\/?$/i;
  const COUNT = /^[×✕x]\s*(\d+(?:[.,]\d+)?)$/i;
  const PRICE = /^[^\d\s]{0,3}\s?\d{1,6}(?:[.,]\d{1,2})?\s?[^\d\s]{0,3}$/;
  const PLACED = /(\d{1,2})\.(\d{1,2})\.(\d{4}),?\s+(\d{1,2}):(\d{2})/;   // "01.10.2026, 12:16"
  const CANCELLED_BADGE = /^(отмен[её]н|отклон[её]н|cancell?ed|rejected|refunded)/i;
  const LETTER = /\p{L}/u;
  const SKIP_TAGS = new Set(["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE", "TITLE"]);
  const FOLLOWING = 4; // Node.DOCUMENT_POSITION_FOLLOWING

  function orderIdFromPath(pathname) {
    const m = ORDER_PAGE.exec(pathname || "");
    return m ? m[1] : null;
  }

  function token(el) {
    return (el.textContent || "").replace(/\s+/g, " ").trim();
  }

  function ownText(el) {
    return [...el.childNodes].filter((n) => n.nodeType === 3).map((n) => n.textContent).join(" ").replace(/\s+/g, " ").trim();
  }

  // Elements that carry text themselves, in document order.
  function textElements(root) {
    return [root, ...root.querySelectorAll("*")].filter((el) => !SKIP_TAGS.has(el.tagName) && ownText(el));
  }

  const isCount = (t) => COUNT.test(t);
  const isPrice = (t) => !isCount(t) && PRICE.test(t);
  const isName = (t) => LETTER.test(t) && !isCount(t) && !isPrice(t);
  const number = (t) => Number(t.replace(/[^\d.,]/g, "").replace(",", "."));

  function rowOf(marker) {
    let el = marker.parentElement;
    for (let depth = 0; el && depth < 6; depth++, el = el.parentElement) {
      if (textElements(el).some((e) => e !== marker && !marker.contains(e) && isName(token(e)))) return el;
    }
    return null;
  }

  function itemFromRow(row, marker) {
    const els = textElements(row).filter((e) => e !== marker && !marker.contains(e));
    const nameEl = els.find((e) => isName(token(e)));
    if (!nameEl) return null;
    const name = nameEl.contains(marker) ? ownText(nameEl) : token(nameEl);
    const prices = els.filter((e) => !nameEl.contains(e) && isPrice(token(e))).map((e) => number(token(e)));
    const count = number(COUNT.exec(token(marker))[1]);
    const total = prices.length ? prices[prices.length - 1] : null;
    return {
      id: null,
      name,
      count: count > 0 ? count : 1,
      grams: null,
      price: total != null && Number.isFinite(total) ? Math.round(total * 100) : null,
    };
  }

  // The venue is the heading closest above the line with the order number.
  function venueAbove(el) {
    for (let a = el.parentElement, depth = 0; a && depth < 5; a = a.parentElement, depth++) {
      const heads = [...a.querySelectorAll("h1,h2,h3,h4,[role=heading]")].filter((h) => h.compareDocumentPosition(el) & FOLLOWING);
      if (heads.length) return token(heads[heads.length - 1]);
    }
    return "";
  }

  function findOrderInPage(doc, pathname) {
    const id = orderIdFromPath(pathname);
    if (!id || !doc.body) return null;
    const all = textElements(doc.body);

    const rows = new Map(); // row -> its count marker, or null if it has more than one
    for (const marker of all.filter((el) => isCount(token(el)))) {
      const row = rowOf(marker);
      if (row) rows.set(row, rows.has(row) ? null : marker);
    }
    const items = [];
    let firstRow = null;
    for (const [row, marker] of rows) {
      if (!marker || [...rows.keys()].some((r) => r !== row && row.contains(r))) continue;
      const item = itemFromRow(row, marker);
      if (!item) continue;
      items.push(item);
      firstRow = firstRow || row;
    }
    if (!items.length) return null;

    // Everything above the items, without the containers around them.
    const header = all.filter((el) => el.compareDocumentPosition(firstRow) === FOLLOWING);
    if (header.some((el) => CANCELLED_BADGE.test(token(el)))) return null;
    const placed = header.map((el) => PLACED.exec(token(el))).find(Boolean);
    const idEl = header.findLast((el) => token(el).includes(id));
    let orderedAt = null;
    if (placed) {
      const [, d, m, y, h, min] = placed.map(Number);
      orderedAt = new Date(y, m - 1, d, h, min).toISOString(); // the page shows local time
    }
    return { id, venue_name: idEl ? venueAbove(idEl) : "", ordered_at: orderedAt, total: null, status: "", items, raw: null };
  }

  const api = { findOrders, parseOrder, parseItem, shapeOf, orderIdFromPath, findOrderInPage };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  else root.EatyExtract = api;
})(globalThis);
