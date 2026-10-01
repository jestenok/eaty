"""recipe book

Revision ID: 72cd0f3e9a80
Revises: 525a0bd9e5e5
Create Date: 2026-10-01 12:38:06.587766

Recipes, products and the standard week used to be Python constants written over the
database on every start. Now the database is the source of truth: this migration loads the
book once from data/recipe_book.json, after that recipes and products are edited through
/api/v1/recipes and /api/v1/products. Recipes are matched by slug, so the ones that were
already there keep their ids (and the meal plan that points at them).

Downgrade leaves the data alone: the rows are valid for the previous schema too.
"""
import json
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import insert


# revision identifiers, used by Alembic.
revision: str = '72cd0f3e9a80'
down_revision: Union[str, Sequence[str], None] = '525a0bd9e5e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

BOOK = Path(__file__).resolve().parents[1] / "data" / "recipe_book.json"

# Tables as they are at this revision (not the app's models, which keep changing).
product = sa.table(
    "product", sa.column("key", sa.String), sa.column("name", sa.Text), sa.column("base_unit", sa.String),
    sa.column("venue_slug", sa.Text), sa.column("search_q", sa.Text), sa.column("match_re", sa.Text),
    sa.column("exclude_re", sa.Text))
wolt_item = sa.table(
    "wolt_item", sa.column("id", sa.String), sa.column("venue_slug", sa.Text), sa.column("name", sa.Text),
    sa.column("product_key", sa.String), sa.column("price", sa.Integer), sa.column("pack_amount", sa.Numeric),
    sa.column("weight_step_g", sa.Integer), sa.column("preferred", sa.Boolean))
recipe = sa.table(
    "recipe", sa.column("id", sa.Integer), sa.column("slug", sa.String), sa.column("title", sa.Text),
    sa.column("category", sa.String), sa.column("appliance", sa.String), sa.column("batch_note", sa.Text),
    sa.column("meals", postgresql.ARRAY(sa.String)))
recipe_ingredient = sa.table(
    "recipe_ingredient", sa.column("recipe_id", sa.Integer), sa.column("position", sa.Integer),
    sa.column("name", sa.Text), sa.column("product_key", sa.String), sa.column("amount", sa.Numeric),
    sa.column("unit", sa.String), sa.column("text_amount", sa.Text), sa.column("note", sa.Text))
recipe_step = sa.table(
    "recipe_step", sa.column("recipe_id", sa.Integer), sa.column("position", sa.Integer), sa.column("text", sa.Text),
    sa.column("timer_seconds", sa.Integer), sa.column("heat", sa.Text))
week_template = sa.table(
    "week_template", sa.column("day_offset", sa.Integer), sa.column("meal", sa.String),
    sa.column("recipe_id", sa.Integer), sa.column("multiplier", sa.Numeric), sa.column("note", sa.Text))


def upsert(table, rows, key, update=None):
    stmt = insert(table).values(rows)
    columns = update if update is not None else [c for c in rows[0] if c != key]
    return stmt.on_conflict_do_update(index_elements=[key], set_={c: stmt.excluded[c] for c in columns})


def upgrade() -> None:
    """Load the recipe book."""
    book = json.loads(BOOK.read_text(encoding="utf-8"))
    conn = op.get_bind()

    conn.execute(upsert(product, book["products"], "key"))
    # Favourite items are inserted once; prices of the ones already there come from catalog refreshes.
    conn.execute(upsert(wolt_item, [{**i, "preferred": True} for i in book["wolt_items"]], "id",
                        update=["preferred", "product_key"]))

    heads = [{k: r[k] for k in ("slug", "title", "category", "appliance", "batch_note", "meals")} for r in book["recipes"]]
    ids = dict(conn.execute(upsert(recipe, heads, "slug").returning(recipe.c.slug, recipe.c.id)).all())
    conn.execute(recipe_ingredient.delete().where(recipe_ingredient.c.recipe_id.in_(ids.values())))
    conn.execute(recipe_step.delete().where(recipe_step.c.recipe_id.in_(ids.values())))
    conn.execute(recipe_ingredient.insert(), [
        dict(recipe_id=ids[r["slug"]], position=pos, name=i["name"], product_key=i.get("product_key"),
             amount=i.get("amount"), unit=i.get("unit"), text_amount=i.get("text_amount", ""), note=i.get("note", ""))
        for r in book["recipes"] for pos, i in enumerate(r["ingredients"])])
    conn.execute(recipe_step.insert(), [
        dict(recipe_id=ids[r["slug"]], position=pos, text=s["text"], timer_seconds=s.get("timer_seconds"),
             heat=s.get("heat", ""))
        for r in book["recipes"] for pos, s in enumerate(r["steps"])])

    conn.execute(insert(week_template).values([
        dict(day_offset=w["day_offset"], meal=w["meal"], recipe_id=ids.get(w["recipe_slug"]),
             multiplier=w["multiplier"], note=w["note"])
        for w in book["week_template"]]).on_conflict_do_nothing())


def downgrade() -> None:
    """Nothing to undo: products and recipes stay, the week template goes with its table."""
