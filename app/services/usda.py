import time
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.config import settings

USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
DEFAULT_SEARCH_LIMIT = 25
_CACHE_TTL_SECONDS = 60 * 60

_search_cache: Dict[str, Dict[str, Any]] = {}
_food_cache: Dict[int, Dict[str, Any]] = {}
logger = logging.getLogger(__name__)


def _cache_get(cache: Dict[Any, Dict[str, Any]], key: Any) -> Optional[Any]:
    entry = cache.get(key)
    if not entry:
        return None
    if entry["expires_at"] < time.time():
        cache.pop(key, None)
        return None
    return entry["value"]


def _cache_set(cache: Dict[Any, Dict[str, Any]], key: Any, value: Any) -> None:
    cache[key] = {"value": value, "expires_at": time.time() + _CACHE_TTL_SECONDS}


def _normalize_query(value: str) -> str:
    return " ".join(value.strip().split())


async def search_foods(query: str, limit: int = DEFAULT_SEARCH_LIMIT) -> List[Dict[str, Any]]:
    limit = max(1, min(limit, 50))
    api_key = settings.USDA_API_KEY
    if not api_key:
        raise ValueError("USDA_API_KEY is not configured")
    normalized = _normalize_query(query)
    cache_key = f"{normalized}:{limit}"
    cached = _cache_get(_search_cache, cache_key)
    if cached is not None:
        return cached

    params = {
        "query": normalized,
        "pageSize": limit,
        "api_key": api_key,
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{USDA_BASE_URL}/foods/search", params=params)
        response.raise_for_status()
        payload = response.json()

    items = []
    for entry in payload.get("foods", [])[:limit]:
        food_category = entry.get("foodCategory")
        if isinstance(food_category, dict):
            food_category = food_category.get("description") or food_category.get("name")
        calories = _extract_nutrient(entry, ["energy", "energy (atwater general factors)"]) or 0.0
        protein = _extract_nutrient(entry, ["protein"]) or 0.0
        carbs = _extract_nutrient(entry, ["carbohydrate, by difference"]) or 0.0
        fat = _extract_nutrient(entry, ["total lipid (fat)"]) or 0.0
        items.append(
            {
                "fdcId": entry.get("fdcId"),
                "description": entry.get("description"),
                "brandOwner": entry.get("brandOwner"),
                "dataType": entry.get("dataType"),
                "foodCategory": food_category,
                "calories": calories,
                "protein": protein,
                "carbs": carbs,
                "fat": fat,
            }
        )
    _cache_set(_search_cache, cache_key, items)
    return items


def _extract_nutrient(food: Dict[str, Any], names: List[str]) -> Optional[float]:
    nutrients = food.get("foodNutrients") or []
    for nutrient in nutrients:
        name = nutrient.get("nutrientName") or nutrient.get("nutrient", {}).get("name")
        if not name:
            continue
        if name.lower() in names:
            value = nutrient.get("amount")
            if value is None:
                value = nutrient.get("value")
            if value is None:
                continue
            try:
                return float(value)
            except (TypeError, ValueError):
                return None
    return None


async def fetch_food(fdc_id: int) -> Dict[str, Any]:
    api_key = settings.USDA_API_KEY
    if not api_key:
        raise ValueError("USDA_API_KEY is not configured")
    cached = _cache_get(_food_cache, fdc_id)
    if cached is not None:
        return cached

    params = {"api_key": api_key}
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{USDA_BASE_URL}/food/{fdc_id}", params=params)
        response.raise_for_status()
        food = response.json()

    calories = _extract_nutrient(food, ["energy", "energy (atwater general factors)"])
    protein = _extract_nutrient(food, ["protein"])
    carbs = _extract_nutrient(food, ["carbohydrate, by difference"])
    fat = _extract_nutrient(food, ["total lipid (fat)"])
    if calories is None:
        logger.warning("USDA nutrient missing: calories for fdc_id=%s", fdc_id)
        calories = 0.0
    if protein is None:
        logger.warning("USDA nutrient missing: protein for fdc_id=%s", fdc_id)
        protein = 0.0
    if carbs is None:
        logger.warning("USDA nutrient missing: carbs for fdc_id=%s", fdc_id)
        carbs = 0.0
    if fat is None:
        logger.warning("USDA nutrient missing: fat for fdc_id=%s", fdc_id)
        fat = 0.0

    normalized = {
        "fdcId": fdc_id,
        "name": food.get("description"),
        "calories_per_100g": calories,
        "protein_g_per_100g": protein,
        "carbs_g_per_100g": carbs,
        "fat_g_per_100g": fat,
        "source": "USDA FoodData Central",
        "source_url": f"https://fdc.nal.usda.gov/fdc-app.html#/food-details/{fdc_id}/nutrients",
    }
    _cache_set(_food_cache, fdc_id, normalized)
    return normalized
