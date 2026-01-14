from __future__ import annotations

TSP_ML = 5.0
TBSP_ML = 15.0
CUP_ML = 250.0


def _safe_value(value: float | None) -> float:
    return 0.0 if value is None else float(value)


def normalize_food_type(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized if normalized in {"SOLID", "LIQUID"} else None


def volume_to_ml(amount: float, unit: str) -> float:
    normalized = unit.strip().lower()
    if normalized in {"ml", "milliliter", "milliliters"}:
        return amount
    if normalized in {"tsp", "teaspoon", "teaspoons"}:
        return amount * TSP_ML
    if normalized in {"tbsp", "tablespoon", "tablespoons"}:
        return amount * TBSP_ML
    if normalized in {"cup", "cups"}:
        return amount * CUP_ML
    raise ValueError(f"Unsupported volume unit: {unit}")


def derive_default_serving_grams(
    *,
    food_type: str | None,
    default_serving_grams: float | None = None,
    default_serving_ml: float | None = None,
    density_g_per_ml: float | None = None,
) -> float | None:
    if food_type == "SOLID":
        return default_serving_grams if default_serving_grams and default_serving_grams > 0 else None
    if food_type == "LIQUID":
        if not density_g_per_ml or density_g_per_ml <= 0:
            return None
        if not default_serving_ml or default_serving_ml <= 0:
            return None
        return default_serving_ml * density_g_per_ml
    return None


def resolve_grams(
    *,
    food_type: str,
    input_grams: float | None = None,
    input_ml: float | None = None,
    input_amount: float | None = None,
    input_unit: str | None = None,
    default_serving_grams: float | None = None,
    default_serving_ml: float | None = None,
    density_g_per_ml: float | None = None,
) -> float:
    if food_type == "SOLID":
        if input_grams and input_grams > 0:
            return input_grams
        if default_serving_grams and default_serving_grams > 0:
            return default_serving_grams
        raise ValueError("Missing grams for solid food")

    if food_type == "LIQUID":
        if not density_g_per_ml or density_g_per_ml <= 0:
            raise ValueError("Missing density for liquid food")
        if input_ml and input_ml > 0:
            return input_ml * density_g_per_ml
        if input_amount and input_unit:
            ml_value = volume_to_ml(input_amount, input_unit)
            return ml_value * density_g_per_ml
        if default_serving_ml and default_serving_ml > 0:
            return default_serving_ml * density_g_per_ml
        raise ValueError("Missing volume for liquid food")

    raise ValueError("Unknown food type")


def calculate_macros_from_grams(
    *,
    grams: float,
    calories_per_100g: float | None,
    protein_per_100g: float | None,
    carbs_per_100g: float | None,
    fat_per_100g: float | None,
    digits: int = 1,
) -> dict:
    if grams <= 0:
        raise ValueError("grams must be positive")
    factor = grams / 100.0
    calories = round(_safe_value(calories_per_100g) * factor, digits)
    protein = round(_safe_value(protein_per_100g) * factor, digits)
    carbs = round(_safe_value(carbs_per_100g) * factor, digits)
    fat = round(_safe_value(fat_per_100g) * factor, digits)
    return {
        "calories": calories,
        "protein": protein,
        "carbs": carbs,
        "fat": fat,
    }
