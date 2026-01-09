from pydantic import BaseModel, Field


class LegalLinksResponse(BaseModel):
    terms_url: str | None = None
    privacy_url: str | None = None
    subscription_url: str | None = None

    model_config = {"from_attributes": True}


class LegalLinksUpdate(BaseModel):
    terms_url: str | None = Field(None, max_length=500)
    privacy_url: str | None = Field(None, max_length=500)
    subscription_url: str | None = Field(None, max_length=500)
