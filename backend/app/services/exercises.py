from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.db.models.exercises import Exercise
from backend.app.repositories.exercises import ExerciseRepository
from backend.app.schemas.exercises import ExerciseCreate, ExerciseUpdate
from backend.app.core.exceptions import ConflictError, NotFoundError


class ExerciseService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._exercises = ExerciseRepository(session)

    def normalize_exercise_name(self, name: str) -> str:
        return " ".join(name.split()).strip()

    async def create(self, data: ExerciseCreate) -> Exercise:
        name = self.normalize_exercise_name(data.name)

        existing = await self._exercises.get_by_name(name)
        if existing is not None:
            raise ConflictError("Exercise name already exists")

        exercise = Exercise(
            name=name,
            muscle_group=data.muscle_group,
            is_active=True,
        )
        created = await self._exercises.create(exercise)
        await self._session.commit()
        return created

    async def get_by_id(self, exercise_id: int) -> Exercise:
        exercise: Exercise | None = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")
        return exercise

    async def list(self, is_active: bool | None = None) -> list[Exercise]:
        return await self._exercises.list(is_active=is_active)

    async def update(self, exercise_id: int, data: ExerciseUpdate) -> Exercise:
        exercise: Exercise | None = await self._exercises.get_by_id(exercise_id)
        if exercise is None:
            raise NotFoundError("Exercise not found")

        if data.name is not None:
            name = self.normalize_exercise_name(data.name)
            existing = await self._exercises.get_by_name(name)
            if existing is not None and existing.id != exercise_id:
                raise ConflictError("Exercise name already exists")
            exercise.name = name

        if data.muscle_group is not None:
            exercise.muscle_group = data.muscle_group

        if data.is_active is not None:
            exercise.is_active = data.is_active

        await self._session.commit()
        return exercise
