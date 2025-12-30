from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.exercise_library import ExerciseLibraryItem
from app.schemas.exercise_library import (
    ExerciseLibraryItemCreate,
    ExerciseLibraryItemResponse,
    ExerciseLibraryItemUpdate,
)
from app.services.auth_middleware import get_current_admin, get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/exercise-library", tags=["Exercise Library"])


@router.get("")
def list_exercise_library(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        items = (
            db.query(ExerciseLibraryItem)
            .filter(ExerciseLibraryItem.is_active == True)
            .order_by(ExerciseLibraryItem.sort_order.asc(), ExerciseLibraryItem.id.asc())
            .all()
        )
        payload = [
            ExerciseLibraryItemResponse.model_validate(item).model_dump()
            for item in items
        ]
        return create_response(
            message="Exercise library items fetched",
            data={"items": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.get("/admin")
def list_exercise_library_admin(
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        items = (
            db.query(ExerciseLibraryItem)
            .order_by(ExerciseLibraryItem.sort_order.asc(), ExerciseLibraryItem.id.asc())
            .all()
        )
        payload = [
            ExerciseLibraryItemResponse.model_validate(item).model_dump()
            for item in items
        ]
        return create_response(
            message="Exercise library items fetched",
            data={"items": payload},
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.post("")
def create_exercise_library_item(
    payload: ExerciseLibraryItemCreate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        existing = (
            db.query(ExerciseLibraryItem)
            .filter(ExerciseLibraryItem.slug == payload.slug)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exercise library item already exists",
            )
        item = ExerciseLibraryItem(
            slug=payload.slug,
            title=payload.title,
            cover_image_url=payload.cover_image_url,
            sort_order=payload.sort_order or 0,
            is_active=payload.is_active if payload.is_active is not None else True,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return create_response(
            message="Exercise library item created",
            data=ExerciseLibraryItemResponse.model_validate(item).model_dump(),
            status_code=status.HTTP_201_CREATED,
        )
    except Exception as exc:
        return handle_exception(exc)


@router.put("/{item_id}")
def update_exercise_library_item(
    item_id: int,
    payload: ExerciseLibraryItemUpdate,
    db: Session = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    try:
        item = (
            db.query(ExerciseLibraryItem)
            .filter(ExerciseLibraryItem.id == item_id)
            .first()
        )
        if not item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exercise library item not found",
            )
        if payload.title is not None:
            item.title = payload.title
        if payload.cover_image_url is not None:
            item.cover_image_url = payload.cover_image_url
        if payload.sort_order is not None:
            item.sort_order = payload.sort_order
        if payload.is_active is not None:
            item.is_active = payload.is_active
        db.commit()
        db.refresh(item)
        return create_response(
            message="Exercise library item updated",
            data=ExerciseLibraryItemResponse.model_validate(item).model_dump(),
            status_code=status.HTTP_200_OK,
        )
    except Exception as exc:
        return handle_exception(exc)
