from datetime import date

from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy.orm import Session

from app.api.deps import get_department_id, require_roles
from app.core.database import get_db
from app.models import AppUser
from app.schemas.teacher import (
    AttendanceDefaultPayload,
    AttendanceRecordsPayload,
    AttendanceSaveResponse,
    RosterStudent,
    SessionCreate,
    SessionPatch,
    SessionResponse,
    TeacherClassResponse,
    TeacherSessionListItem,
)
from app.services import teacher as teacher_service

router = APIRouter(prefix="/teacher", tags=["teacher"])
teacher_role = require_roles("teacher")
attendance_editor_role = require_roles("teacher", "hod", "admin")


@router.get(
    "/classes",
    response_model=list[TeacherClassResponse],
    summary="List the authenticated teacher's assigned classes",
)
def read_classes(
    user: AppUser = Depends(teacher_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[TeacherClassResponse]:
    return teacher_service.list_classes(db, user, department_id)


@router.get(
    "/sessions",
    response_model=list[TeacherSessionListItem],
    summary="List the authenticated teacher's class sessions with optional filters",
)
def read_sessions(
    teaching_assignment_id: int | None = None,
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    session_status: str | None = Query(
        default=None, alias="status", pattern="^(scheduled|attendance_updated)$"
    ),
    user: AppUser = Depends(teacher_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[TeacherSessionListItem]:
    if date_from and date_to and date_from > date_to:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail={"code": "invalid_date_range", "message": "from must be on or before to."},
        )
    return teacher_service.list_sessions(
        db, user, department_id, teaching_assignment_id, date_from, date_to, session_status
    )


@router.post(
    "/sessions",
    response_model=SessionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a scheduled session for one of the teacher's classes",
)
def create_session(
    payload: SessionCreate,
    user: AppUser = Depends(teacher_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return teacher_service.create_session(db, user, department_id, payload)


@router.get(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Get an assigned class session",
)
def read_session(
    session_id: int,
    user: AppUser = Depends(attendance_editor_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return teacher_service.get_session(db, user, department_id, session_id)


@router.patch(
    "/sessions/{session_id}",
    response_model=SessionResponse,
    summary="Edit session details within the attendance edit window",
)
def update_session(
    session_id: int,
    payload: SessionPatch,
    user: AppUser = Depends(attendance_editor_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> SessionResponse:
    return teacher_service.patch_session(db, user, department_id, session_id, payload)


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a scheduled session that has no attendance records",
)
def remove_session(
    session_id: int,
    user: AppUser = Depends(teacher_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> Response:
    teacher_service.delete_session(db, user, department_id, session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get(
    "/sessions/{session_id}/roster",
    response_model=list[RosterStudent],
    summary="Get the complete section roster and current session attendance",
)
def read_roster(
    session_id: int,
    user: AppUser = Depends(teacher_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[RosterStudent]:
    return teacher_service.get_roster(db, user, department_id, session_id)


@router.put(
    "/sessions/{session_id}/attendance",
    response_model=AttendanceSaveResponse,
    summary="Preview or save a complete attendance roster for a class session",
)
def put_attendance(
    session_id: int,
    payload: AttendanceRecordsPayload | AttendanceDefaultPayload,
    dry_run: bool = Query(default=False),
    user: AppUser = Depends(attendance_editor_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> AttendanceSaveResponse:
    result = teacher_service.save_attendance(
        db, user, department_id, session_id, payload, dry_run=dry_run
    )
    return AttendanceSaveResponse(**result)
