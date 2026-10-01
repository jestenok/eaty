import re


def camel_to_snake(name: str) -> str:
    """'RecipeIngredient' -> 'recipe_ingredient'."""
    return re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()


def snake_to_kebab(name: str) -> str:
    return name.replace("_", "-")
