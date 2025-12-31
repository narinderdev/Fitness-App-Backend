from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.nutrition import FoodItem, FoodLog, FoodCategory
from app.models.user import User
from app.schemas.nutrition import (
    FoodCategoryCreate,
    FoodCategoryResponse,
    FoodCategoryUpdate,
    FoodItemAdminPayload,
    FoodItemResponse,
    FoodLogEntry,
    LogCreate,
    ScanRequest,
)
from app.services.auth_middleware import get_current_admin, get_current_user
from app.services.openfoodfacts import get_or_create_food_item
from app.utils.response import create_response, handle_exception
import httpx

router = APIRouter(prefix="/nutrition", tags=["Nutrition"], dependencies=[Depends(get_current_user)])
admin_router = APIRouter(prefix="/nutrition/admin", tags=["Nutrition Admin"], dependencies=[Depends(get_current_admin)])


async def _get_cached_food(db: Session, barcode: str) -> FoodItem | None:
    return db.query(FoodItem).filter(FoodItem.barcode == barcode).first()


def _serialize_food_item(item: FoodItem | None) -> dict | None:
    if not item:
        return None
    name = (item.product_name or item.brand or "Food item").strip()
    payload = FoodItemResponse(
        id=item.id,
        barcode=item.barcode,
        product_name=name,
        brand=item.brand,
        calories=item.calories,
        protein=item.protein,
        carbs=item.carbs,
        fat=item.fat,
        serving_quantity=item.serving_quantity,
        serving_unit=item.serving_unit,
        image_url=item.image_url,
        description=item.description,
        source=item.source,
        category_id=item.category_id,
        category_name=item.category.name if item.category else None,
        is_active=item.is_active,
    ).model_dump()
    return payload


def _log_payload(log: FoodLog) -> dict:
    item = _serialize_food_item(log.food_item)
    payload = FoodLogEntry(
        id=log.id,
        consumed_date=log.consumed_date.isoformat(),
        servings=log.serving_multiplier,
        calories=log.calories,
        protein=log.protein,
        carbs=log.carbs,
        fat=log.fat,
        notes=log.notes,
        food_item=item,
    ).model_dump()
    return payload


@router.get("/categories")
def list_categories(
    db: Session = Depends(get_db),
):
    try:
        categories = (
            db.query(FoodCategory)
            .filter(FoodCategory.is_active == True)
            .order_by(FoodCategory.name.asc())
            .all()
        )
        payload = [FoodCategoryResponse.model_validate(cat).model_dump() for cat in categories]
        return create_response(
            message="Food categories fetched",
            data={"count": len(payload), "categories": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.get("/categories")
def admin_list_categories(
    include_inactive: bool = Query(True),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(FoodCategory).order_by(FoodCategory.name.asc())
        if not include_inactive:
            query = query.filter(FoodCategory.is_active == True)
        categories = query.all()
        payload = [FoodCategoryResponse.model_validate(cat).model_dump() for cat in categories]
        return create_response(
            message="Admin categories fetched",
            data={"count": len(payload), "categories": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.post("/categories")
def admin_create_category(
    payload: FoodCategoryCreate,
    db: Session = Depends(get_db),
):
    try:
        category = FoodCategory(
            name=payload.name.strip(),
            description=payload.description,
            is_active=payload.is_active,
        )
        db.add(category)
        db.commit()
        db.refresh(category)
        return create_response(
            message="Category created",
            data=FoodCategoryResponse.model_validate(category).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.put("/categories/{category_id}")
def admin_update_category(
    category_id: int,
    payload: FoodCategoryUpdate,
    db: Session = Depends(get_db),
):
    try:
        category = db.query(FoodCategory).filter(FoodCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        if payload.name is not None:
            category.name = payload.name.strip()
        if payload.description is not None:
            category.description = payload.description
        if payload.is_active is not None:
            category.is_active = payload.is_active
        db.commit()
        db.refresh(category)
        return create_response(
            message="Category updated",
            data=FoodCategoryResponse.model_validate(category).model_dump(),
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.delete("/categories/{category_id}")
def admin_delete_category(
    category_id: int,
    db: Session = Depends(get_db),
):
    try:
        category = db.query(FoodCategory).filter(FoodCategory.id == category_id).first()
        if not category:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
        db.query(FoodItem).filter(FoodItem.category_id == category_id).update(
            {FoodItem.category_id: None},
            synchronize_session=False,
        )
        db.delete(category)
        db.commit()
        return create_response(
            message="Category deleted",
            data={"deleted": True, "category_id": category_id},
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.get("/foods")
def admin_list_foods(
    search: str | None = Query(None),
    category_id: int | None = Query(None),
    include_inactive: bool = Query(True),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(FoodItem).outerjoin(FoodCategory).filter(FoodItem.source == "manual")
        if not include_inactive:
            query = query.filter(FoodItem.is_active == True)
        if category_id:
            query = query.filter(FoodItem.category_id == category_id)
        if search:
            like = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(FoodItem.product_name).like(like),
                    func.lower(FoodItem.brand).like(like),
                )
            )
        total = query.count()
        items = (
            query.order_by(
                func.coalesce(FoodCategory.name, "").asc(),
                FoodItem.product_name.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        payload = [_serialize_food_item(item) for item in items]
        return create_response(
            message="Admin foods fetched",
            data={
                "items": payload,
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": page * page_size < total,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.post("/foods")
def admin_create_food(
    payload: FoodItemAdminPayload,
    db: Session = Depends(get_db),
):
    try:
        category = None
        if payload.category_id:
            category = db.query(FoodCategory).filter(FoodCategory.id == payload.category_id).first()
            if not category:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

        item = FoodItem(
            product_name=payload.name.strip(),
            brand=payload.brand.strip() if payload.brand else None,
            calories=payload.calories,
            protein=payload.protein,
            carbs=payload.carbs,
            fat=payload.fat,
            serving_quantity=payload.serving_quantity or 1.0,
            serving_unit=payload.serving_unit or "serving",
            image_url=payload.image_url,
            description=payload.description,
            source="manual",
            category_id=category.id if category else None,
            is_active=payload.is_active,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return create_response(
            message="Food created",
            data=_serialize_food_item(item),
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.put("/foods/{food_id}")
def admin_update_food(
    food_id: int,
    payload: FoodItemAdminPayload,
    db: Session = Depends(get_db),
):
    try:
        item = db.query(FoodItem).filter(FoodItem.id == food_id, FoodItem.source == "manual").first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        if payload.category_id is not None:
            if payload.category_id == 0:
                item.category_id = None
            else:
                category = db.query(FoodCategory).filter(FoodCategory.id == payload.category_id).first()
                if not category:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")
                item.category_id = category.id
        item.product_name = payload.name.strip()
        item.brand = payload.brand.strip() if payload.brand else None
        item.calories = payload.calories
        item.protein = payload.protein
        item.carbs = payload.carbs
        item.fat = payload.fat
        item.serving_quantity = payload.serving_quantity or 1.0
        item.serving_unit = payload.serving_unit or "serving"
        item.image_url = payload.image_url
        item.description = payload.description
        item.is_active = payload.is_active
        db.commit()
        db.refresh(item)
        return create_response(
            message="Food updated",
            data=_serialize_food_item(item),
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.delete("/foods/{food_id}")
def admin_delete_food(
    food_id: int,
    db: Session = Depends(get_db),
):
    try:
        item = db.query(FoodItem).filter(FoodItem.id == food_id, FoodItem.source == "manual").first()
        if not item:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Food not found")
        db.query(FoodLog).filter(FoodLog.food_item_id == food_id).update(
            {FoodLog.food_item_id: None},
            synchronize_session=False,
        )
        db.delete(item)
        db.commit()
        return create_response(
            message="Food deleted",
            data={"deleted": True, "food_id": food_id},
            status_code=status.HTTP_200_OK,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@router.get("/foods")
def list_manual_foods(
    search: str | None = Query(None),
    category_id: int | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        query = (
            db.query(FoodItem)
            .outerjoin(FoodCategory)
            .filter(
                FoodItem.source == "manual",
                FoodItem.is_active == True,
            )
        )
        if category_id:
            query = query.filter(FoodItem.category_id == category_id)
        if search:
            like = f"%{search.strip().lower()}%"
            query = query.filter(
                or_(
                    func.lower(FoodItem.product_name).like(like),
                    func.lower(FoodItem.brand).like(like),
                )
            )
        total = query.count()
        items = (
            query.order_by(
                func.coalesce(FoodCategory.name, "").asc(),
                FoodItem.product_name.asc(),
            )
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        payload = [_serialize_food_item(item) for item in items]
        return create_response(
            message="Foods fetched",
            data={
                "items": payload,
                "page": page,
                "page_size": page_size,
                "total": total,
                "has_next": page * page_size < total,
            },
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


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

        payload = _serialize_food_item(item)
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

        existing_log = None
        barcode = body.barcode or (food_item.barcode if food_item else None)
        food_item_id = food_item.id if food_item else None
        if barcode:
            existing_log = (
                db.query(FoodLog)
                .filter(
                    FoodLog.user_id == current_user.id,
                    FoodLog.consumed_date == consumed_date,
                    FoodLog.barcode == barcode,
                )
                .first()
            )
        elif food_item_id:
            existing_log = (
                db.query(FoodLog)
                .filter(
                    FoodLog.user_id == current_user.id,
                    FoodLog.consumed_date == consumed_date,
                    FoodLog.food_item_id == food_item_id,
                )
                .first()
            )

        if existing_log:
            existing_log.serving_multiplier += servings
            if food_item:
                existing_log.calories = (existing_log.calories or 0) + (food_item.calories or 0) * servings
                existing_log.protein = (existing_log.protein or 0) + (food_item.protein or 0) * servings
                existing_log.carbs = (existing_log.carbs or 0) + (food_item.carbs or 0) * servings
                existing_log.fat = (existing_log.fat or 0) + (food_item.fat or 0) * servings
            if body.notes is not None:
                existing_log.notes = body.notes
            db.commit()
            db.refresh(existing_log)
            log = existing_log
        else:
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
