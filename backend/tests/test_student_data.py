import csv

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth as auth_api
from app.api.deps import get_current_user, get_department_id
from app.core.database import Base
from app.models import (
    AcademicYear,
    AppUser,
    AttendanceRecord,
    ClassSession,
    Course,
    Department,
    Faculty,
    Program,
    Section,
    Student,
    TeachingAssignment,
)
from app.schemas.auth import LoginRequest
from app.schemas.student import CourseIdentity
from app.seed import load_student_rows, seed_demo_data
from app.services.attendance import attendance_band, is_shortage, percentage
from app.services.student import (
    get_assignments,
    get_attendance_summary,
    get_course_sessions,
    get_fees,
    get_profile,
    get_results,
)


def _request():
    from fastapi import Request

    return Request(
        {
            "type": "http",
            "client": ("127.0.0.1", 8000),
            "server": ("testserver", 80),
            "headers": [],
        }
    )


@pytest.fixture
def seeded_database(tmp_path, monkeypatch):
    csv_path = tmp_path / "students.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "enrollment_no",
                "roll_no",
                "full_name",
                "gender",
                "email",
                "section",
                "aadhaar",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "enrollment_no": "SAMPLE001",
                "roll_no": "1",
                "full_name": "DEMO LEARNER ONE",
                "gender": "F",
                "email": "one@example.test",
                "section": "A",
                "aadhaar": "IGNORED-TEST-VALUE",
            }
        )
        writer.writerow(
            {
                "enrollment_no": "SAMPLE002",
                "roll_no": "2",
                "full_name": "Demo Learner Two",
                "gender": "M",
                "email": "two@example.test",
                "section": "A",
                "aadhaar": "IGNORED-TEST-VALUE",
            }
        )
        writer.writerow(
            {
                "enrollment_no": "SAMPLE003",
                "roll_no": "3",
                "full_name": "Demo Learner Three",
                "gender": "F",
                "email": "three@example.test",
                "section": "B",
                "aadhaar": "IGNORED-TEST-VALUE",
            }
        )

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with TestingSession() as db:
        counts_first = seed_demo_data(db, students_file=csv_path, password="demo-password")
        counts_second = seed_demo_data(db, students_file=csv_path, password="demo-password")
    assert counts_first == counts_second

    monkeypatch.setattr("app.api.auth._attempts", {})
    yield TestingSession, counts_first, csv_path
    engine.dispose()


def test_seed_is_idempotent_and_ignores_unapproved_column(seeded_database):
    session_factory, counts, csv_path = seeded_database
    rows = load_student_rows(csv_path)
    assert set(rows[0]) == {
        "enrollment_no",
        "roll_no",
        "full_name",
        "gender",
        "email",
        "section",
    }
    assert rows[0]["full_name"] == "Demo Learner One"
    with session_factory() as db:
        assert db.scalar(select(func.count()).select_from(Student)) == 3
        assert db.scalar(select(func.count()).select_from(ClassSession)) == counts["sessions"]
        assert "aadhaar" not in Student.__table__.columns
        assert db.scalar(select(func.count()).select_from(AttendanceRecord)) > 0


def test_seed_updates_existing_student_by_exact_name_when_enrollment_is_blank(
    seeded_database, tmp_path
):
    session_factory, _, source_path = seeded_database
    updated_path = tmp_path / "replacement.csv"
    original_rows = load_student_rows(source_path)
    original_rows[0]["enrollment_no"] = None
    original_rows[0]["roll_no"] = "101"
    with updated_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=original_rows[0].keys())
        writer.writeheader()
        writer.writerows(original_rows)
    with session_factory() as db:
        before = db.scalar(select(Student).where(Student.full_name == "Demo Learner One"))
        student_id = before.id
        seed_demo_data(db, students_file=updated_path, password="demo-password")
        after = db.get(Student, student_id)
        user = db.get(AppUser, after.user_id)
        assert db.scalar(select(func.count()).select_from(Student)) == 3
        assert after.roll_no == "101"
        assert after.enrollment_no is None
        assert user.login_id == "101"


def test_student_reads_are_scoped_to_the_authenticated_user(seeded_database):
    session_factory, _, _ = seeded_database
    with session_factory() as db:
        first_login = auth_api.login(
            LoginRequest(login_id="SAMPLE001", password="demo-password"), _request(), db
        )
        second_login = auth_api.login(
            LoginRequest(login_id="SAMPLE002", password="demo-password"), _request(), db
        )
        from fastapi.security import HTTPAuthorizationCredentials

        first = get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=first_login.access_token), db
        )
        second = get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=second_login.access_token), db
        )
        first_department = get_department_id(first)
        second_department = get_department_id(second)
        first_profile = get_profile(db, first, first_department)
        second_profile = get_profile(db, second, second_department)
        assert first_profile.student_id != second_profile.student_id
        assert first_profile.roll_no == "1"
        assert second_profile.roll_no == "2"
        summary = get_attendance_summary(db, first, first_department)
        course_id = next(course.course.id for course in summary.courses if course.total)
        sessions = get_course_sessions(db, first, first_department, course_id)
        assert sessions
        assert get_fees(db, first, first_department)
        assert get_results(db, first, first_department)
        assert get_assignments(db, first, first_department)


def test_attendance_percent_band_and_scheduled_exclusion():
    assert percentage(189, 262) == 72.14
    assert attendance_band(49.99) == "Critical"
    assert attendance_band(50) == "Watch"
    assert attendance_band(90) == "Safe"
    assert is_shortage(74.99)
    assert not is_shortage(75)
    assert percentage(0, 0) == 0


def test_attendance_service_matches_hand_computed_updated_sessions_only():
    engine = create_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        department = Department(code="CSE", name="Computer Science")
        db.add(department)
        db.flush()
        year = AcademicYear(label="2026-27", is_current=True)
        program = Program(department_id=department.id, code="BTECH-CSE", name="B.Tech CSE")
        db.add_all([year, program])
        db.flush()
        section = Section(
            program_id=program.id,
            academic_year_id=year.id,
            semester=5,
            name="A",
            code="OIST-CSE-V-A",
        )
        user = AppUser(
            role="student",
            login_id="1",
            email=None,
            password_hash="unused",
            is_active=True,
            department_id=department.id,
        )
        faculty_user = AppUser(
            role="teacher",
            login_id="FAC001",
            email=None,
            password_hash="unused",
            is_active=True,
            department_id=department.id,
        )
        db.add_all([section, user, faculty_user])
        db.flush()
        student = Student(
            user_id=user.id,
            department_id=department.id,
            section_id=section.id,
            enrollment_no=None,
            roll_no="1",
            full_name="Demo Student",
        )
        faculty = Faculty(
            user_id=faculty_user.id,
            department_id=department.id,
            employee_code="FAC001",
            full_name="Demo Faculty One",
            designation="Faculty",
        )
        course = Course(
            department_id=department.id,
            semester=5,
            code="CS501",
            name="Theory of Computation",
            kind="theory",
        )
        db.add_all([student, faculty, course])
        db.flush()
        assignment = TeachingAssignment(
            course_id=course.id,
            section_id=section.id,
            faculty_id=faculty.id,
            academic_year_id=year.id,
        )
        db.add(assignment)
        db.flush()
        from datetime import UTC, date, datetime, time

        updated = ClassSession(
            teaching_assignment_id=assignment.id,
            session_date=date(2026, 11, 2),
            start_time=time(9),
            end_time=time(10),
            topic="Updated session",
            status="attendance_updated",
            created_by=faculty_user.id,
            created_at=datetime(2026, 11, 2, 3, tzinfo=UTC),
        )
        scheduled = ClassSession(
            teaching_assignment_id=assignment.id,
            session_date=date(2026, 11, 3),
            start_time=time(9),
            end_time=time(10),
            topic="Pending session",
            status="scheduled",
            created_by=faculty_user.id,
            created_at=datetime(2026, 11, 3, 3, tzinfo=UTC),
        )
        db.add_all([updated, scheduled])
        db.flush()
        db.add_all(
            [
                AttendanceRecord(
                    session_id=updated.id,
                    student_id=student.id,
                    status="present",
                    marked_by=faculty_user.id,
                    updated_at=datetime(2026, 11, 2, 4, tzinfo=UTC),
                ),
            ]
        )
        db.commit()

        summary = get_attendance_summary(db, user, department.id)
        assert summary.overall.present == 1
        assert summary.overall.total == 1
        assert summary.overall.percent == 100
        assert summary.overall.formula == "Present 1 / Total 1"
        assert summary.courses[0].course == CourseIdentity(
            id=course.id, code="CS501", name="Theory of Computation"
        )
        assert summary.courses[0].present == 1
        assert summary.courses[0].total == 1
    engine.dispose()
