from pydantic import BaseModel


class ExerciseLibraryItemBase(BaseModel):
    slug: str
    title: str
    cover_image_url: str | None = None
    sort_order: int | None = 0
    is_active: bool | None = True


class ExerciseLibraryItemCreate(ExerciseLibraryItemBase):
    pass


class ExerciseLibraryItemUpdate(BaseModel):
    title: str | None = None
    cover_image_url: str | None = None
    sort_order: int | None = None
    is_active: bool | None = None


class ExerciseLibraryItemResponse(BaseModel):
    id: int
    slug: str
    title: str
    cover_image_url: str | None = None
    sort_order: int
    is_active: bool

    model_config = {"from_attributes": True}
