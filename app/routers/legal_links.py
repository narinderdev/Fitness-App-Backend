from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.legal_links import LegalLinks
from app.schemas.app_settings import LegalLinksResponse, LegalLinksUpdate
from app.services.auth_middleware import get_current_admin
from app.utils.response import create_response, handle_exception

router = APIRouter(prefix="/legal-links", tags=["Legal Links"])


def _get_links(db: Session) -> LegalLinks:
    links = db.query(LegalLinks).order_by(LegalLinks.id.asc()).first()
    if links:
        return links
    links = LegalLinks()
    db.add(links)
    db.commit()
    db.refresh(links)
    return links


@router.get("")
def get_legal_links(db: Session = Depends(get_db)):
    try:
        links = _get_links(db)
        payload = LegalLinksResponse.model_validate(links).model_dump()
        return create_response(message="Legal links fetched", data=payload)
    except Exception as exc:
        return handle_exception(exc)


@router.put("/admin")
def update_legal_links(
    body: LegalLinksUpdate,
    db: Session = Depends(get_db),
    admin=Depends(get_current_admin),
):
    del admin
    try:
        links = _get_links(db)
        updates = body.model_dump(exclude_unset=True)
        for field, value in updates.items():
            setattr(links, field, value)
        db.add(links)
        db.commit()
        db.refresh(links)
        payload = LegalLinksResponse.model_validate(links).model_dump()
        return create_response(message="Legal links updated", data=payload)
    except Exception as exc:
        return handle_exception(exc)
