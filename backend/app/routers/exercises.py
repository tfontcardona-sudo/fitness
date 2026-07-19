"""Biblioteca de ejercicios (F.3): filtros, alta de personalizados, edición
(video_url incluido) y archivado sin romper el historial."""


from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.deps import get_current_user
from app.models import Exercise
from app.schemas.entities import ExerciseIn, ExerciseOut, ExerciseUpdate
from app.services.audit import log_event
from app.services.storage import (
    VideoValidationError,
    delete_exercise_video,
    save_exercise_video,
)

router = APIRouter(
    prefix="/api/exercises", tags=["exercises"], dependencies=[Depends(get_current_user)]
)


def _get_or_404(db: Session, exercise_id: int) -> Exercise:
    ex = db.get(Exercise, exercise_id)
    if not ex:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Ejercicio no encontrado")
    return ex


@router.get("", response_model=list[ExerciseOut])
def list_exercises(
    db: Session = Depends(get_db),
    pattern: str | None = Query(default=None, description="movement_pattern exacto"),
    muscle: str | None = Query(default=None, description="músculo primario"),
    equipment: str | None = Query(default=None, description="requiere este equipamiento"),
    level_max: int | None = Query(default=None, ge=1, le=3, description="nivel mínimo ≤"),
    q: str | None = Query(default=None, min_length=2, description="busca en nombre/aliases"),
    include_archived: bool = Query(default=False),
) -> list[ExerciseOut]:
    stmt = select(Exercise).order_by(Exercise.muscle_primary, Exercise.canonical_name)
    if not include_archived:
        stmt = stmt.where(Exercise.archived.is_(False))
    if pattern:
        stmt = stmt.where(Exercise.movement_pattern == pattern)
    if muscle:
        stmt = stmt.where(Exercise.muscle_primary == muscle)
    if equipment:
        stmt = stmt.where(Exercise.equipment.any(equipment))
    if level_max:
        stmt = stmt.where(Exercise.level_min <= level_max)
    if q:
        like = f"%{q.strip()}%"
        stmt = stmt.where(
            Exercise.canonical_name.ilike(like) | Exercise.aliases.any(q.strip())
        )
    return [ExerciseOut.model_validate(e) for e in db.scalars(stmt)]


@router.get("/{exercise_id}", response_model=ExerciseOut)
def get_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    return ExerciseOut.model_validate(_get_or_404(db, exercise_id))


@router.post("", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
def create_exercise(body: ExerciseIn, db: Session = Depends(get_db)) -> ExerciseOut:
    if db.scalar(select(Exercise).where(Exercise.canonical_name == body.canonical_name)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un ejercicio con ese nombre")
    ex = Exercise(**body.model_dump())
    db.add(ex)
    db.flush()
    log_event(db, "exercise", ex.id, "exercise_created", {"name": ex.canonical_name})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.patch("/{exercise_id}", response_model=ExerciseOut)
def update_exercise(exercise_id: int, body: ExerciseUpdate, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    changes = body.model_dump(exclude_unset=True)
    for field, value in changes.items():
        setattr(ex, field, value)
    if changes:
        log_event(db, "exercise", ex.id, "exercise_updated", {"fields": sorted(changes)})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/video", response_model=ExerciseOut)
def upload_exercise_video(
    exercise_id: int,
    file: UploadFile = File(..., description="Vídeo del ejercicio (MP4, MOV, WebM…)"),
    db: Session = Depends(get_db),
) -> ExerciseOut:
    """Sube el VÍDEO del ejercicio como archivo (reemplaza el anterior). Tiene
    prioridad sobre el enlace externo (video_url) en portal y rutina."""
    ex = _get_or_404(db, exercise_id)
    try:
        ex.video_path = save_exercise_video(exercise_id, file.file, file.filename or "")
    except VideoValidationError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc)) from exc
    log_event(db, "exercise", ex.id, "exercise_video_uploaded", {"path": ex.video_path})
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.delete("/{exercise_id}/video", response_model=ExerciseOut)
def delete_exercise_video_endpoint(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    """Quita el vídeo subido del ejercicio (el enlace externo, si lo hay, queda)."""
    ex = _get_or_404(db, exercise_id)
    delete_exercise_video(exercise_id)
    ex.video_path = None
    log_event(db, "exercise", ex.id, "exercise_video_deleted", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/archive", response_model=ExerciseOut)
def archive_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = True
    log_event(db, "exercise", ex.id, "exercise_archived", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)


@router.post("/{exercise_id}/restore", response_model=ExerciseOut)
def restore_exercise(exercise_id: int, db: Session = Depends(get_db)) -> ExerciseOut:
    ex = _get_or_404(db, exercise_id)
    ex.archived = False
    log_event(db, "exercise", ex.id, "exercise_restored", None)
    db.commit()
    db.refresh(ex)
    return ExerciseOut.model_validate(ex)
