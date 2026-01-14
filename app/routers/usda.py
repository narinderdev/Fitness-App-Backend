from fastapi import APIRouter, Depends, HTTPException, Query, status
import httpx

from app.services.auth_middleware import get_current_admin
from app.services.usda import DEFAULT_SEARCH_LIMIT, fetch_food, search_foods
from app.utils.response import create_response, handle_exception

router = APIRouter(
    prefix="/api/usda",
    tags=["USDA"],
    dependencies=[Depends(get_current_admin)],
)


@router.get("/search")
async def usda_search(
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(DEFAULT_SEARCH_LIMIT, ge=1, le=50),
):
    try:
        items = await search_foods(q, limit=limit)
        return create_response(
            message="USDA search results",
            data={"items": items},
            status_code=status.HTTP_200_OK,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"USDA error: {exc.response.status_code}",
        )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach USDA")
    except Exception as exc:
        return handle_exception(exc)


@router.get("/food/{fdc_id}")
async def usda_food(fdc_id: int):
    try:
        data = await fetch_food(fdc_id)
        return create_response(
            message="USDA food details",
            data=data,
            status_code=status.HTTP_200_OK,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc))
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"USDA error: {exc.response.status_code}",
        )
    except httpx.RequestError:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Unable to reach USDA")
    except Exception as exc:
        return handle_exception(exc)
