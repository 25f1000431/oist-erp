from datetime import date, datetime, time
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Department(Base):
    __tablename__ = "department"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(120))


class Program(Base):
    __tablename__ = "program"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)
    code: Mapped[str] = mapped_column(String(30), unique=True)
    name: Mapped[str] = mapped_column(String(160))


class AcademicYear(Base):
    __tablename__ = "academic_year"
    id: Mapped[int] = mapped_column(primary_key=True)
    label: Mapped[str] = mapped_column(String(9), unique=True)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False)


class Section(Base):
    __tablename__ = "section"
    __table_args__ = (UniqueConstraint("program_id", "academic_year_id", "semester", "name"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    program_id: Mapped[int] = mapped_column(ForeignKey("program.id"), index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_year.id"), index=True)
    semester: Mapped[int] = mapped_column(Integer)
    name: Mapped[str] = mapped_column(String(20))
    code: Mapped[str] = mapped_column(String(40), unique=True)


class AppUser(Base):
    __tablename__ = "app_user"
    id: Mapped[int] = mapped_column(primary_key=True)
    role: Mapped[str] = mapped_column(String(20), index=True)
    login_id: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)


class Student(Base):
    __tablename__ = "student"
    __table_args__ = (UniqueConstraint("section_id", "roll_no"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("section.id"), index=True)
    enrollment_no: Mapped[str | None] = mapped_column(String(40), unique=True, nullable=True)
    roll_no: Mapped[str] = mapped_column(String(30))
    full_name: Mapped[str] = mapped_column(String(160))
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(254), nullable=True)


class Faculty(Base):
    __tablename__ = "faculty"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), unique=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(160))
    designation: Mapped[str] = mapped_column(String(100))


class Course(Base):
    __tablename__ = "course"
    id: Mapped[int] = mapped_column(primary_key=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("department.id"), index=True)
    semester: Mapped[int] = mapped_column(Integer)
    code: Mapped[str] = mapped_column(String(40))
    name: Mapped[str] = mapped_column(String(160))
    kind: Mapped[str] = mapped_column(String(20))


class TeachingAssignment(Base):
    __tablename__ = "teaching_assignment"
    __table_args__ = (UniqueConstraint("course_id", "section_id", "academic_year_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("section.id"), index=True)
    faculty_id: Mapped[int] = mapped_column(ForeignKey("faculty.id"), index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_year.id"), index=True)


class ClassSession(Base):
    __tablename__ = "class_session"
    __table_args__ = (UniqueConstraint("teaching_assignment_id", "session_date", "start_time"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    teaching_assignment_id: Mapped[int] = mapped_column(
        ForeignKey("teaching_assignment.id"), index=True
    )
    session_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    topic: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled")
    created_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    attendance_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    attendance_updated_by: Mapped[int | None] = mapped_column(
        ForeignKey("app_user.id"), nullable=True
    )


class AttendanceRecord(Base):
    __tablename__ = "attendance_record"
    __table_args__ = (UniqueConstraint("session_id", "student_id"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("class_session.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    status: Mapped[str] = mapped_column(String(10))
    marked_by: Mapped[int] = mapped_column(ForeignKey("app_user.id"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class FeeRecord(Base):
    __tablename__ = "fee_record"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    academic_year_id: Mapped[int] = mapped_column(ForeignKey("academic_year.id"))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    fine_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    due_date: Mapped[date] = mapped_column(Date)


class AssessmentResult(Base):
    __tablename__ = "assessment_result"
    id: Mapped[int] = mapped_column(primary_key=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), index=True)
    exam_name: Mapped[str] = mapped_column(String(100))
    max_marks: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    marks_obtained: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Assignment(Base):
    __tablename__ = "assignment"
    id: Mapped[int] = mapped_column(primary_key=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("course.id"), index=True)
    section_id: Mapped[int] = mapped_column(ForeignKey("section.id"), index=True)
    title: Mapped[str] = mapped_column(String(180))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    due_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    max_marks: Mapped[Decimal] = mapped_column(Numeric(7, 2))


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submission"
    id: Mapped[int] = mapped_column(primary_key=True)
    assignment_id: Mapped[int] = mapped_column(ForeignKey("assignment.id"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("student.id"), index=True)
    file_path: Mapped[str] = mapped_column(String(500))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(30))


class AuditLog(Base):
    __tablename__ = "audit_log"
    id: Mapped[int] = mapped_column(primary_key=True)
    actor_user_id: Mapped[int] = mapped_column(ForeignKey("app_user.id"), index=True)
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(80))
    entity_id: Mapped[int] = mapped_column(Integer)
    before_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
