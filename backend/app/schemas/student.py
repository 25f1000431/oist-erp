from datetime import date, datetime, time
from decimal import Decimal

from pydantic import BaseModel


class CourseIdentity(BaseModel):
    id: int
    code: str
    name: str


class StudentProfileResponse(BaseModel):
    student_id: int
    enrollment_no: str | None
    roll_no: str
    full_name: str
    gender: str | None
    email: str | None
    department_code: str
    program_name: str
    semester: int
    section_name: str
    section_code: str
    academic_year: str


class AttendanceTotals(BaseModel):
    present: int
    total: int
    percent: float
    band: str
    shortage: bool
    formula: str


class CourseAttendanceSummary(BaseModel):
    course: CourseIdentity
    kind: str
    present: int
    total: int
    percent: float
    band: str
    shortage: bool


class AttendanceSummaryResponse(BaseModel):
    overall: AttendanceTotals
    courses: list[CourseAttendanceSummary]


class AttendanceSessionResponse(BaseModel):
    session_date: date
    start_time: time
    end_time: time
    topic: str | None
    outcome: str


class FeeRecordResponse(BaseModel):
    academic_year: str
    total_amount: Decimal
    paid_amount: Decimal
    fine_amount: Decimal
    pending_amount: Decimal
    due_date: date


class ResultResponse(BaseModel):
    course: CourseIdentity
    exam_name: str
    max_marks: Decimal
    marks_obtained: Decimal
    published_at: datetime | None


class AssignmentResponse(BaseModel):
    id: int
    course: CourseIdentity
    title: str
    description: str | None
    due_at: datetime
    max_marks: Decimal
    status: str
    submitted_at: datetime | None


class AssignmentSubmissionResponse(BaseModel):
    assignment_id: int
    status: str
    submitted_at: datetime
