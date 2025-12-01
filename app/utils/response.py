from fastapi import HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def create_response(
    message: str,
    data=None,
    status_code: int = status.HTTP_200_OK,
    status_text: str | None = None
) -> JSONResponse:
    """Return a consistent API response payload and status code."""
    payload_status = status_text or ("success" if status_code < 400 else "error")
    encoded_data = jsonable_encoder(data)
    return JSONResponse(
        status_code=status_code,
        content={
            "message": message,
            "data": encoded_data,
            "status": payload_status,
            "status_code": status_code,
        },
    )


def handle_exception(error: Exception, fallback_message: str = "Internal server error") -> JSONResponse:
    """Coerce raised errors into the shared response structure."""
    if isinstance(error, HTTPException):
        detail = error.detail if isinstance(error.detail, str) else str(error.detail)
        return create_response(detail, None, error.status_code, status_text="error")

    return create_response(fallback_message, None, status.HTTP_500_INTERNAL_SERVER_ERROR, status_text="error")
