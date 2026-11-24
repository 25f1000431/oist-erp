from datetime import date, datetime, time
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AttendanceStatus = Literal["present", "absent"]
SessionStatus = Literal["scheduled", "attendance_updated"]


class TeacherCourse(BaseModel):
    id: int
    code: str
    name: str
    kind: str


class TeacherSection(BaseModel):
    id: int
    name: str
    code: str
    semester: int
    academic_year: str


class TeacherClassResponse(BaseModel):
    teaching_assignment_id: int
    course: TeacherCourse
    section: TeacherSection
    last_session: date | None
    pending_attendance_count: int


class SessionCreate(BaseModel):
    teaching_assignment_id: int
    session_date: date
    start_time: time
    end_time: time
    topic: str | None = Field(default=None, max_length=2000)


class SessionPatch(BaseModel):
    session_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    topic: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def at_least_one_field(self):
        if not self.model_fields_set:
            raise ValueError("At least one session field must be provided.")
        return self


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    teaching_assignment_id: int
    course: TeacherCourse
    section: TeacherSection
    session_date: date
    start_time: time
    end_time: time
    topic: str | None
    status: SessionStatus
    created_at: datetime
    attendance_updated_at: datetime | None


class AttendanceRecordInput(BaseModel):
    roll_no: str = Field(min_length=1, max_length=30)
    status: AttendanceStatus


class AttendanceRecordsPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[AttendanceRecordInput]


class AttendanceDefaultPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    default_status: AttendanceStatus
    absent_roll_nos: list[str] = Field(default_factory=list)


class AttendanceSaveResponse(BaseModel):
    saved: bool
    present: int
    absent: int
    total: int
    diff: list[dict[str, str | None]]


class RosterStudent(BaseModel):
    student_id: int
    roll_no: str
    full_name: str
    status: AttendanceStatus | None


class TeacherSessionListItem(BaseModel):
    id: int
    teaching_assignment_id: int
    course: TeacherCourse
    section: TeacherSection
    session_date: date
    start_time: time
    end_time: time
    topic: str | None
    status: SessionStatus
