import random
import string

from app.models.user import User

_REFERRAL_ALPHABET = string.ascii_uppercase + string.digits


def normalize_referral_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().upper()
    return normalized or None


def generate_referral_code(db, length: int = 6) -> str:
    for _ in range(12):
        code = "".join(random.choice(_REFERRAL_ALPHABET) for _ in range(length))
        exists = db.query(User).filter(User.referral_code == code).first()
        if not exists:
            return code
    suffix = "".join(random.choice(_REFERRAL_ALPHABET) for _ in range(8))
    return f"SS{suffix}"


def ensure_referral_code(db, user: User) -> str:
    if user.referral_code:
        return user.referral_code
    user.referral_code = generate_referral_code(db)
    return user.referral_code
