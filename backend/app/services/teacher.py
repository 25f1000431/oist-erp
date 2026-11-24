import json
from datetime import UTC, date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.constants import BACKDATE_DAYS
from app.models import (
    AcademicYear,
    AppUser,
    AttendanceRecord,
    AuditLog,
    ClassSession,
    Course,
    Faculty,
    Program,
    Section,
    Student,
    TeachingAssignment,
)
from app.schemas.teacher import (
    AttendanceDefaultPayload,
    AttendanceRecordsPayload,
    RosterStudent,
    SessionCreate,
    SessionPatch,
    SessionResponse,
    TeacherClassResponse,
    TeacherCourse,
    TeacherSection,
    TeacherSessionListItem,
)

LOCAL_TZ = ZoneInfo("Asia/Kolkata")


def _error(status_code: int, code: str, message: str, details=None):
    raise HTTPException(
        status_code=status_code,
        detail={"code": code, "message": message, "details": details},
    )


def _audit(
    db: Session,
    actor: AppUser,
    action: str,
    entity_type: str,
    entity_id: int,
    before: dict | list | None,
    after: dict | list | None,
) -> None:
    db.add(
        AuditLog(
            actor_user_id=actor.id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=json.dumps(before, sort_keys=True) if before is not None else None,
            after_json=json.dumps(after, sort_keys=True) if after is not None else None,
            created_at=datetime.now(UTC),
        )
    )


def _today() -> date:
    return datetime.now(LOCAL_TZ).date()


def _validate_date(session_date: date) -> None:
    today = _today()
    if session_date > today:
        _error(422, "future_session", "Session date cannot be in the future.")
    if session_date < today - timedelta(days=BACKDATE_DAYS):
        _error(
            422,
            "backdate_window_exceeded",
            f"Session date must be within the last {BACKDATE_DAYS} days.",
        )


def _validate_teacher_edit_window(session: ClassSession) -> None:
    if session.session_date < _today() - timedelta(days=BACKDATE_DAYS):
        _error(403, "edit_window_expired", "Attendance edit window has expired.")


def _assignment_query(department_id: int, faculty_id: int | None = None):
    query = (
        select(TeachingAssignment, Course, Section, AcademicYear)
        .join(Course, Course.id == TeachingAssignment.course_id)
        .join(Section, Section.id == TeachingAssignment.section_id)
        .join(Program, Program.id == Section.program_id)
        .join(AcademicYear, AcademicYear.id == TeachingAssignment.academic_year_id)
        .join(Faculty, Faculty.id == TeachingAssignment.faculty_id)
        .where(
            Faculty.department_id == department_id,
            Course.department_id == department_id,
            Program.department_id == department_id,
        )
    )
    if faculty_id is not None:
        query = query.where(TeachingAssignment.faculty_id == faculty_id)
    return query


def _session_query(department_id: int, session_id: int, faculty_id: int | None = None):
    query = (
        select(ClassSession, TeachingAssignment, Course, Section, AcademicYear)
        .join(
            TeachingAssignment,
            TeachingAssignment.id == ClassSession.teaching_assignment_id,
        )
        .join(Course, Course.id == TeachingAssignment.course_id)
        .join(Section, Section.id == TeachingAssignment.section_id)
        .join(Program, Program.id == Section.program_id)
        .join(AcademicYear, AcademicYear.id == TeachingAssignment.academic_year_id)
        .join(Faculty, Faculty.id == TeachingAssignment.faculty_id)
        .where(
            ClassSession.id == session_id,
            Faculty.department_id == department_id,
            Course.department_id == department_id,
            Program.department_id == department_id,
        )
    )
    if faculty_id is not None:
        query = query.where(TeachingAssignment.faculty_id == faculty_id)
    return query


def _course(course: Course) -> TeacherCourse:
    return TeacherCourse(id=course.id, code=course.code, name=course.name, kind=course.kind)


def _section(section: Section, year: AcademicYear) -> TeacherSection:
    return TeacherSection(
        id=section.id,
        name=section.name,
        code=section.code,
        semester=section.semester,
        academic_year=year.label,
    )


def _session_response(row) -> SessionResponse:
    session, assignment, course, section, year = row
    return SessionResponse(
        id=session.id,
        teaching_assignment_id=assignment.id,
        course=_course(course),
        section=_section(section, year),
        session_date=session.session_date,
        start_time=session.start_time,
        end_time=session.end_time,
        topic=session.topic,
        status=session.status,
        created_at=session.created_at,
        attendance_updated_at=session.attendance_updated_at,
    )


def _ensure_time_order(start_time: time, end_time: time) -> None:
    if end_time <= start_time:
        _error(422, "invalid_time_range", "End time must be later than start time.")


def _get_teacher_faculty(db: Session, user: AppUser, department_id: int) -> Faculty:
    faculty = db.scalar(
        select(Faculty).where(
            Faculty.user_id == user.id,
            Faculty.department_id == department_id,
        )
    )
    if faculty is None:
        _error(403, "forbidden", "No faculty profile is assigned to this account.")
    return faculty


def list_classes(db: Session, user: AppUser, department_id: int) -> list[TeacherClassResponse]:
    faculty = _get_teacher_faculty(db, user, department_id)
    rows = db.execute(_assignment_query(department_id, faculty.id)).all()
    result = []
    for assignment, course, section, year in rows:
        sessions = db.scalars(
            select(ClassSession).where(ClassSession.teaching_assignment_id == assignment.id)
        ).all()
        result.append(
            TeacherClassResponse(
                teaching_assignment_id=assignment.id,
                course=_course(course),
                section=_section(section, year),
                last_session=max((item.session_date for item in sessions), default=None),
                pending_attendance_count=sum(item.status == "scheduled" for item in sessions),
            )
        )
    return result


def list_sessions(
    db: Session,
    user: AppUser,
    department_id: int,
    teaching_assignment_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    status: str | None = None,
) -> list[TeacherSessionListItem]:
    faculty = _get_teacher_faculty(db, user, department_id)
    query = (
        select(ClassSession, TeachingAssignment, Course, Section, AcademicYear)
        .join(TeachingAssignment, TeachingAssignment.id == ClassSession.teaching_assignment_id)
        .join(Course, Course.id == TeachingAssignment.course_id)
        .join(Section, Section.id == TeachingAssignment.section_id)
        .join(Program, Program.id == Section.program_id)
        .join(AcademicYear, AcademicYear.id == TeachingAssignment.academic_year_id)
        .join(Faculty, Faculty.id == TeachingAssignment.faculty_id)
        .where(
            Faculty.department_id == department_id,
            Course.department_id == department_id,
            Program.department_id == department_id,
            TeachingAssignment.faculty_id == faculty.id,
        )
    )
    if teaching_assignment_id is not None:
        query = query.where(TeachingAssignment.id == teaching_assignment_id)
    if date_from is not None:
        query = query.where(ClassSession.session_date >= date_from)
    if date_to is not None:
        query = query.where(ClassSession.session_date <= date_to)
    if status is not None:
        query = query.where(ClassSession.status == status)
    rows = db.execute(
        query.order_by(ClassSession.session_date.desc(), ClassSession.start_time)
    ).all()
    return [
        TeacherSessionListItem(
            id=session.id,
            teaching_assignment_id=assignment.id,
            course=_course(course),
            section=_section(section, year),
            session_date=session.session_date,
            start_time=session.start_time,
            end_time=session.end_time,
            topic=session.topic,
            status=session.status,
        )
        for session, assignment, course, section, year in rows
    ]


def create_session(
    db: Session, user: AppUser, department_id: int, payload: SessionCreate
) -> SessionResponse:
    faculty = _get_teacher_faculty(db, user, department_id)
    _validate_date(payload.session_date)
    _ensure_time_order(payload.start_time, payload.end_time)
    assignment_row = db.execute(
        _assignment_query(department_id, faculty.id).where(
            TeachingAssignment.id == payload.teaching_assignment_id
        )
    ).first()
    if assignment_row is None:
        _error(404, "class_not_found", "Teaching assignment was not found.")
    duplicate = db.scalar(
        select(ClassSession.id).where(
            ClassSession.teaching_assignment_id == payload.teaching_assignment_id,
            ClassSession.session_date == payload.session_date,
            ClassSession.start_time == payload.start_time,
        )
    )
    if duplicate is not None:
        _error(
            409,
            "duplicate_session",
            "A session already exists for that class, date, and start time.",
        )
    session = ClassSession(
        teaching_assignment_id=payload.teaching_assignment_id,
        session_date=payload.session_date,
        start_time=payload.start_time,
        end_time=payload.end_time,
        topic=payload.topic,
        status="scheduled",
        created_by=user.id,
        created_at=datetime.now(UTC),
    )
    db.add(session)
    db.flush()
    _audit(
        db,
        user,
        "create",
        "class_session",
        session.id,
        None,
        {
            "teaching_assignment_id": payload.teaching_assignment_id,
            "session_date": payload.session_date.isoformat(),
            "start_time": payload.start_time.isoformat(),
            "end_time": payload.end_time.isoformat(),
            "topic": payload.topic,
            "status": "scheduled",
        },
    )
    db.commit()
    row = db.execute(_session_query(department_id, session.id, faculty.id)).one()
    return _session_response(row)


def get_session(db: Session, user: AppUser, department_id: int, session_id: int) -> SessionResponse:
    faculty_id = None
    if user.role == "teacher":
        faculty_id = _get_teacher_faculty(db, user, department_id).id
    row = db.execute(_session_query(department_id, session_id, faculty_id)).first()
    if row is None:
        _error(404, "session_not_found", "Session was not found.")
    return _session_response(row)


def patch_session(
    db: Session,
    user: AppUser,
    department_id: int,
    session_id: int,
    payload: SessionPatch,
) -> SessionResponse:
    faculty_id = None
    if user.role == "teacher":
        faculty_id = _get_teacher_faculty(db, user, department_id).id
    row = db.execute(_session_query(department_id, session_id, faculty_id)).first()
    if row is None:
        _error(404, "session_not_found", "Session was not found.")
    session = row[0]
    if session.status == "attendance_updated":
        if user.role == "teacher":
            _validate_teacher_edit_window(session)
    changes = payload.model_dump(exclude_unset=True)
    next_date = changes.get("session_date", session.session_date)
    next_start = changes.get("start_time", session.start_time)
    next_end = changes.get("end_time", session.end_time)
    _validate_date(next_date)
    _ensure_time_order(next_start, next_end)
    before = {
        "session_date": session.session_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "topic": session.topic,
        "status": session.status,
    }
    for field, value in changes.items():
        setattr(session, field, value)
    after = {
        "session_date": session.session_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "topic": session.topic,
        "status": session.status,
    }
    _audit(db, user, "update", "class_session", session.id, before, after)
    db.commit()
    refreshed = db.execute(_session_query(department_id, session.id, faculty_id)).one()
    return _session_response(refreshed)


def delete_session(db: Session, user: AppUser, department_id: int, session_id: int) -> None:
    faculty_id = _get_teacher_faculty(db, user, department_id).id
    row = db.execute(_session_query(department_id, session_id, faculty_id)).first()
    if row is None:
        _error(404, "session_not_found", "Session was not found.")
    session = row[0]
    records_exist = db.scalar(
        select(AttendanceRecord.id).where(AttendanceRecord.session_id == session.id).limit(1)
    )
    if session.status != "scheduled" or records_exist is not None:
        _error(
            409,
            "session_has_attendance",
            "Only scheduled sessions without attendance can be deleted.",
        )
    before = {
        "teaching_assignment_id": session.teaching_assignment_id,
        "session_date": session.session_date.isoformat(),
        "start_time": session.start_time.isoformat(),
        "end_time": session.end_time.isoformat(),
        "topic": session.topic,
        "status": session.status,
    }
    _audit(db, user, "delete", "class_session", session.id, before, None)
    db.delete(session)
    db.commit()


def get_roster(
    db: Session, user: AppUser, department_id: int, session_id: int
) -> list[RosterStudent]:
    faculty = _get_teacher_faculty(db, user, department_id)
    row = db.execute(_session_query(department_id, session_id, faculty.id)).first()
    if row is None:
        _error(404, "session_not_found", "Session was not found.")
    section_id = row[3].id
    records = {
        record.student_id: record.status
        for record in db.scalars(
            select(AttendanceRecord)
            .join(ClassSession, ClassSession.id == AttendanceRecord.session_id)
            .where(ClassSession.id == session_id)
        ).all()
    }
    students = db.scalars(
        select(Student)
        .where(Student.section_id == section_id, Student.department_id == department_id)
        .order_by(Student.roll_no)
    ).all()
    return [
        RosterStudent(
            student_id=student.id,
            roll_no=student.roll_no,
            full_name=student.full_name,
            status=records.get(student.id),
        )
        for student in students
    ]


def _desired_records(
    payload: AttendanceRecordsPayload | AttendanceDefaultPayload,
    students: list[Student],
) -> dict[int, str]:
    by_roll = {student.roll_no: student for student in students}
    if isinstance(payload, AttendanceRecordsPayload):
        roll_values = [record.roll_no.strip() for record in payload.records]
        if len(roll_values) != len(set(roll_values)):
            _error(422, "duplicate_roll_no", "Attendance payload contains a duplicate roll number.")
        unknown = sorted(set(roll_values) - set(by_roll))
        missing = sorted(set(by_roll) - set(roll_values))
        if unknown or missing:
            _error(
                422,
                "incomplete_roster",
                "Attendance must include every student in this section exactly once.",
                {"unknown_roll_nos": unknown, "missing_roll_nos": missing},
            )
        return {by_roll[record.roll_no.strip()].id: record.status for record in payload.records}
    absent_rolls = [roll.strip() for roll in payload.absent_roll_nos]
    if len(absent_rolls) != len(set(absent_rolls)):
        _error(
            422, "duplicate_roll_no", "Attendance payload contains a duplicate absent roll number."
        )
    unknown = sorted(set(absent_rolls) - set(by_roll))
    if unknown:
        _error(
            422,
            "unknown_roll_no",
            "Absent roll number is not in this section.",
            {"unknown_roll_nos": unknown},
        )
    return {
        student.id: ("absent" if student.roll_no in absent_rolls else payload.default_status)
        for student in students
    }


def save_attendance(
    db: Session,
    user: AppUser,
    department_id: int,
    session_id: int,
    payload: AttendanceRecordsPayload | AttendanceDefaultPayload,
    dry_run: bool = False,
) -> dict:
    faculty_id = None
    if user.role == "teacher":
        faculty_id = _get_teacher_faculty(db, user, department_id).id
    row = db.execute(_session_query(department_id, session_id, faculty_id)).first()
    if row is None:
        _error(404, "session_not_found", "Session was not found.")
    session, assignment, _, section, _ = row
    if user.role == "teacher" and session.status == "attendance_updated":
        _validate_teacher_edit_window(session)
    students = db.scalars(
        select(Student)
        .where(Student.section_id == section.id, Student.department_id == department_id)
        .order_by(Student.roll_no)
    ).all()
    desired = _desired_records(payload, students)
    existing = {
        record.student_id: record
        for record in db.scalars(
            select(AttendanceRecord).where(AttendanceRecord.session_id == session.id)
        ).all()
    }
    diff = []
    for student in students:
        previous = existing.get(student.id)
        previous_status = previous.status if previous else None
        next_status = desired[student.id]
        if previous_status != next_status:
            diff.append(
                {
                    "roll_no": student.roll_no,
                    "name": student.full_name,
                    "from": previous_status,
                    "to": next_status,
                }
            )
    present = sum(value == "present" for value in desired.values())
    summary = {"present": present, "absent": len(desired) - present, "total": len(desired)}
    if dry_run:
        return {"saved": False, **summary, "diff": diff}

    before = [
        {"roll_no": student.roll_no, "status": existing[student.id].status}
        for student in students
        if student.id in existing
    ]
    now = datetime.now(UTC)
    for student in students:
        status_value = desired[student.id]
        record = existing.get(student.id)
        if record is None:
            db.add(
                AttendanceRecord(
                    session_id=session.id,
                    student_id=student.id,
                    status=status_value,
                    marked_by=user.id,
                    updated_at=now,
                )
            )
        else:
            record.status = status_value
            record.marked_by = user.id
            record.updated_at = now
    session.status = "attendance_updated"
    session.attendance_updated_at = now
    session.attendance_updated_by = user.id
    after = [{"roll_no": student.roll_no, "status": desired[student.id]} for student in students]
    _audit(db, user, "save_attendance", "class_session", session.id, before, after)
    db.commit()
    return {"saved": True, **summary, "diff": diff}
