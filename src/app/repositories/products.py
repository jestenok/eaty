from app.models import Product
from core.repository import BaseRepository


class ProductRepository(BaseRepository[Product]):
    model = Product

    async def all(self) -> list[Product]:
        return await self.find(order_by=[Product.name])
