import json
import os
import uuid
import zipfile
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import and_, case, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import (
    AcademicYear,
    AppUser,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    AttendanceRecord,
    AuditLog,
    ClassSession,
    Course,
    Department,
    FeeRecord,
    Program,
    Section,
    Student,
    TeachingAssignment,
)
from app.schemas.student import (
    AssignmentResponse,
    AssignmentSubmissionResponse,
    AttendanceSessionResponse,
    AttendanceSummaryResponse,
    AttendanceTotals,
    CourseAttendanceSummary,
    CourseIdentity,
    FeeRecordResponse,
    ResultResponse,
    StudentProfileResponse,
)
from app.services.attendance import attendance_band, is_shortage, percentage


def _student(db: Session, user_id: int, department_id: int) -> Student:
    student = db.scalar(
        select(Student).where(
            Student.user_id == user_id,
            Student.department_id == department_id,
        )
    )
    if student is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "student_profile_not_found", "message": "Student profile not found."},
        )
    return student


def get_profile(db: Session, user: AppUser, department_id: int) -> StudentProfileResponse:
    student = _student(db, user.id, department_id)
    row = db.execute(
        select(Student, Section, Program, AcademicYear, Department)
        .join(Section, Section.id == Student.section_id)
        .join(Program, Program.id == Section.program_id)
        .join(AcademicYear, AcademicYear.id == Section.academic_year_id)
        .join(Department, Department.id == Student.department_id)
        .where(
            Student.id == student.id,
            Department.id == department_id,
            Program.department_id == department_id,
        )
    ).one()
    student_row, section, program, year, department = row
    return StudentProfileResponse(
        student_id=student_row.id,
        enrollment_no=student_row.enrollment_no,
        roll_no=student_row.roll_no,
        full_name=student_row.full_name,
        gender=student_row.gender,
        email=student_row.email,
        department_code=department.code,
        program_name=program.name,
        semester=section.semester,
        section_name=section.name,
        section_code=section.code,
        academic_year=year.label,
    )


def _attendance_totals(present: int, total: int, *, formula: bool = False) -> AttendanceTotals:
    percent = percentage(present, total)
    return AttendanceTotals(
        present=present,
        total=total,
        percent=percent,
        band=attendance_band(percent),
        shortage=is_shortage(percent),
        formula=f"Present {present} / Total {total}" if formula else "",
    )


def get_attendance_summary(
    db: Session, user: AppUser, department_id: int
) -> AttendanceSummaryResponse:
    student = _student(db, user.id, department_id)
    present_expr = func.coalesce(
        func.sum(case((AttendanceRecord.status == "present", 1), else_=0)), 0
    )
    rows = db.execute(
        select(
            Course.id,
            Course.code,
            Course.name,
            Course.kind,
            func.count(ClassSession.id).label("total"),
            present_expr.label("present"),
        )
        .join(TeachingAssignment, TeachingAssignment.course_id == Course.id)
        .join(Section, Section.id == TeachingAssignment.section_id)
        .outerjoin(
            ClassSession,
            and_(
                ClassSession.teaching_assignment_id == TeachingAssignment.id,
                ClassSession.status == "attendance_updated",
            ),
        )
        .outerjoin(
            AttendanceRecord,
            and_(
                AttendanceRecord.session_id == ClassSession.id,
                AttendanceRecord.student_id == student.id,
            ),
        )
        .where(
            Course.department_id == department_id,
            TeachingAssignment.section_id == student.section_id,
        )
        .group_by(Course.id, Course.code, Course.name, Course.kind)
        .order_by(Course.code, Course.name)
    ).all()

    courses = []
    all_present = 0
    all_total = 0
    for row in rows:
        present, total = int(row.present or 0), int(row.total or 0)
        percent = percentage(present, total)
        all_present += present
        all_total += total
        courses.append(
            CourseAttendanceSummary(
                course=CourseIdentity(id=row.id, code=row.code, name=row.name),
                kind=row.kind,
                present=present,
                total=total,
                percent=percent,
                band=attendance_band(percent),
                shortage=is_shortage(percent),
            )
        )
    return AttendanceSummaryResponse(
        overall=_attendance_totals(all_present, all_total, formula=True),
        courses=courses,
    )


def get_course_sessions(
    db: Session, user: AppUser, department_id: int, course_id: int
) -> list[AttendanceSessionResponse]:
    student = _student(db, user.id, department_id)
    assignment_exists = db.scalar(
        select(TeachingAssignment.id)
        .join(Course, Course.id == TeachingAssignment.course_id)
        .where(
            TeachingAssignment.section_id == student.section_id,
            Course.id == course_id,
            Course.department_id == department_id,
        )
    )
    if assignment_exists is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "course_not_found", "message": "Course not found for this section."},
        )
    rows = db.execute(
        select(ClassSession, AttendanceRecord)
        .join(
            TeachingAssignment,
            TeachingAssignment.id == ClassSession.teaching_assignment_id,
        )
        .join(Course, Course.id == TeachingAssignment.course_id)
        .join(
            AttendanceRecord,
            and_(
                AttendanceRecord.session_id == ClassSession.id,
                AttendanceRecord.student_id == student.id,
            ),
        )
        .where(
            TeachingAssignment.section_id == student.section_id,
            Course.id == course_id,
            Course.department_id == department_id,
            ClassSession.status == "attendance_updated",
        )
        .order_by(ClassSession.session_date.desc(), ClassSession.start_time.desc())
    ).all()
    return [
        AttendanceSessionResponse(
            session_date=session.session_date,
            start_time=session.start_time,
            end_time=session.end_time,
            topic=session.topic,
            outcome="P" if record.status == "present" else "A",
        )
        for session, record in rows
    ]


def get_fees(db: Session, user: AppUser, department_id: int) -> list[FeeRecordResponse]:
    student = _student(db, user.id, department_id)
    current_year_id = db.scalar(
        select(Section.academic_year_id)
        .join(Program, Program.id == Section.program_id)
        .where(Section.id == student.section_id, Program.department_id == department_id)
    )
    if current_year_id is None:
        return []
    rows = db.execute(
        select(FeeRecord, AcademicYear)
        .join(AcademicYear, AcademicYear.id == FeeRecord.academic_year_id)
        .where(
            FeeRecord.student_id == student.id,
            FeeRecord.academic_year_id == current_year_id,
        )
        .order_by(AcademicYear.label.desc())
    ).all()
    return [
        FeeRecordResponse(
            academic_year=year.label,
            total_amount=fee.total_amount,
            paid_amount=fee.paid_amount,
            fine_amount=fee.fine_amount,
            pending_amount=fee.total_amount + fee.fine_amount - fee.paid_amount,
            due_date=fee.due_date,
        )
        for fee, year in rows
    ]


def get_results(db: Session, user: AppUser, department_id: int) -> list[ResultResponse]:
    student = _student(db, user.id, department_id)
    rows = db.execute(
        select(AssessmentResult, Course)
        .join(Course, Course.id == AssessmentResult.course_id)
        .where(
            AssessmentResult.student_id == student.id,
            Course.department_id == department_id,
        )
        .order_by(Course.code, Course.name, AssessmentResult.published_at, AssessmentResult.id)
    ).all()
    return [
        ResultResponse(
            course=CourseIdentity(id=course.id, code=course.code, name=course.name),
            exam_name=result.exam_name,
            max_marks=result.max_marks,
            marks_obtained=result.marks_obtained,
            published_at=result.published_at,
        )
        for result, course in rows
    ]


def get_assignments(db: Session, user: AppUser, department_id: int) -> list[AssignmentResponse]:
    student = _student(db, user.id, department_id)
    rows = db.execute(
        select(Assignment, Course, AssignmentSubmission)
        .join(Course, Course.id == Assignment.course_id)
        .outerjoin(
            AssignmentSubmission,
            and_(
                AssignmentSubmission.assignment_id == Assignment.id,
                AssignmentSubmission.student_id == student.id,
            ),
        )
        .where(
            Assignment.section_id == student.section_id,
            Course.department_id == department_id,
        )
        .order_by(Assignment.due_at, Course.code, Assignment.id)
    ).all()
    return [
        AssignmentResponse(
            id=assignment.id,
            course=CourseIdentity(id=course.id, code=course.code, name=course.name),
            title=assignment.title,
            description=assignment.description,
            due_at=assignment.due_at,
            max_marks=assignment.max_marks,
            status=submission.status if submission else "pending",
            submitted_at=submission.submitted_at if submission else None,
        )
        for assignment, course, submission in rows
    ]


MAX_SUBMISSION_BYTES = 5 * 1024 * 1024
ALLOWED_SUBMISSION_EXTENSIONS = {".pdf", ".zip", ".docx"}


def _validate_submission_file(filename: str, content: bytes) -> str:
    extension = Path(filename).suffix.casefold()
    if extension not in ALLOWED_SUBMISSION_EXTENSIONS:
        raise HTTPException(
            status_code=422,
            detail={"code": "unsupported_file_type", "message": "Upload a PDF, ZIP, or DOCX file."},
        )
    if not content:
        raise HTTPException(
            status_code=422,
            detail={"code": "empty_file", "message": "The uploaded file is empty."},
        )
    if len(content) > MAX_SUBMISSION_BYTES:
        raise HTTPException(
            status_code=413,
            detail={"code": "file_too_large", "message": "The file must be 5 MB or smaller."},
        )
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=422,
            detail={
                "code": "invalid_file_content",
                "message": "The file does not contain a valid PDF.",
            },
        )
    if extension in {".zip", ".docx"}:
        try:
            archive = zipfile.ZipFile(BytesIO(content))
            entries = archive.infolist()
            expanded_size = sum(entry.file_size for entry in entries)
            valid_archive = (
                len(entries) <= 2000
                and expanded_size <= 25 * 1024 * 1024
                and archive.testzip() is None
            )
            names = set(archive.namelist())
            archive.close()
        except (OSError, zipfile.BadZipFile, RuntimeError):
            valid_archive = False
            names = set()
        if not valid_archive or (
            extension == ".docx"
            and not {
                "[Content_Types].xml",
                "word/document.xml",
            }.issubset(names)
        ):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "invalid_file_content",
                    "message": "The file is not a valid ZIP or DOCX archive.",
                },
            )
    return extension[1:]


def submit_assignment(
    db: Session,
    user: AppUser,
    department_id: int,
    assignment_id: int,
    filename: str,
    content: bytes,
) -> AssignmentSubmissionResponse:
    extension = _validate_submission_file(filename, content)
    student = _student(db, user.id, department_id)
    assignment = db.scalar(
        select(Assignment)
        .join(Course, Course.id == Assignment.course_id)
        .where(
            Assignment.id == assignment_id,
            Assignment.section_id == student.section_id,
            Course.department_id == department_id,
        )
    )
    if assignment is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "assignment_not_found", "message": "Assignment not found."},
        )

    storage_root = Path(settings.upload_dir).expanduser().resolve()
    web_root = Path(__file__).resolve().parents[3] / "frontend" / "public"
    if storage_root == web_root or web_root in storage_root.parents:
        raise RuntimeError("UPLOAD_DIR must be outside the frontend web root.")
    storage_root.mkdir(parents=True, exist_ok=True, mode=0o700)

    file_key = uuid.uuid4().hex
    destination = storage_root / f"{file_key}.{extension}"
    temporary = storage_root / f".{file_key}.part"
    previous = db.scalar(
        select(AssignmentSubmission).where(
            AssignmentSubmission.assignment_id == assignment.id,
            AssignmentSubmission.student_id == student.id,
        )
    )
    old_path = Path(previous.file_path) if previous is not None else None
    submitted_at = datetime.now(UTC)
    before = None
    if previous is not None:
        before = {
            "status": previous.status,
            "submitted_at": previous.submitted_at.isoformat(),
        }

    try:
        file_descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(file_descriptor, "wb") as output:
            output.write(content)
        temporary.replace(destination)
        if previous is None:
            previous = AssignmentSubmission(
                assignment_id=assignment.id,
                student_id=student.id,
                file_path=str(destination),
                submitted_at=submitted_at,
                status="submitted",
            )
            db.add(previous)
        else:
            previous.file_path = str(destination)
            previous.submitted_at = submitted_at
            previous.status = "submitted"
        db.flush()
        db.add(
            AuditLog(
                actor_user_id=user.id,
                action="create" if before is None else "replace",
                entity_type="assignment_submission",
                entity_id=previous.id,
                before_json=json.dumps(before, sort_keys=True) if before else None,
                after_json=json.dumps(
                    {
                        "status": "submitted",
                        "submitted_at": submitted_at.isoformat(),
                        "file_type": extension,
                    },
                    sort_keys=True,
                ),
                created_at=submitted_at,
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        temporary.unlink(missing_ok=True)
        destination.unlink(missing_ok=True)
        raise

    if (
        old_path is not None
        and old_path.resolve().is_relative_to(storage_root)
        and old_path.resolve() != destination
    ):
        try:
            old_path.unlink(missing_ok=True)
        except OSError:
            pass
    return AssignmentSubmissionResponse(
        assignment_id=assignment.id,
        status="submitted",
        submitted_at=submitted_at,
    )
