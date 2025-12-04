import os
from typing import List, Dict

import firebase_admin
from firebase_admin import credentials, messaging

from app.config import settings

FIREBASE_CREDENTIALS_FILE = settings.FIREBASE_CREDENTIALS_FILE

firebase_app = None
if FIREBASE_CREDENTIALS_FILE and os.path.exists(FIREBASE_CREDENTIALS_FILE):
    cred = credentials.Certificate(FIREBASE_CREDENTIALS_FILE)
    firebase_app = firebase_admin.initialize_app(cred)


def send_push_notification(tokens: List[str], title: str, body: str, data: Dict[str, str] | None = None) -> dict:
    if not firebase_app:
        raise RuntimeError("Firebase app is not configured. Set FIREBASE_CREDENTIALS_FILE env.")

    if not tokens:
        return {"success": 0, "failure": 0}

    message = messaging.MulticastMessage(
        tokens=tokens,
        notification=messaging.Notification(title=title, body=body),
        data=data or {},
    )

    response = messaging.send_each_for_multicast(message)
    return {"success": response.success_count, "failure": response.failure_count}
