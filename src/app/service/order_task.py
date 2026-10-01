"""The shopping list of a week menu as a task for whoever orders it in Wolt (Claude in a
browser, or you): stores, items with links and how many to put in the cart, and the rules."""

from __future__ import annotations

import datetime as dt

from app.schemas.shopping import ShoppingListOut

MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня",
          "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def money(tetri: int) -> str:
    return f"{tetri / 100:.2f}".replace(".", ",") + " ₾"


def period(first: dt.date, last: dt.date) -> str:
    """'2–8 октября', '29 сентября – 5 октября'."""
    if first.month == last.month:
        return f"{first.day}–{last.day} {MONTHS[last.month - 1]}"
    return f"{first.day} {MONTHS[first.month - 1]} – {last.day} {MONTHS[last.month - 1]}"


def order_task(first: dt.date, last: dt.date, shopping: ShoppingListOut) -> str:
    title = f"Закажи в Wolt продукты для меню eaty на {period(first, last)}."
    if not shopping.stores and not shopping.not_found:
        return f"{title}\nДокупать ничего не нужно: всё уже дома."

    lines = [title, ""]
    if shopping.stores:
        lines.append(f"Магазинов: {len(shopping.stores)}, каждый — отдельный заказ. "
                     f"Товары на сумму около {money(shopping.total)}, без доставки.")
    for n, store in enumerate(shopping.stores, 1):
        lines += ["", f"{n}. {store.name} — {store.url} (≈ {money(store.total)})"]
        for line in store.lines:
            item = line.item
            pack = (f"на развес, шаг {item.pack}, {money(item.price)} за шаг" if item.by_weight
                    else f"{item.pack}, {money(item.price)}")
            lines.append(f"   - {line.packs} × {item.name} ({pack}) — для «{line.product}», нужно {line.to_buy}"
                         f" — {item.url}")
    if shopping.not_found:
        lines += ["", "Этого нет в каталоге eaty, найди сам в тех же магазинах:"]
        lines += [f"   - {line.product}: нужно {line.to_buy or line.need}" for line in shopping.not_found]
    lines += [
        "",
        "Как заказывать:",
        "- Открой ссылку товара и положи в корзину указанное количество. Товар на развес добавляй шагами:"
        " «2 ×» значит два шага.",
        "- Если товара нет, возьми похожий по размеру и составу (не «продукт», не копчёный) и запомни замену.",
        "- Адрес доставки и способ оплаты не меняй.",
        "- Перед оплатой покажи мне корзины, итог с доставкой и замены и жди моего «да».",
        "- После оплаты открой заказ в истории (https://wolt.com/ru/me/order-history): расширение eaty"
        " само заберёт его, продукты попадут в «Дома», а меню станет «Заказано».",
    ]
    return "\n".join(lines)
