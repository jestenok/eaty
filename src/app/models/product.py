from core.db import Base, CheckConstraint, Mp, String, Text, mc


class Product(Base):
    """Something we buy in Wolt and keep at home: 'chicken_legs', 'eggs'…"""

    key: Mp[str] = mc(String(64), primary_key=True)
    name: Mp[str] = mc(Text)
    base_unit: Mp[str] = mc(String(3))                      # g | ml | pcs
    venue_slug: Mp[str] = mc(Text)                          # the store we normally buy it in
    search_q: Mp[str] = mc(Text)                            # query for the Wolt catalog search
    match_re: Mp[str] = mc(Text)                            # item names that count as this product
    exclude_re: Mp[str] = mc(Text, server_default="")

    __table_args__ = (CheckConstraint("base_unit in ('g', 'ml', 'pcs')", name="base_unit"),)
