from app.repositories.products import ProductRepository
from app.schemas.product import ProductIn, ProductOut
from core.error import ConflictError
from core.service import BaseService


class ProductService(BaseService[ProductRepository]):
    """Products we buy in Wolt: what recipes, the shopping list and the pantry count in."""

    async def list(self) -> list[ProductOut]:
        return [ProductOut.model_validate(p) for p in await self.repository.all()]

    async def put(self, key: str, dto: ProductIn) -> ProductOut:
        """Add a product or change how it's searched and matched in Wolt."""
        existing = await self.repository.get(key)
        if existing and existing.base_unit != dto.base_unit:
            raise ConflictError(
                f"Единицу продукта «{key}» поменять нельзя: в ней записаны рецепты и запасы дома")
        await self.repository.upsert(dict(key=key, **dto.model_dump()), conflict=["key"])
        return ProductOut(key=key, **dto.model_dump())
