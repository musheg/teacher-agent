"""Admin CRUD endpoints for curriculum content (admin role required)."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import DB, require_admin
from app.db.models import AgeBand, Course, Exercise, ExerciseType, Skill, Unit, User

router = APIRouter(prefix="/api/admin", tags=["admin"])
AdminUser = Annotated[User, Depends(require_admin)]


# ── Schemas ─────────────────────────────────────────────────────────
class AgeBandIn(BaseModel):
    name: str
    min_age: int = Field(ge=0, le=18)
    max_age: int = Field(ge=0, le=18)
    description: str | None = None
    pedagogy_notes: dict = Field(default_factory=dict)


class AgeBandOut(AgeBandIn):
    id: UUID
    model_config = {"from_attributes": True}


class CourseIn(BaseModel):
    age_band_id: UUID
    subject: str
    title: str
    description: str | None = None


class CourseOut(CourseIn):
    id: UUID
    model_config = {"from_attributes": True}


class UnitIn(BaseModel):
    course_id: UUID
    name: str
    description: str | None = None
    order_index: int = 0


class UnitOut(UnitIn):
    id: UUID
    model_config = {"from_attributes": True}


class SkillIn(BaseModel):
    unit_id: UUID
    code: str
    name: str
    description: str | None = None
    order_index: int = 0
    p_init: float = 0.1
    p_transit: float = 0.2
    p_slip: float = 0.1
    p_guess: float = 0.2
    prerequisites: list[str] = Field(default_factory=list)


class SkillOut(SkillIn):
    id: UUID
    model_config = {"from_attributes": True}


class ExerciseIn(BaseModel):
    skill_id: UUID
    type: ExerciseType
    prompt: str
    payload: dict = Field(default_factory=dict)
    difficulty: int = 1
    locale: str = "hy-AM"


class ExerciseOut(ExerciseIn):
    id: UUID
    model_config = {"from_attributes": True}


# ── Helpers shared by every CRUD ────────────────────────────────────
async def _list(model: Any, session: Any) -> list[Any]:
    rows = await session.scalars(select(model).order_by(model.created_at))
    return list(rows)


async def _get(model: Any, obj_id: UUID, session: Any) -> Any:
    obj = await session.get(model, obj_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"{model.__tablename__} not found")
    return obj


async def _create(model: Any, payload: BaseModel, session: Any) -> Any:
    obj = model(**payload.model_dump())
    session.add(obj)
    await session.commit()
    await session.refresh(obj)
    return obj


async def _update(model: Any, obj_id: UUID, payload: BaseModel, session: Any) -> Any:
    obj = await _get(model, obj_id, session)
    for k, v in payload.model_dump().items():
        setattr(obj, k, v)
    await session.commit()
    await session.refresh(obj)
    return obj


async def _delete(model: Any, obj_id: UUID, session: Any) -> None:
    obj = await _get(model, obj_id, session)
    await session.delete(obj)
    await session.commit()


# ── age-bands ────────────────────────────────────────────────────────
@router.get("/age-bands", response_model=list[AgeBandOut])
async def list_age_bands(_u: AdminUser, session: DB) -> list[AgeBand]:
    return await _list(AgeBand, session)


@router.post("/age-bands", response_model=AgeBandOut, status_code=201)
async def create_age_band(payload: AgeBandIn, _u: AdminUser, session: DB) -> AgeBand:
    return await _create(AgeBand, payload, session)


@router.get("/age-bands/{obj_id}", response_model=AgeBandOut)
async def get_age_band(obj_id: UUID, _u: AdminUser, session: DB) -> AgeBand:
    return await _get(AgeBand, obj_id, session)


@router.put("/age-bands/{obj_id}", response_model=AgeBandOut)
async def update_age_band(obj_id: UUID, payload: AgeBandIn, _u: AdminUser, session: DB) -> AgeBand:
    return await _update(AgeBand, obj_id, payload, session)


@router.delete("/age-bands/{obj_id}", status_code=204)
async def delete_age_band(obj_id: UUID, _u: AdminUser, session: DB) -> None:
    await _delete(AgeBand, obj_id, session)


# ── courses ─────────────────────────────────────────────────────────
@router.get("/courses", response_model=list[CourseOut])
async def list_courses(_u: AdminUser, session: DB) -> list[Course]:
    return await _list(Course, session)


@router.post("/courses", response_model=CourseOut, status_code=201)
async def create_course(payload: CourseIn, _u: AdminUser, session: DB) -> Course:
    return await _create(Course, payload, session)


@router.get("/courses/{obj_id}", response_model=CourseOut)
async def get_course(obj_id: UUID, _u: AdminUser, session: DB) -> Course:
    return await _get(Course, obj_id, session)


@router.put("/courses/{obj_id}", response_model=CourseOut)
async def update_course(obj_id: UUID, payload: CourseIn, _u: AdminUser, session: DB) -> Course:
    return await _update(Course, obj_id, payload, session)


@router.delete("/courses/{obj_id}", status_code=204)
async def delete_course(obj_id: UUID, _u: AdminUser, session: DB) -> None:
    await _delete(Course, obj_id, session)


# ── units ───────────────────────────────────────────────────────────
@router.get("/units", response_model=list[UnitOut])
async def list_units(_u: AdminUser, session: DB) -> list[Unit]:
    return await _list(Unit, session)


@router.post("/units", response_model=UnitOut, status_code=201)
async def create_unit(payload: UnitIn, _u: AdminUser, session: DB) -> Unit:
    return await _create(Unit, payload, session)


@router.get("/units/{obj_id}", response_model=UnitOut)
async def get_unit(obj_id: UUID, _u: AdminUser, session: DB) -> Unit:
    return await _get(Unit, obj_id, session)


@router.put("/units/{obj_id}", response_model=UnitOut)
async def update_unit(obj_id: UUID, payload: UnitIn, _u: AdminUser, session: DB) -> Unit:
    return await _update(Unit, obj_id, payload, session)


@router.delete("/units/{obj_id}", status_code=204)
async def delete_unit(obj_id: UUID, _u: AdminUser, session: DB) -> None:
    await _delete(Unit, obj_id, session)


# ── skills ──────────────────────────────────────────────────────────
@router.get("/skills", response_model=list[SkillOut])
async def list_skills(_u: AdminUser, session: DB) -> list[Skill]:
    return await _list(Skill, session)


@router.post("/skills", response_model=SkillOut, status_code=201)
async def create_skill(payload: SkillIn, _u: AdminUser, session: DB) -> Skill:
    return await _create(Skill, payload, session)


@router.get("/skills/{obj_id}", response_model=SkillOut)
async def get_skill(obj_id: UUID, _u: AdminUser, session: DB) -> Skill:
    return await _get(Skill, obj_id, session)


@router.put("/skills/{obj_id}", response_model=SkillOut)
async def update_skill(obj_id: UUID, payload: SkillIn, _u: AdminUser, session: DB) -> Skill:
    return await _update(Skill, obj_id, payload, session)


@router.delete("/skills/{obj_id}", status_code=204)
async def delete_skill(obj_id: UUID, _u: AdminUser, session: DB) -> None:
    await _delete(Skill, obj_id, session)


# ── exercises ───────────────────────────────────────────────────────
@router.get("/exercises", response_model=list[ExerciseOut])
async def list_exercises(_u: AdminUser, session: DB) -> list[Exercise]:
    return await _list(Exercise, session)


@router.post("/exercises", response_model=ExerciseOut, status_code=201)
async def create_exercise(payload: ExerciseIn, _u: AdminUser, session: DB) -> Exercise:
    return await _create(Exercise, payload, session)


@router.get("/exercises/{obj_id}", response_model=ExerciseOut)
async def get_exercise(obj_id: UUID, _u: AdminUser, session: DB) -> Exercise:
    return await _get(Exercise, obj_id, session)


@router.put("/exercises/{obj_id}", response_model=ExerciseOut)
async def update_exercise(
    obj_id: UUID, payload: ExerciseIn, _u: AdminUser, session: DB
) -> Exercise:
    return await _update(Exercise, obj_id, payload, session)


@router.delete("/exercises/{obj_id}", status_code=204)
async def delete_exercise(obj_id: UUID, _u: AdminUser, session: DB) -> None:
    await _delete(Exercise, obj_id, session)
