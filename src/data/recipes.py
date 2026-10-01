"""Built-in products, recipes and the default week plan.

Recipes are for 2 portions (one meal for two). Kitchen: stove + air fryer, no oven.
Amounts are in the product's base unit: grams, millilitres or pieces.
"""

from __future__ import annotations

import datetime as dt

WM = "wolt-market-batumi"
RED = "red-market-meat-store"

# key, name, base_unit, venue, search query, name regex, exclude regex,
# preferred Wolt item: (id, name, price in tetri, unit_info, weight step in grams)
PRODUCTS = [
    dict(key="chicken_legs", name="Куриные окорочка", base_unit="g", venue=RED, search_q="курица",
         match=r"окороч|куриная ножка|ножк[аи] кур", exclude=r"копч|барбекю|гриль|рулет",
         preferred=("c71af1cad259d733a9205145", "Куриная ножка", 2074, None, 1100)),
    dict(key="beef_mince", name="Говяжий фарш", base_unit="g", venue=RED, search_q="фарш",
         match=r"говяж\w* фарш|фарш\w* говяж", exclude=r"заморож|котлет",
         preferred=("0d23081cb50c6a71acb17636", "Говяжий фарш", 3416, None, 300)),
    dict(key="eggs", name="Яйца", base_unit="pcs", venue=WM, search_q="яйца",
         match=r"яйц|яичн|кумыс", exclude=r"перепел|шоколад|киндер|лапш|майонез|макарон",
         preferred=("66a0dd8b9dfb545d3cc3f96f", "Яйца кумысные, картонный рынок, I категория, 15 шт.", 895, "15 шт", None)),
    dict(key="milk", name="Молоко", base_unit="ml", venue=WM, search_q="молоко",
         match=r"^молоко|молоко \d", exclude=r"сгущ|шоколад|кокос|миндал|овсян|соев|рисов|детск|сух|коктейл|безлакт",
         preferred=("67b11a65b43072db0d097720", "Молоко 3,2% 1л", 595, "1 л", None)),
    dict(key="cheese", name="Сыр", base_unit="g", venue=WM, search_q="сыр",
         match=r"сыр", exclude=r"плавлен|сливочн|творож|сырок|глазир|продукт|закуск|палоч|соус|чипс|крекер|ломтик|нарезан",
         preferred=("66d9ac1d5116df1f4f1cee3f", "Сыр Sanebo заводской 250г (в)", 1295, "250 г", None)),
    dict(key="potato", name="Картофель", base_unit="g", venue=WM, search_q="картофель",
         match=r"^картофель", exclude=r"сладк|чипс|фри|пюре|крахмал|ньокки|заморож|очищен",
         preferred=("67c58479c847018e6542e6c5", "Картофель (ц), ~1000 г", 165, "1 кг", 1000)),
    dict(key="carrot", name="Морковь", base_unit="g", venue=WM, search_q="морковь",
         match=r"^морковь", exclude=r"корейск|сок|заморож|салат",
         preferred=("66d9ac1d5116df1f4f1ceec9", "Морковь Имери 500г (в)", 330, "500 г", None)),
    dict(key="onion", name="Лук репчатый", base_unit="g", venue=WM, search_q="лук",
         match=r"^лук", exclude=r"зелен|порей|жарен|сушен|чипс|шалот|размягч",
         preferred=("66d9ac1d5116df1f4f1ceec5", "Лук Имери белый 500г (c)", 255, "500 г", None)),
    dict(key="garlic", name="Чеснок", base_unit="g", venue=WM, search_q="чеснок",
         match=r"чеснок", exclude=r"сушен|молот|гранул|соус|паста|чипс|сухари|хлебц|песто|смесь|измельч",
         preferred=("66d9ac1d5116df1f4f1ceecf", "Имерский чеснок 250г (в)", 430, "250 г", None)),
    dict(key="banana", name="Бананы", base_unit="g", venue=WM, search_q="банан",
         match=r"^банан", exclude=r"чипс|сушен|сублим|йогурт|пюре|сок|десерт",
         preferred=("67c585b1ac0b3c4daeab8b7b", "Банан, 1 кг", 540, "1 кг", None)),
    dict(key="rice", name="Рис пропаренный", base_unit="g", venue=WM, search_q="рис",
         match=r"^рис", exclude=r"хлопь|лапш|бумаг|уксус|мук|крекер|молок|пудинг|вафл|суши|басмати|жасмин|круглозерн",
         preferred=("ccf825558df270a7e4d3cf87", "Рис Сэвил пропаренный 800 г", 480, "800 г", None)),
    dict(key="pasta", name="Макароны", base_unit="g", venue=WM, search_q="спагетти",
         match=r"спагетти|макарон|пенне|фузилли|паста ", exclude=r"соус|песто|томат|рисов|лапш|без глютен|ньокки|морков",
         preferred=("65d2720d97cb939f1539dbc2", "Спагетти Arrighi Pasta 500 г", 379, "500 г", None)),
    dict(key="tomatoes_canned", name="Томаты консервированные", base_unit="g", venue=WM, search_q="томаты",
         match=r"(томат|помидор)\w* (нарезан|очищен|резан|консерв|в собств)|(нарезан|очищен|консерв)\w* (томат|помидор)",
         exclude=r"паста|кетчуп|сок|соус|черри|вялен|маринов",
         preferred=("880f7bdbb1e9f4ce9edd2863", "Кикнос помидоры нарезанные 400 гр", 450, "400 г", None)),
    dict(key="oats", name="Овсяные хлопья", base_unit="g", venue=WM, search_q="овсяные хлопья",
         match=r"овсян\w* хлопь|хлопья овсян|геркулес", exclude=r"печен|батончик|быстр|отруб|гранол|мюсли",
         preferred=("66a0dd8b9dfb545d3cc3fc81", "Овсяные хлопья Ярмарка 600г", 595, "600 г", None)),
    dict(key="bread", name="Хлеб", base_unit="g", venue=WM, search_q="хлеб",
         match=r"хлеб|выпечк", exclude=r"хрустящ|хлебц|сухар|панир|гренк|крекер|лаваш|тортил",
         preferred=("66a0dd8a9dfb545d3cc3f029", "Бутерброд с литовской выпечкой 600г", 295, "600 г", None)),
]


def ing(name, key=None, amount=None, unit=None, text="", note=""):
    return dict(name=name, product_key=key, amount=amount, unit=unit, text_amount=text, note=note)


def step(text, minutes=None, heat=""):
    return dict(text=text, timer_seconds=round(minutes * 60) if minutes else None, heat=heat)


RECIPES = [
    dict(
        slug="chicken-legs-air-fryer", title="Окорочка с картошкой в аэрогриле", appliance="air_fryer",
        batch_note="На ×2 готовь в два захода подряд: в корзину влезает 2 порции.",
        ingredients=[
            ing("Куриные окорочка", "chicken_legs", 650, "g", note="2 шт"),
            ing("Картофель", "potato", 600, "g", note="4–5 шт"),
            ing("Морковь", "carrot", 100, "g", note="1 шт"),
            ing("Лук", "onion", 60, "g", note="½ луковицы"),
            ing("Чеснок", "garlic", 10, "g", note="2 зубчика"),
            ing("Масло", text="1,5 ст. л."),
            ing("Соль, перец, паприка", text="по вкусу"),
        ],
        steps=[
            step("Окорочка разрезать по суставу на бедро и голень. Натереть солью, паприкой, давленым чесноком и ½ ст. л. масла."),
            step("Картошку нарезать дольками, морковь кружками, лук крупно. Перемешать с 1 ст. л. масла, солью, перцем и паприкой."),
            step("Овощи в корзину, курицу сверху кожей вверх. Запекать.", 15, "190 °C"),
            step("Встряхнуть корзину, чтобы овощи перемешались. Запекать дальше.", 17, "190 °C"),
            step("Проверить ножом у кости: сок прозрачный — готово. Если розовый — ещё немного.", 5, "190 °C"),
        ],
    ),
    dict(
        slug="bolognese", title="Макароны болоньезе", appliance="stove",
        batch_note="На ×2 всё в 2 раза больше: сковорода побольше, воды для макарон 3 л.",
        ingredients=[
            ing("Фарш говяжий", "beef_mince", 300, "g"),
            ing("Макароны", "pasta", 200, "g"),
            ing("Томаты консервированные", "tomatoes_canned", 400, "g", note="1 банка"),
            ing("Лук", "onion", 60, "g", note="½ луковицы"),
            ing("Морковь", "carrot", 60, "g", note="½ шт"),
            ing("Чеснок", "garlic", 10, "g", note="2 зубчика"),
            ing("Сыр", "cheese", 50, "g"),
            ing("Масло", text="1 ст. л."),
            ing("Соль, перец", text="по вкусу"),
        ],
        steps=[
            step("Поставить кастрюлю с 2 л воды на сильный огонь, посолить. Пока закипает — режь овощи."),
            step("Лук и морковь мелко порезать, обжарить на масле.", 5, "средний огонь"),
            step("Добавить фарш и жарить, разбивая лопаткой.", 7, "средний огонь"),
            step("Добавить томаты, чеснок, соль, перец. Тушить под крышкой.", 12, "слабый огонь"),
            step("Макароны в кипящую воду. Время смотри на пачке, обычно 9 минут.", 9, "сильный огонь"),
            step("Слить воду, смешать макароны с соусом, сверху тёртый сыр."),
        ],
    ),
    dict(
        slug="plov", title="Плов с курицей", appliance="stove",
        batch_note="На ×2 нужна кастрюля 3–4 л и в 2 раза больше всего, время то же.",
        ingredients=[
            ing("Куриные окорочка", "chicken_legs", 400, "g", note="кусками"),
            ing("Рис пропаренный", "rice", 200, "g"),
            ing("Морковь", "carrot", 150, "g", note="1–2 шт"),
            ing("Лук", "onion", 120, "g", note="1 шт"),
            ing("Чеснок", "garlic", 25, "g", note="½ головки"),
            ing("Масло", text="2 ст. л."),
            ing("Зира", text="½ ч. л."),
            ing("Соль", text="по вкусу"),
            ing("Кипяток", text="~400 мл"),
        ],
        steps=[
            step("Курицу порезать кусками, обжарить в кастрюле с толстым дном до корочки.", 8, "сильный огонь"),
            step("Добавить лук.", 5, "средний огонь"),
            step("Добавить морковь соломкой.", 5, "средний огонь"),
            step("Посолить, добавить зиру. Сверху ровным слоем промытый рис, воткнуть чеснок, залить кипятком на 1,5 см выше риса. Варить без крышки, пока вода не уйдёт в рис.", 10, "средний огонь"),
            step("Сделать ножом несколько дырок до дна, накрыть крышкой.", 20, "минимальный огонь"),
            step("Не открывая, дать постоять, потом перемешать.", 5),
        ],
    ),
    dict(
        slug="shakshuka", title="Шакшука", appliance="stove",
        ingredients=[
            ing("Яйца", "eggs", 5, "pcs"),
            ing("Томаты консервированные", "tomatoes_canned", 400, "g", note="1 банка"),
            ing("Лук", "onion", 120, "g", note="1 шт"),
            ing("Хлеб", "bread", 150, "g"),
            ing("Масло", text="1 ст. л."),
            ing("Паприка, соль", text="по вкусу"),
        ],
        steps=[
            step("Лук мелко, обжарить на масле.", 4, "средний огонь"),
            step("Добавить томаты и паприку, посолить, тушить.", 6, "средний огонь"),
            step("Сделать лунки, вбить яйца, накрыть крышкой — пока белок не схватится.", 5, "слабый огонь"),
        ],
    ),
    dict(
        slug="oatmeal", title="Овсянка с бананом", appliance="stove",
        ingredients=[
            ing("Овсяные хлопья", "oats", 140, "g"),
            ing("Молоко", "milk", 400, "ml"),
            ing("Бананы", "banana", 300, "g", note="2 шт"),
            ing("Соль", text="щепотка"),
        ],
        steps=[
            step("Молоко, хлопья и щепотку соли в кастрюлю, довести до кипения, помешивая.", 3, "средний огонь"),
            step("Варить, иногда помешивая.", 5, "слабый огонь"),
            step("Разложить по тарелкам, сверху нарезанный банан."),
        ],
    ),
    dict(
        slug="fried-eggs", title="Яичница с хлебом", appliance="stove",
        ingredients=[
            ing("Яйца", "eggs", 5, "pcs"),
            ing("Хлеб", "bread", 150, "g"),
            ing("Масло", text="1 ст. л."),
            ing("Соль", text="по вкусу"),
        ],
        steps=[
            step("Прогреть сковороду с маслом.", 1, "средний огонь"),
            step("Разбить яйца на сковороду, посолить. Жарить, пока белок не станет белым.", 4, "средний огонь"),
        ],
    ),
    dict(
        slug="omelette", title="Омлет с сыром", appliance="stove",
        ingredients=[
            ing("Яйца", "eggs", 5, "pcs"),
            ing("Молоко", "milk", 50, "ml", note="3 ст. л."),
            ing("Сыр", "cheese", 50, "g"),
            ing("Хлеб", "bread", 100, "g"),
            ing("Масло", text="1 ст. л."),
            ing("Соль", text="щепотка"),
        ],
        steps=[
            step("Разбить яйца в миску, добавить молоко и соль, взбить вилкой до однородности. Сыр натереть."),
            step("Прогреть сковороду с маслом.", 1, "средний огонь"),
            step("Вылить яйца и не мешать, пока края не схватятся.", 2, "чуть ниже среднего"),
            step("Посыпать сыром, накрыть крышкой. Готов, когда верх не жидкий.", 4, "чуть ниже среднего"),
            step("Разрезать пополам — две порции."),
        ],
    ),
]

# Day offset from the plan start -> {meal: (recipe slug or None, multiplier, note)}.
# Dinner is cooked x2: the second half is tomorrow's lunch.
WEEK_TEMPLATE = [
    {"breakfast": ("oatmeal", 1, ""), "lunch": ("omelette", 1, ""), "dinner": ("chicken-legs-air-fryer", 2, "половина — на обед завтра")},
    {"breakfast": ("fried-eggs", 1, ""), "lunch": (None, 1, "Окорочка со вчера"), "dinner": ("bolognese", 2, "половина — на обед завтра")},
    {"breakfast": ("oatmeal", 1, ""), "lunch": (None, 1, "Болоньезе со вчера"), "dinner": ("plov", 2, "половина — на обед завтра")},
    {"breakfast": ("fried-eggs", 1, ""), "lunch": (None, 1, "Плов со вчера"), "dinner": ("shakshuka", 1, "")},
    {"breakfast": ("oatmeal", 1, ""), "lunch": ("omelette", 1, ""), "dinner": ("chicken-legs-air-fryer", 2, "половина — на обед завтра")},
    {"breakfast": ("fried-eggs", 1, ""), "lunch": (None, 1, "Окорочка со вчера"), "dinner": ("bolognese", 2, "половина — на обед завтра")},
    {"breakfast": ("oatmeal", 1, ""), "lunch": (None, 1, "Болоньезе со вчера"), "dinner": ("plov", 2, "половина — на обед завтра")},
]


def default_week(start: dt.date, recipe_ids: dict[str, int]) -> list[dict]:
    """Rows of the default 7-day menu starting at `start`, ready for MealPlan inserts."""
    return [
        dict(day=start + dt.timedelta(days=offset), meal=meal,
             recipe_id=recipe_ids.get(slug) if slug else None, multiplier=multiplier, note=note)
        for offset, meals in enumerate(WEEK_TEMPLATE)
        for meal, (slug, multiplier, note) in meals.items()
    ]
