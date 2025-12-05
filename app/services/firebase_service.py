import os
from typing import List, Dict
import logging

import firebase_admin
from firebase_admin import credentials, messaging

from app.config import settings

logger = logging.getLogger(__name__)

FIREBASE_CREDENTIALS_FILE = settings.FIREBASE_CREDENTIALS_FILE

firebase_app = None
if FIREBASE_CREDENTIALS_FILE and os.path.exists(FIREBASE_CREDENTIALS_FILE):
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
    firebase_app = firebase_admin.initialize_app(cred)
    logger.info("Firebase app initialized using %s", FIREBASE_CREDENTIALS_FILE)
else:
    logger.warning("Firebase credentials not configured. Notifications disabled.")


def send_push_notification(tokens: List[str], title: str, body: str, data: Dict[str, str] | None = None) -> dict:
    if not firebase_app:
        raise RuntimeError("Firebase app is not configured. Set FIREBASE_CREDENTIALS_FILE env.")

    if not tokens:
        logger.info("send_push_notification called with empty token list.")
        return {"success": 0, "failure": 0}

    logger.info("Sending push notification to %s tokens title=%s", len(tokens), title)

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )

    response = messaging.send_each_for_multicast(message)
    logger.info("Push result success=%s failure=%s", response.success_count, response.failure_count)
    invalid_tokens: list[str] = []
    errors: list[dict] = []
    for idx, resp in enumerate(response.responses):
        token = tokens[idx]
        if resp.success:
            logger.debug("Token %s delivered", token)
            continue
        error_message = str(resp.exception)
        error_code = getattr(resp.exception, "code", None)
        logger.warning("Token %s failed: %s (code=%s)", token, error_message, error_code)
        errors.append({"token": token, "code": error_code, "message": error_message})
        if _should_invalidate_token(error_code, error_message):
            invalid_tokens.append(token)
    if invalid_tokens:
        logger.info("Identified %s invalid tokens to remove", len(invalid_tokens))
    return {
        "success": response.success_count,
        "failure": response.failure_count,
        "invalid_tokens": invalid_tokens,
        "errors": errors,
    }


def _should_invalidate_token(error_code: str | None, error_message: str) -> bool:
    normalized_code = (error_code or "").lower()
    normalized_message = (error_message or "").lower()
    invalid_codes = {
        "registration-token-not-registered",
        "messaging/registration-token-not-registered",
        "messaging/invalid-apns-credentials",
        "invalid-argument",
    }
    if normalized_code in invalid_codes:
        return True
    keywords = [
        "requested entity was not found",
        "notregistered",
        "auth error from apns",
        "invalid-apns-credentials",
    ]
    return any(keyword in normalized_message for keyword in keywords)
