import pytest
from fastapi import HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import auth as auth_api
from app.api.deps import get_current_user, get_department_id, require_roles
from app.core.database import Base
from app.core.security import hash_password
from app.main import app, health, root
from app.models import AcademicYear, AppUser, Department, Program, Section, Student
from app.schemas.auth import LoginRequest


@pytest.fixture
def client_and_db(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    Base.metadata.create_all(engine)
    with TestingSession() as db:
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
            code="A",
        )
        db.add(section)
        db.flush()
        user = AppUser(
            role="student",
            login_id="ST100",
            email="student@example.test",
            password_hash=hash_password("demo-password"),
            is_active=True,
            department_id=department.id,
        )
        teacher = AppUser(
            role="teacher",
            login_id="teacher1",
            email=None,
            password_hash=hash_password("teacher-password"),
            is_active=True,
            department_id=department.id,
        )
        db.add_all([user, teacher])
        db.flush()
        db.add(
            Student(
                user_id=user.id,
                department_id=department.id,
                section_id=section.id,
                enrollment_no="ST100",
                roll_no="1",
                full_name="Demo Student",
            )
        )
        db.commit()
        student_user_id = user.id

    monkeypatch.setattr(auth_api, "_attempts", {})
    yield TestingSession, student_user_id
    engine.dispose()


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "client": ("127.0.0.1", 8000),
            "server": ("testserver", 80),
            "headers": [],
        }
    )


def test_login_and_auth_me(client_and_db):
    session_factory, student_id = client_and_db
    with session_factory() as db:
        result = auth_api.login(
            LoginRequest(login_id="ST100", password="demo-password"), _request(), db
        )
        user = get_current_user(
            HTTPAuthorizationCredentials(scheme="Bearer", credentials=result.access_token), db
        )
        me = auth_api.read_me(user)
        assert me.role == "student"
        assert me.id == student_id


def test_root_lists_api_entry_points(client_and_db):
    assert root().docs == "/docs"
    assert health().status == "ok"
    paths = app.openapi()["paths"]
    assert paths["/api/v1/auth/login"]["post"]["summary"]


def test_student_can_log_in_by_roll_number(client_and_db):
    session_factory, _ = client_and_db
    with session_factory() as db:
        result = auth_api.login(
            LoginRequest(login_id="1", password="demo-password"), _request(), db
        )
    assert result.user.login_id == "ST100"


def test_student_can_log_in_by_email(client_and_db):
    session_factory, _ = client_and_db
    with session_factory() as db:
        result = auth_api.login(
            LoginRequest(login_id="STUDENT@example.test", password="demo-password"),
            _request(),
            db,
        )
    assert result.user.role == "student"


def test_generic_login_failure_and_rate_limit(client_and_db):
    session_factory, _ = client_and_db
    with session_factory() as db:
        payload = LoginRequest(login_id="missing", password="wrong")
        with pytest.raises(HTTPException) as failed:
            auth_api.login(payload, _request(), db)
        assert failed.value.status_code == 401
        assert failed.value.detail["message"] == "Login failed."
        for _ in range(4):
            with pytest.raises(HTTPException):
                auth_api.login(payload, _request(), db)
        with pytest.raises(HTTPException) as limited:
            auth_api.login(payload, _request(), db)
        assert limited.value.status_code == 429


def test_role_dependency_rejects_student_from_teacher_route(client_and_db):
    session_factory, student_id = client_and_db
    with session_factory() as db:
        student = db.get(AppUser, student_id)
        with pytest.raises(HTTPException) as error:
            require_roles("teacher")(student)
        assert error.value.status_code == 403


def test_department_scope_comes_from_authenticated_user(client_and_db):
    session_factory, student_id = client_and_db
    with session_factory() as db:
        student = db.get(AppUser, student_id)
        assert get_department_id(student) == student.department_id
