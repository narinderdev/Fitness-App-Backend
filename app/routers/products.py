from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.product import Product
from app.schemas.product import ProductCreate, ProductResponse, ProductUpdate
from app.services.auth_middleware import get_current_admin, get_current_user
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/products", tags=["Products"])
admin_router = APIRouter(
    prefix="/products/admin",
    tags=["Products Admin"],
    dependencies=[Depends(get_current_admin)],
)


def _product_payload(product: Product) -> dict:
    return ProductResponse.model_validate(product).model_dump()


@router.get("")
def list_products(
    include_inactive: bool = Query(
        False, description="Include inactive products alongside active entries."
    ),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    del user
    try:
        query = db.query(Product)
        if not include_inactive:
            query = query.filter(Product.is_active == True)
        products = query.order_by(Product.sort_order.asc(), Product.created_at.desc()).all()
        return create_response(
            message="Products fetched",
            data={
                "count": len(products),
                "products": [_product_payload(product) for product in products],
            },
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.get("")
def admin_list_products(
    include_inactive: bool = Query(
        False, description="Include inactive products alongside active entries."
    ),
    status_filter: Optional[Literal["active", "inactive", "all"]] = Query(
        None,
        alias="status",
        description="Filter products by status; defaults to active unless include_inactive is true.",
    ),
    db: Session = Depends(get_db),
):
    try:
        query = db.query(Product)
        effective_status = status_filter
        if effective_status is None:
            effective_status = "all" if include_inactive else "active"

        if effective_status == "active":
            query = query.filter(Product.is_active == True)
        elif effective_status == "inactive":
            query = query.filter(Product.is_active == False)
        elif not include_inactive:
            query = query.filter(Product.is_active == True)

        products = query.order_by(Product.sort_order.asc(), Product.created_at.desc()).all()
        return create_response(
            message="Products fetched",
            data={
                "count": len(products),
                "products": [_product_payload(product) for product in products],
            },
        )
    except Exception as exc:
        return handle_exception(exc)


@admin_router.post("", status_code=status.HTTP_201_CREATED)
def create_product(
    body: ProductCreate,
    db: Session = Depends(get_db),
):
    try:
        payload = body.model_dump()
        product = Product(**payload)
        db.add(product)
        db.commit()
        db.refresh(product)
        return create_response(
            message="Product created",
            data=_product_payload(product),
            status_code=status.HTTP_201_CREATED,
        )
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.get("/{product_id}")
def get_product(product_id: int, db: Session = Depends(get_db)):
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        return create_response(message="Product fetched", data=_product_payload(product))
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.put("/{product_id}")
def update_product(
    product_id: int,
    body: ProductUpdate,
    db: Session = Depends(get_db),
):
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        update_data = body.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(product, field, value)
        db.commit()
        db.refresh(product)
        return create_response(message="Product updated", data=_product_payload(product))
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)


@admin_router.delete("/{product_id}")
def delete_product(product_id: int, db: Session = Depends(get_db)):
    try:
        product = db.query(Product).filter(Product.id == product_id).first()
        if not product:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
        db.delete(product)
        db.commit()
        return create_response(message="Product deleted", data=None, status_code=status.HTTP_200_OK)
    except HTTPException:
        raise
    except Exception as exc:
        return handle_exception(exc)
