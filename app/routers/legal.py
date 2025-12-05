from fastapi import APIRouter, status

from app.utils.response import create_response

router = APIRouter(prefix="/legal", tags=["Legal"])

PRIVACY_TEXT = (
    "We collect only the information needed to provide fitness tracking features. "
    "Data is not shared with third parties and you can request deletion at any time."
)

DELETE_ACCOUNT_TEXT = (
    "To delete your account, contact support via the in-app chat or email developer@glowante.com with your "
    "registered email address. We will remove your profile and associated wellness data within 7 business days."
)


@router.get("/privacy")
def privacy_policy():
    return create_response(
        message="Privacy policy",
        data={"content": PRIVACY_TEXT},
        status_code=status.HTTP_200_OK,
    )


@router.get("/delete-account")
def delete_account_info():
    return create_response(
        message="Account deletion instructions",
        data={"content": DELETE_ACCOUNT_TEXT},
        status_code=status.HTTP_200_OK,
    )
