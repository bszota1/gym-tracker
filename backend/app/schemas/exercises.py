from pydantic import BaseModel, Field

from backend.app.schemas.common import APIModel


class ExerciseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    muscle_group: str | None = Field(default=None, max_length=50)


class ExerciseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    muscle_group: str | None = Field(default=None, max_length=50)
    is_active: bool | None = None


class ExerciseResponse(APIModel):
    id: int
    name: str
    muscle_group: str | None
    is_active: bool
