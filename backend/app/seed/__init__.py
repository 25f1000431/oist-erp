"""Idempotent synthetic ERP data loader."""

import csv
import random
import sys
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import Base, SessionLocal
from app.core.security import hash_password
from app.models import (
    AcademicYear,
    AppUser,
    AssessmentResult,
    Assignment,
    AssignmentSubmission,
    AttendanceRecord,
    ClassSession,
    Course,
    Department,
    Faculty,
    FeeRecord,
    Program,
    Section,
    Student,
    TeachingAssignment,
)
from app.seed.courses import COURSES, FACULTY, HISTORY_COURSE_KEYS

ROOT = Path(__file__).resolve().parents[2]
PRIVATE_STUDENTS = ROOT / "seed" / "private" / "students_2024_cse_A_B.csv"
SAMPLE_STUDENTS = ROOT / "seed" / "sample" / "students.sample.csv"
ALLOWED_STUDENT_FIELDS = (
    "enrollment_no",
    "roll_no",
    "full_name",
    "gender",
    "email",
    "section",
)
LOCAL_TZ = ZoneInfo("Asia/Kolkata")
COURSE_TOPICS = (
    "Core concepts",
    "Worked examples",
    "Problem solving",
    "Review and practice",
)


def _clean(value: str | None) -> str | None:
    value = (value or "").strip()
    return value or None


def _clean_name(value: str | None) -> str:
    name = (value or "").strip()
    if name.isupper() or name.islower():
        name = name.title()
    return name


def load_student_rows(path: Path) -> list[dict[str, str | None]]:
    """Read only the approved student fields plus the section routing field."""
    required = {"roll_no", "full_name", "section"}
    rows: list[dict[str, str | None]] = []
    roll_keys: set[tuple[str, str]] = set()
    enrollment_numbers: set[str] = set()
    with path.open(newline="", encoding="utf-8-sig") as source:
        reader = csv.DictReader(source)
        fields = set(reader.fieldnames or [])
        missing = required - fields
        if missing:
            raise ValueError(
                f"Student CSV is missing required columns: {', '.join(sorted(missing))}."
            )
        for line_number, raw in enumerate(reader, start=2):
            # Never copy arbitrary input columns into the returned row.
            row = {key: _clean(raw.get(key)) for key in ALLOWED_STUDENT_FIELDS}
            row["full_name"] = _clean_name(row["full_name"])
            section = row["section"]
            roll_no = row["roll_no"]
            if not row["full_name"] or not roll_no or section not in {"A", "B"}:
                raise ValueError(
                    f"Invalid name, roll number, or section on CSV line {line_number}."
                )
            roll_key = (section, roll_no)
            if roll_key in roll_keys:
                raise ValueError(f"Duplicate roll_no {roll_no!r} in section {section}.")
            roll_keys.add(roll_key)
            enrollment = row["enrollment_no"]
            if enrollment:
                if enrollment in enrollment_numbers:
                    raise ValueError(f"Duplicate enrollment_no {enrollment!r}.")
                enrollment_numbers.add(enrollment)
            rows.append(row)
    if not rows:
        raise ValueError("Student CSV contains no student rows.")
    return rows


def _upsert_user(
    db: Session,
    *,
    login_id: str,
    role: str,
    email: str | None,
    department_id: int,
    password_hash: str,
) -> AppUser:
    user = db.scalar(select(AppUser).where(AppUser.login_id == login_id))
    if user is None:
        user = AppUser(
            login_id=login_id,
            role=role,
            email=email,
            password_hash=password_hash,
            is_active=True,
            department_id=department_id,
        )
        db.add(user)
    else:
        user.role = role
        user.email = email
        user.password_hash = password_hash
        user.is_active = True
        user.department_id = department_id
    return user


def _student_match(
    db: Session, row: dict[str, str | None], section_id: int, department_id: int
) -> Student | None:
    enrollment = row["enrollment_no"]
    if enrollment:
        found = db.scalar(select(Student).where(Student.enrollment_no == enrollment))
        if found is not None:
            return found
    matches = list(
        db.scalars(
            select(Student).where(
                Student.department_id == department_id,
                Student.full_name == row["full_name"],
            )
        ).all()
    )
    same_section = [student for student in matches if student.section_id == section_id]
    matches = same_section or matches
    if len(matches) > 1:
        raise ValueError(
            f"Cannot safely match duplicate student name {row['full_name']!r}; "
            "provide enrollment_no."
        )
    return matches[0] if matches else None


def _load_students(
    db: Session,
    rows: list[dict[str, str | None]],
    *,
    department_id: int,
    sections: dict[str, Section],
    password_hash: str,
) -> None:
    matched: list[tuple[dict[str, str | None], Section, Student | None]] = []
    used_student_ids: set[int] = set()
    for row in rows:
        section = sections[row["section"]]
        student = _student_match(db, row, section.id, department_id)
        if student is not None and student.id in used_student_ids:
            raise ValueError(
                "Multiple CSV rows match the same existing student; add enrollment numbers."
            )
        if student is not None:
            used_student_ids.add(student.id)
        matched.append((row, section, student))

    # Free existing roll-based login IDs first, so simultaneous roll changes can be applied safely.
    for _, _, student in matched:
        if student is not None:
            user = db.get(AppUser, student.user_id)
            if user is not None:
                user.login_id = f"seed-update-{user.id}"
    db.flush()

    for row, section, student in matched:
        enrollment = row["enrollment_no"]
        roll_no = row["roll_no"]
        email = row["email"]
        login_id = enrollment or roll_no or email
        if not login_id:
            raise ValueError(f"Student {row['full_name']!r} has no usable login identifier.")
        conflict = db.scalar(select(AppUser).where(AppUser.login_id == login_id))
        if conflict is not None and (student is None or conflict.id != student.user_id):
            raise ValueError(f"Student login identifier {login_id!r} is already assigned.")
        if student is not None:
            user = db.get(AppUser, student.user_id)
            if user is None:
                raise ValueError("Existing student record has no account.")
            user.login_id = login_id
            user.role = "student"
            user.email = email
            user.password_hash = password_hash
            user.is_active = True
            user.department_id = department_id
            student.department_id = department_id
            student.section_id = section.id
            student.enrollment_no = enrollment
            student.roll_no = roll_no
            student.full_name = row["full_name"] or ""
            student.gender = row["gender"]
            student.email = email
        else:
            user = _upsert_user(
                db,
                login_id=login_id,
                role="student",
                email=email,
                department_id=department_id,
                password_hash=password_hash,
            )
            db.flush()
            db.add(
                Student(
                    user_id=user.id,
                    department_id=department_id,
                    section_id=section.id,
                    enrollment_no=enrollment,
                    roll_no=roll_no or "",
                    full_name=row["full_name"] or "",
                    gender=row["gender"],
                    email=email,
                )
            )
    db.flush()


def _ensure_reference_data(
    db: Session, password_hash: str
) -> tuple[
    Department, AcademicYear, dict[str, Section], dict[tuple[str, str], Course], dict[str, Faculty]
]:
    department = db.scalar(select(Department).where(Department.code == "CSE"))
    if department is None:
        department = Department(code="CSE", name="Computer Science and Engineering")
        db.add(department)
        db.flush()

    program = db.scalar(select(Program).where(Program.code == "BTECH-CSE"))
    if program is None:
        program = Program(
            department_id=department.id,
            code="BTECH-CSE",
            name="B.Tech (Computer Science and Engineering)",
        )
        db.add(program)
    else:
        program.department_id = department.id
        program.name = "B.Tech (Computer Science and Engineering)"

    year = db.scalar(select(AcademicYear).where(AcademicYear.label == "2026-27"))
    if year is None:
        year = AcademicYear(label="2026-27", is_current=True)
        db.add(year)
    else:
        year.is_current = True
    db.flush()

    # Only one academic year is current in the seeded department.
    db.query(AcademicYear).filter(AcademicYear.id != year.id).update(
        {AcademicYear.is_current: False}
    )
    sections: dict[str, Section] = {}
    for name, code in (("A", "OIST-CSE-V-A"), ("B", "OIST-CSE-V-B")):
        section = db.scalar(select(Section).where(Section.code == code))
        if section is None:
            section = Section(
                program_id=program.id,
                academic_year_id=year.id,
                semester=5,
                name=name,
                code=code,
            )
            db.add(section)
        else:
            section.program_id = program.id
            section.academic_year_id = year.id
            section.semester = 5
            section.name = name
        sections[name] = section
    db.flush()

    courses: dict[tuple[str, str], Course] = {}
    for spec in COURSES:
        course = db.scalar(
            select(Course).where(
                Course.department_id == department.id,
                Course.semester == 5,
                Course.code == spec.code,
                Course.name == spec.name,
            )
        )
        if course is None:
            course = Course(
                department_id=department.id,
                semester=5,
                code=spec.code,
                name=spec.name,
                kind=spec.kind,
            )
            db.add(course)
        else:
            course.kind = spec.kind
        courses[(spec.code, spec.name)] = course

    faculty: dict[str, Faculty] = {}
    for employee_code, (name, designation) in FACULTY.items():
        user = _upsert_user(
            db,
            login_id=employee_code,
            role="teacher",
            email=f"{employee_code.lower()}@example.test",
            department_id=department.id,
            password_hash=password_hash,
        )
        db.flush()
        faculty_row = db.scalar(select(Faculty).where(Faculty.employee_code == employee_code))
        if faculty_row is None:
            faculty_row = Faculty(
                user_id=user.id,
                department_id=department.id,
                employee_code=employee_code,
                full_name=name,
                designation=designation,
            )
            db.add(faculty_row)
        else:
            faculty_row.user_id = user.id
            faculty_row.department_id = department.id
            faculty_row.full_name = name
            faculty_row.designation = designation
        faculty[employee_code] = faculty_row

    for login_id, role, email in (
        ("DEMO-HOD", "hod", "hod@example.test"),
        ("DEMO-ADMIN", "admin", "admin@example.test"),
    ):
        _upsert_user(
            db,
            login_id=login_id,
            role=role,
            email=email,
            department_id=department.id,
            password_hash=password_hash,
        )
    db.flush()

    for spec in COURSES:
        course = courses[(spec.code, spec.name)]
        for section_name, employee_code in (("A", spec.faculty_a), ("B", spec.faculty_b)):
            section = sections[section_name]
            assignment = db.scalar(
                select(TeachingAssignment).where(
                    TeachingAssignment.course_id == course.id,
                    TeachingAssignment.section_id == section.id,
                    TeachingAssignment.academic_year_id == year.id,
                )
            )
            if assignment is None:
                db.add(
                    TeachingAssignment(
                        course_id=course.id,
                        section_id=section.id,
                        faculty_id=faculty[employee_code].id,
                        academic_year_id=year.id,
                    )
                )
            else:
                assignment.faculty_id = faculty[employee_code].id
    db.flush()
    return department, year, sections, courses, faculty


def _local_datetime(day: date, at: time) -> datetime:
    return datetime.combine(day, at, tzinfo=LOCAL_TZ).astimezone(UTC)


def _ensure_fees_and_results(
    db: Session,
    *,
    students: list[Student],
    year: AcademicYear,
    courses: dict[tuple[str, str], Course],
) -> None:
    fees = {
        fee.student_id: fee
        for fee in db.scalars(select(FeeRecord).where(FeeRecord.academic_year_id == year.id)).all()
    }
    pending_rng = random.Random(42)
    pending_students = set(
        student.id
        for index, student in enumerate(sorted(students, key=lambda row: row.id))
        if index % 17 == 0
    )
    fine_students = set(
        student.id
        for index, student in enumerate(sorted(students, key=lambda row: row.id))
        if index % 55 == 0
    )
    for student in students:
        if student.id not in fees:
            fine = (
                Decimal(pending_rng.choice([150, 250, 400]))
                if student.id in fine_students
                else Decimal(0)
            )
            if student.id in pending_students:
                pending = Decimal(pending_rng.randint(2000, 9000))
                paid = Decimal(16407) + fine - pending
            else:
                fine = Decimal(0) if student.id not in fine_students else fine
                paid = Decimal(16407) + fine
            db.add(
                FeeRecord(
                    student_id=student.id,
                    academic_year_id=year.id,
                    total_amount=Decimal(16407),
                    paid_amount=paid,
                    fine_amount=fine,
                    due_date=date(2026, 11, 15),
                )
            )

    theory_courses = [course for course in courses.values() if course.kind == "theory"]
    existing_results = {
        (row.student_id, row.course_id, row.exam_name)
        for row in db.execute(
            select(
                AssessmentResult.student_id,
                AssessmentResult.course_id,
                AssessmentResult.exam_name,
            )
        ).all()
    }
    for student in students:
        student_key = student.enrollment_no or f"{student.roll_no}:{student.full_name}"
        rng = random.Random(f"seed-42-results-{student_key}")
        for course in theory_courses:
            for index, exam_name in enumerate(("Internal Test 1", "Internal Test 2"), start=1):
                key = (student.id, course.id, exam_name)
                if key in existing_results:
                    continue
                marks = Decimal(rng.randint(10, 30)).quantize(Decimal("0.01"))
                published = _local_datetime(date(2026, 9 if index == 1 else 10, 20), time(12))
                db.add(
                    AssessmentResult(
                        student_id=student.id,
                        course_id=course.id,
                        exam_name=exam_name,
                        max_marks=Decimal(30),
                        marks_obtained=marks,
                        published_at=published,
                    )
                )
    db.flush()


def _ensure_assignments(
    db: Session,
    *,
    sections: dict[str, Section],
    courses: dict[tuple[str, str], Course],
    students: list[Student],
) -> None:
    existing = {
        (assignment.section_id, assignment.course_id, assignment.title): assignment
        for assignment in db.scalars(select(Assignment)).all()
    }
    assignments: list[Assignment] = []
    ordered_courses = list(courses.values())
    for section_name, section in sections.items():
        for index in range(9):
            course = ordered_courses[index % len(ordered_courses)]
            title = f"Practice set {index + 1}"
            key = (section.id, course.id, title)
            assignment = existing.get(key)
            if assignment is None:
                due_day = date(2026, 11, 4) + timedelta(days=index - 2)
                due_at = _local_datetime(due_day, time(23, 59))
                assignment = Assignment(
                    course_id=course.id,
                    section_id=section.id,
                    title=title,
                    description=f"Practice work for {course.name}.",
                    due_at=due_at,
                    max_marks=Decimal(10),
                )
                db.add(assignment)
            assignments.append(assignment)
    db.flush()

    student_by_section: dict[int, list[Student]] = {}
    for student in students:
        student_by_section.setdefault(student.section_id, []).append(student)
    section_codes = {section.id: section.code for section in sections.values()}
    course_names = {course.id: course.name for course in courses.values()}
    submissions = {
        (submission.assignment_id, submission.student_id)
        for submission in db.scalars(select(AssignmentSubmission)).all()
    }
    for assignment in assignments:
        section_students = student_by_section.get(assignment.section_id, [])
        for student in section_students:
            key = (assignment.id, student.id)
            if key in submissions:
                continue
            # About two thirds submitted; the rest remain pending with no submission row.
            student_key = student.enrollment_no or f"{student.roll_no}:{student.full_name}"
            assignment_key = (
                f"{section_codes[assignment.section_id]}:{course_names[assignment.course_id]}:"
                f"{assignment.title}"
            )
            submission_rng = random.Random(f"seed-42-submission-{assignment_key}-{student_key}")
            if submission_rng.random() < 0.67:
                submitted_at = assignment.due_at - timedelta(days=submission_rng.randint(0, 5))
                db.add(
                    AssignmentSubmission(
                        assignment_id=assignment.id,
                        student_id=student.id,
                        file_path=(
                            f"{settings.upload_dir}/demo-submissions/"
                            f"{student.id}/{assignment.id}.pdf"
                        ),
                        submitted_at=submitted_at,
                        status="submitted",
                    )
                )
                submissions.add(key)
    db.flush()


def _ensure_sessions(
    db: Session,
    *,
    department: Department,
    students: list[Student],
    year: AcademicYear,
    courses: dict[tuple[str, str], Course],
    faculty: dict[str, Faculty],
) -> None:
    assignments = db.scalars(
        select(TeachingAssignment)
        .join(Course, Course.id == TeachingAssignment.course_id)
        .where(
            TeachingAssignment.academic_year_id == year.id,
            Course.department_id == department.id,
        )
        .order_by(TeachingAssignment.id)
    ).all()
    rng = random.Random(42)
    sessions_by_assignment: dict[int, list[ClassSession]] = {}
    existing_sessions = {
        (session.teaching_assignment_id, session.session_date, session.start_time): session
        for session in db.scalars(select(ClassSession)).all()
    }
    course_by_id = {course.id: course for course in courses.values()}
    faculty_by_id = {person.id: person for person in faculty.values()}
    user_by_faculty_id = {person.id: db.get(AppUser, person.user_id) for person in faculty.values()}
    section_codes = {
        section.id: section.code
        for section in db.scalars(select(Section).where(Section.academic_year_id == year.id)).all()
    }
    weekdays: list[date] = []
    day = date(2026, 8, 3)
    last_day = date(2026, 11, 6)
    while day <= last_day:
        if day.weekday() < 5:
            weekdays.append(day)
        day += timedelta(days=1)

    for assignment in assignments:
        course = course_by_id[assignment.course_id]
        count = rng.randint(35, 55)
        chosen_days = sorted(rng.sample(weekdays, count))
        session_rows: list[ClassSession] = []
        owner = faculty_by_id[assignment.faculty_id]
        creator = user_by_faculty_id[owner.id]
        for index, session_day in enumerate(chosen_days):
            start_at = time(rng.choice([9, 10, 11, 13, 14, 15]))
            topic = rng.choice(COURSE_TOPICS)
            key = (assignment.id, session_day, start_at)
            session = existing_sessions.get(key)
            history_key = (course.code, course.name) in HISTORY_COURSE_KEYS
            scheduled = history_key and index >= len(chosen_days) - 3
            if session is None:
                session_start = _local_datetime(session_day, start_at)
                session_end_time = (
                    datetime.combine(session_day, start_at) + timedelta(hours=1)
                ).time()
                session = ClassSession(
                    teaching_assignment_id=assignment.id,
                    session_date=session_day,
                    start_time=start_at,
                    end_time=session_end_time,
                    topic=topic,
                    status="scheduled" if scheduled else "attendance_updated",
                    created_by=creator.id,
                    created_at=session_start - timedelta(days=1),
                    attendance_updated_at=(
                        _local_datetime(session_day, session_end_time) if not scheduled else None
                    ),
                    attendance_updated_by=creator.id if not scheduled else None,
                )
                db.add(session)
            session_rows.append(session)
        sessions_by_assignment[assignment.id] = session_rows
    db.flush()

    all_session_ids = [
        session.id for sessions in sessions_by_assignment.values() for session in sessions
    ]
    existing_records = (
        {
            (record.session_id, record.student_id)
            for record in db.scalars(
                select(AttendanceRecord).where(AttendanceRecord.session_id.in_(all_session_ids))
            ).all()
        }
        if all_session_ids
        else set()
    )
    students_by_section: dict[int, list[Student]] = {}
    for student in students:
        students_by_section.setdefault(student.section_id, []).append(student)

    assignment_by_id = {assignment.id: assignment for assignment in assignments}
    records_to_add: list[AttendanceRecord] = []
    for assignment_id, sessions in sessions_by_assignment.items():
        assignment = assignment_by_id[assignment_id]
        actor = user_by_faculty_id[assignment.faculty_id]
        if actor is None:
            continue
        roster = students_by_section.get(assignment.section_id, [])
        for session in sessions:
            if session.status != "attendance_updated":
                continue
            for student in roster:
                key = (session.id, student.id)
                if key in existing_records:
                    continue
                student_key = student.enrollment_no or f"{student.roll_no}:{student.full_name}"
                session_key = (
                    f"{course_by_id[assignment.course_id].code}:"
                    f"{course_by_id[assignment.course_id].name}:"
                    f"{section_codes[assignment.section_id]}:"
                    f"{session.session_date}:{session.start_time}"
                )
                tendency_rng = random.Random(f"seed-42-tendency-{student_key}")
                tendency = 0.4 + tendency_rng.random() * 0.6
                outcome_rng = random.Random(f"seed-42-attendance-{student_key}-{session_key}")
                status = "present" if outcome_rng.random() < tendency else "absent"
                records_to_add.append(
                    AttendanceRecord(
                        session_id=session.id,
                        student_id=student.id,
                        status=status,
                        marked_by=actor.id,
                        updated_at=session.attendance_updated_at or datetime.now(UTC),
                    )
                )
                existing_records.add(key)
    db.add_all(records_to_add)
    db.flush()


def seed_demo_data(
    db: Session,
    *,
    students_file: Path | None = None,
    password: str | None = None,
    reset: bool = False,
) -> dict[str, int]:
    seed_password = password if password is not None else settings.seed_default_password
    if not seed_password:
        raise ValueError("Set SEED_DEFAULT_PASSWORD before running the seed command.")
    source = students_file or PRIVATE_STUDENTS
    if not source.exists():
        source = SAMPLE_STUDENTS
        print(f"WARNING: private student CSV missing; using fake sample data at {source}.")
    rows = load_student_rows(source)
    try:
        if reset:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(delete(table))
            db.flush()
        pwd_hash = hash_password(seed_password)
        department, year, sections, courses, faculty = _ensure_reference_data(db, pwd_hash)
        _load_students(
            db,
            rows,
            department_id=department.id,
            sections=sections,
            password_hash=pwd_hash,
        )
        students = db.scalars(
            select(Student).where(Student.department_id == department.id).order_by(Student.id)
        ).all()
        _ensure_fees_and_results(db, students=students, year=year, courses=courses)
        _ensure_assignments(db, sections=sections, courses=courses, students=students)
        _ensure_sessions(
            db,
            department=department,
            students=students,
            year=year,
            courses=courses,
            faculty=faculty,
        )
        db.commit()
    except Exception:
        db.rollback()
        raise

    return {
        "students": int(db.scalar(select(func.count()).select_from(Student)) or 0),
        "courses": int(db.scalar(select(func.count()).select_from(Course)) or 0),
        "teaching_assignments": int(
            db.scalar(select(func.count()).select_from(TeachingAssignment)) or 0
        ),
        "sessions": int(db.scalar(select(func.count()).select_from(ClassSession)) or 0),
    }


def main(argv: list[str] | None = None) -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Load the synthetic OIST CSE ERP dataset.")
    parser.add_argument("--reset", action="store_true", help="Delete existing rows before seeding.")
    args = parser.parse_args(argv)
    with SessionLocal() as db:
        counts = seed_demo_data(db, reset=args.reset)
    print(
        "Seed complete: "
        f"{counts['students']} students, {counts['courses']} courses, "
        f"{counts['teaching_assignments']} teaching assignments, {counts['sessions']} sessions."
    )


if __name__ == "__main__":
    main(sys.argv[1:])
