from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.nutrition import FoodItem, FoodLog
from app.models.user import User
from app.schemas.nutrition import FoodItemResponse, FoodLogEntry, LogCreate, ScanRequest
from app.services.auth_middleware import get_current_user
from app.services.openfoodfacts import get_or_create_food_item
from app.utils.response import create_response, handle_exception
import httpx

router = APIRouter(prefix="/nutrition", tags=["Nutrition"], dependencies=[Depends(get_current_user)])


async def _get_cached_food(db: Session, barcode: str) -> FoodItem | None:
    return db.query(FoodItem).filter(FoodItem.barcode == barcode).first()


def _log_payload(log: FoodLog) -> dict:
    item = log.food_item
    return FoodLogEntry(
        id=log.id,
        consumed_date=log.consumed_date.isoformat(),
        servings=log.serving_multiplier,
        calories=log.calories,
        protein=log.protein,
        carbs=log.carbs,
        fat=log.fat,
        notes=log.notes,
        food_item=FoodItemResponse.model_validate(item) if item else None,
    ).model_dump()


@router.post("/scan")
async def scan_barcode(
    body: ScanRequest,
    db: Session = Depends(get_db),
):
    try:
        barcode = body.barcode.strip()
        if not barcode:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Barcode is required")

        item = await _get_cached_food(db, barcode)
        if not item:
            item = await get_or_create_food_item(db, barcode)
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

        payload = FoodItemResponse.model_validate(item).model_dump()
        return create_response(
            message="Product retrieved",
            data=payload,
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=f"OpenFoodFacts error: {exc.response.status_code}")
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach OpenFoodFacts")
    except Exception as exc:
        return handle_exception(exc)


@router.post("/logs")
async def create_log(
    body: LogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        servings = body.servings or 1.0
        if servings <= 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Servings must be positive")

        food_item = None
        if body.food_item_id:
            food_item = db.query(FoodItem).filter(FoodItem.id == body.food_item_id).first()
        elif body.barcode:
            food_item = await get_or_create_food_item(db, body.barcode)

        if not food_item and not body.barcode:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Provide food_item_id or barcode")

        consumed_date = date.fromisoformat(body.consumed_date) if body.consumed_date else date.today()
        calories = protein = carbs = fat = None
        if food_item:
            calories = (food_item.calories or 0) * servings
            protein = (food_item.protein or 0) * servings
            carbs = (food_item.carbs or 0) * servings
            fat = (food_item.fat or 0) * servings

        log = FoodLog(
            user_id=current_user.id,
            food_item_id=food_item.id if food_item else None,
            barcode=body.barcode if body.barcode else (food_item.barcode if food_item else None),
            serving_multiplier=servings,
            calories=calories,
            protein=protein,
            carbs=carbs,
            fat=fat,
            notes=body.notes,
            consumed_date=consumed_date,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        return create_response(
            message="Food log saved",
            data=_log_payload(log),
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs")
def list_logs(
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        query = db.query(FoodLog).filter(FoodLog.user_id == current_user.id).order_by(FoodLog.consumed_date.desc())

        if start_date:
            query = query.filter(FoodLog.consumed_date >= date.fromisoformat(start_date))
        if end_date:
            query = query.filter(FoodLog.consumed_date <= date.fromisoformat(end_date))

        logs = query.all()
        payload = [_log_payload(log) for log in logs]

        return create_response(
            message="Food logs fetched",
            data={"count": len(payload), "logs": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/summary")
def calorie_summary(
    days: int = Query(7, ge=1, le=31),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        end_date = date.today()
        start_date = end_date - timedelta(days=days - 1)

        logs = (
            db.query(FoodLog)
            .filter(
                FoodLog.user_id == current_user.id,
                FoodLog.consumed_date >= start_date,
                FoodLog.consumed_date <= end_date,
            )
            .all()
        )

        totals = {}
        entries_per_date = {}
        for log in logs:
            totals.setdefault(log.consumed_date, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0})
            totals[log.consumed_date]["calories"] += log.calories or 0.0
            totals[log.consumed_date]["protein"] += log.protein or 0.0
            totals[log.consumed_date]["carbs"] += log.carbs or 0.0
            totals[log.consumed_date]["fat"] += log.fat or 0.0

            entries_per_date.setdefault(log.consumed_date, [])
            entries_per_date[log.consumed_date].append(
                {
                    "log_id": log.id,
                    "food_item": FoodItemResponse.model_validate(log.food_item).model_dump()
                    if log.food_item
                    else None,
                    "barcode": log.barcode,
                    "servings": log.serving_multiplier,
                    "calories": log.calories,
                    "protein": log.protein,
                    "carbs": log.carbs,
                    "fat": log.fat,
                    "notes": log.notes,
                }
            )

        entries = []
        cursor = end_date
        while cursor >= start_date:
            totals_for_day = totals.get(cursor, {"calories": 0.0, "protein": 0.0, "carbs": 0.0, "fat": 0.0})
            entries.append(
                {
                    "date": cursor.isoformat(),
                    "calories": round(totals_for_day["calories"], 2),
                    "protein": round(totals_for_day["protein"], 2),
                    "carbs": round(totals_for_day["carbs"], 2),
                    "fat": round(totals_for_day["fat"], 2),
                    "items": entries_per_date.get(cursor, []),
                }
            )
            cursor -= timedelta(days=1)

        return create_response(
            message="Calorie summary fetched",
            data={
                "range": {"start": start_date.isoformat(), "end": end_date.isoformat()},
                "entries": entries,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/logs/today")
def today_nutrition(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        today = date.today()
        logs = (
            db.query(FoodLog)
            .filter(FoodLog.user_id == current_user.id, FoodLog.consumed_date == today)
            .all()
        )

        total_calories = sum(log.calories or 0 for log in logs)
        total_protein = sum(log.protein or 0 for log in logs)
        total_carbs = sum(log.carbs or 0 for log in logs)
        total_fat = sum(log.fat or 0 for log in logs)

        return create_response(
            message="Today's nutrition fetched",
            data={
                "date": today.isoformat(),
                "calories": round(total_calories, 2),
                "protein": round(total_protein, 2),
                "carbs": round(total_carbs, 2),
                "fat": round(total_fat, 2),
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
