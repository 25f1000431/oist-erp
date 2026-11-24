from datetime import date, time, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import Base
from app.models import (
    AcademicYear,
    AppUser,
    AttendanceRecord,
    AuditLog,
    Course,
    Department,
    Faculty,
    Program,
    Section,
    Student,
    TeachingAssignment,
)
from app.schemas.teacher import (
    AttendanceDefaultPayload,
    AttendanceRecordInput,
    AttendanceRecordsPayload,
    SessionCreate,
    SessionPatch,
)
from app.services.teacher import (
    create_session,
    get_roster,
    get_session,
    list_classes,
    patch_session,
    save_attendance,
)


@pytest.fixture
def teacher_db():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    db = Session(engine, autoflush=False, expire_on_commit=False)
    department = Department(code="CSE", name="Computer Science")
    other_department = Department(code="ECE", name="Electronics")
    db.add_all([department, other_department])
    db.flush()
    year = AcademicYear(label="2026-27", is_current=True)
    program = Program(department_id=department.id, code="BTECH-CSE", name="B.Tech CSE")
    other_program = Program(department_id=other_department.id, code="BTECH-ECE", name="B.Tech ECE")
    db.add_all([year, program, other_program])
    db.flush()
    section_a = Section(
        program_id=program.id, academic_year_id=year.id, semester=5, name="A", code="OIST-CSE-V-A"
    )
    section_b = Section(
        program_id=program.id, academic_year_id=year.id, semester=5, name="B", code="OIST-CSE-V-B"
    )
    other_section = Section(
        program_id=other_program.id,
        academic_year_id=year.id,
        semester=5,
        name="A",
        code="OIST-ECE-V-A",
    )
    users = [
        AppUser(
            role="teacher",
            login_id="FAC001",
            password_hash="unused",
            is_active=True,
            department_id=department.id,
        ),
        AppUser(
            role="teacher",
            login_id="FAC002",
            password_hash="unused",
            is_active=True,
            department_id=department.id,
        ),
        AppUser(
            role="teacher",
            login_id="FAC101",
            password_hash="unused",
            is_active=True,
            department_id=other_department.id,
        ),
    ]
    db.add_all([section_a, section_b, other_section, *users])
    db.flush()
    faculty = [
        Faculty(
            user_id=users[0].id,
            department_id=department.id,
            employee_code="FAC001",
            full_name="Demo Teacher One",
            designation="Faculty",
        ),
        Faculty(
            user_id=users[1].id,
            department_id=department.id,
            employee_code="FAC002",
            full_name="Demo Teacher Two",
            designation="Faculty",
        ),
        Faculty(
            user_id=users[2].id,
            department_id=other_department.id,
            employee_code="FAC101",
            full_name="Demo Teacher Other",
            designation="Faculty",
        ),
    ]
    course = Course(
        department_id=department.id,
        semester=5,
        code="CS501",
        name="Theory of Computation",
        kind="theory",
    )
    other_course = Course(
        department_id=other_department.id, semester=5, code="EC501", name="Circuits", kind="theory"
    )
    db.add_all([*faculty, course, other_course])
    db.flush()
    assignments = [
        TeachingAssignment(
            course_id=course.id,
            section_id=section_a.id,
            faculty_id=faculty[0].id,
            academic_year_id=year.id,
        ),
        TeachingAssignment(
            course_id=course.id,
            section_id=section_b.id,
            faculty_id=faculty[1].id,
            academic_year_id=year.id,
        ),
        TeachingAssignment(
            course_id=other_course.id,
            section_id=other_section.id,
            faculty_id=faculty[2].id,
            academic_year_id=year.id,
        ),
    ]
    db.add_all(assignments)
    db.flush()
    students = []
    for index in range(3):
        student_user = AppUser(
            role="student",
            login_id=f"{index + 1}",
            password_hash="unused",
            is_active=True,
            department_id=department.id,
        )
        db.add(student_user)
        db.flush()
        student = Student(
            user_id=student_user.id,
            department_id=department.id,
            section_id=section_a.id,
            roll_no=str(index + 1),
            full_name=f"Demo Student {index + 1}",
        )
        db.add(student)
        students.append(student)
    db.commit()
    yield (
        db,
        users[0],
        users[1],
        users[2],
        department.id,
        other_department.id,
        assignments[0],
        assignments[1],
        students,
    )
    db.close()
    engine.dispose()


def test_teacher_scope_classes_session_and_roster(teacher_db):
    (
        db,
        teacher,
        other_teacher,
        cross_department_teacher,
        cse_id,
        ece_id,
        assignment,
        other_assignment,
        students,
    ) = teacher_db
    classes = list_classes(db, teacher, cse_id)
    assert [row.teaching_assignment_id for row in classes] == [assignment.id]
    session = create_session(
        db,
        teacher,
        cse_id,
        SessionCreate(
            teaching_assignment_id=assignment.id,
            session_date=date.today(),
            start_time=time(9),
            end_time=time(10),
            topic="Revision",
        ),
    )
    assert len(get_roster(db, teacher, cse_id, session.id)) == 3
    for actor, department_id in [(other_teacher, cse_id), (cross_department_teacher, ece_id)]:
        with pytest.raises(HTTPException) as exc:
            get_session(db, actor, department_id, session.id)
        assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        save_attendance(
            db,
            other_teacher,
            cse_id,
            session.id,
            AttendanceDefaultPayload(default_status="present"),
        )
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        patch_session(db, other_teacher, cse_id, session.id, SessionPatch(topic="Changed"))
    assert exc.value.status_code == 404
    with pytest.raises(HTTPException) as exc:
        create_session(
            db,
            teacher,
            cse_id,
            SessionCreate(
                teaching_assignment_id=other_assignment.id,
                session_date=date.today(),
                start_time=time(11),
                end_time=time(12),
            ),
        )
    assert exc.value.status_code == 404


def test_dry_run_does_not_write_and_attendance_save_is_idempotent_audited(teacher_db):
    db, teacher, _, _, cse_id, _, assignment, _, students = teacher_db
    session = create_session(
        db,
        teacher,
        cse_id,
        SessionCreate(
            teaching_assignment_id=assignment.id,
            session_date=date.today(),
            start_time=time(9),
            end_time=time(10),
        ),
    )
    payload = AttendanceDefaultPayload(default_status="present", absent_roll_nos=["2"])
    preview = save_attendance(db, teacher, cse_id, session.id, payload, dry_run=True)
    assert preview == {
        "saved": False,
        "present": 2,
        "absent": 1,
        "total": 3,
        "diff": [
            {"roll_no": "1", "name": "Demo Student 1", "from": None, "to": "present"},
            {"roll_no": "2", "name": "Demo Student 2", "from": None, "to": "absent"},
            {"roll_no": "3", "name": "Demo Student 3", "from": None, "to": "present"},
        ],
    }
    assert db.scalar(select(func.count()).select_from(AttendanceRecord)) == 0
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 1  # session creation only
    first_save = save_attendance(db, teacher, cse_id, session.id, payload)
    second_save = save_attendance(db, teacher, cse_id, session.id, payload)
    assert first_save["saved"] and second_save["saved"]
    assert db.scalar(select(func.count()).select_from(AttendanceRecord)) == len(students)
    assert db.scalar(select(func.count()).select_from(AuditLog)) == 3
    record_statuses = db.scalars(
        select(AttendanceRecord.status).order_by(AttendanceRecord.student_id)
    ).all()
    assert record_statuses == ["present", "absent", "present"]


def test_attendance_requires_complete_valid_roster_and_rejects_duplicate_session(teacher_db):
    db, teacher, _, _, cse_id, _, assignment, _, _ = teacher_db
    session = create_session(
        db,
        teacher,
        cse_id,
        SessionCreate(
            teaching_assignment_id=assignment.id,
            session_date=date.today(),
            start_time=time(9),
            end_time=time(10),
        ),
    )
    partial = AttendanceRecordsPayload(
        records=[AttendanceRecordInput(roll_no="1", status="present")]
    )
    with pytest.raises(HTTPException) as exc:
        save_attendance(db, teacher, cse_id, session.id, partial)
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        create_session(
            db,
            teacher,
            cse_id,
            SessionCreate(
                teaching_assignment_id=assignment.id,
                session_date=date.today(),
                start_time=time(9),
                end_time=time(10),
            ),
        )
    assert exc.value.status_code == 409


def test_backdate_and_time_validation(teacher_db):
    db, teacher, _, _, cse_id, _, assignment, _, _ = teacher_db
    too_old = date.today() - timedelta(days=15)
    with pytest.raises(HTTPException) as exc:
        create_session(
            db,
            teacher,
            cse_id,
            SessionCreate(
                teaching_assignment_id=assignment.id,
                session_date=too_old,
                start_time=time(9),
                end_time=time(10),
            ),
        )
    assert exc.value.status_code == 422
    with pytest.raises(HTTPException) as exc:
        create_session(
            db,
            teacher,
            cse_id,
            SessionCreate(
                teaching_assignment_id=assignment.id,
                session_date=date.today(),
                start_time=time(10),
                end_time=time(10),
            ),
        )
    assert exc.value.status_code == 422
