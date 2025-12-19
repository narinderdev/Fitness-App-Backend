from datetime import datetime
import httpx

from app.models.nutrition import FoodItem

BASE_URL = "https://world.openfoodfacts.org/api/v0/product/{barcode}.json"


def _to_float(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).split()[0])
    except (ValueError, TypeError):
        digits = "".join(ch for ch in str(value) if ch.isdigit() or ch in {".", "-"})
        return float(digits) if digits else None


async def fetch_product(barcode: str) -> dict | None:
    headers = {"User-Agent": "FitnessAppBackend/1.0"}
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.get(BASE_URL.format(barcode=barcode), headers=headers)
        response.raise_for_status()
        payload = response.json()
    if payload.get("status") != 1:
        return None
    return payload.get("product")


def map_product(product: dict) -> dict:
    nutriments = product.get("nutriments", {})
    name = (
        product.get("product_name")
        or product.get("product_name_en")
        or product.get("generic_name")
        or "Food item"
    )
    return {
        "barcode": product.get("code"),
        "product_name": name,
        "brand": product.get("brands"),
        "calories": _to_float(nutriments.get("energy-kcal_serving")),
        "protein": _to_float(nutriments.get("proteins_serving")),
        "carbs": _to_float(nutriments.get("carbohydrates_serving")),
        "fat": _to_float(nutriments.get("fat_serving")),
        "serving_quantity": _to_float(product.get("serving_quantity") or nutriments.get("serving_quantity")),
        "serving_unit": product.get("serving_size"),
        "image_url": product.get("image_front_thumb_url") or product.get("image_url"),
        "source": "openfoodfacts",
        "is_active": True,
    }


async def get_or_create_food_item(db, barcode: str) -> FoodItem | None:
    item = db.query(FoodItem).filter(FoodItem.barcode == barcode).first()
    if item:
        return item

    product = await fetch_product(barcode)
    if not product:
        return None

    data = map_product(product)
    item = FoodItem(**data, last_synced_at=datetime.utcnow())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
