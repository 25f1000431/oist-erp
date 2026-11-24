from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_department_id, require_roles
from app.core.database import get_db
from app.models import AppUser
from app.schemas.student import (
    AssignmentResponse,
    AttendanceSessionResponse,
    AttendanceSummaryResponse,
    FeeRecordResponse,
    ResultResponse,
    StudentProfileResponse,
)
from app.services import student as student_service

router = APIRouter(prefix="/me", tags=["student"])
student_role = require_roles("student")


@router.get(
    "/profile",
    response_model=StudentProfileResponse,
    summary="Get the authenticated student's profile and section",
)
def read_profile(
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> StudentProfileResponse:
    return student_service.get_profile(db, user, department_id)


@router.get(
    "/attendance/summary",
    response_model=AttendanceSummaryResponse,
    summary="Get overall and course-wise attendance totals",
)
def read_attendance_summary(
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> AttendanceSummaryResponse:
    return student_service.get_attendance_summary(db, user, department_id)


@router.get(
    "/attendance/courses/{course_id}/sessions",
    response_model=list[AttendanceSessionResponse],
    summary="List updated attendance sessions for one of the student's courses",
)
def read_course_sessions(
    course_id: int,
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[AttendanceSessionResponse]:
    return student_service.get_course_sessions(db, user, department_id, course_id)


@router.get(
    "/fees",
    response_model=list[FeeRecordResponse],
    summary="List the authenticated student's fee records",
)
def read_fees(
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[FeeRecordResponse]:
    return student_service.get_fees(db, user, department_id)


@router.get(
    "/results",
    response_model=list[ResultResponse],
    summary="List the authenticated student's published results",
)
def read_results(
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[ResultResponse]:
    return student_service.get_results(db, user, department_id)


@router.get(
    "/assignments",
    response_model=list[AssignmentResponse],
    summary="List assignments for the authenticated student's section",
)
def read_assignments(
    user: AppUser = Depends(student_role),
    department_id: int = Depends(get_department_id),
    db: Session = Depends(get_db),
) -> list[AssignmentResponse]:
    return student_service.get_assignments(db, user, department_id)
