# API reference

Generated from the FastAPI OpenAPI schema by `PYTHONPATH=backend uv run python scripts/export_api_docs.py`.

OpenAPI version: `3.1.0` · API version: `0.1.0`

All routes are under `/api/v1` except the system endpoints. Authenticated routes use a bearer token. Student identity is derived from the token; student endpoints accept no student ID.

Errors use `{"error":{"code":string,"message":string,"details":object|null}}`. Login failures share one response. Attendance writes accept `dry_run=true` to preview without saving.

## Authentication

| Method | Path | Summary | Parameters | Request | Responses |
| --- | --- | --- | --- | --- | --- |
| `POST` | `/api/v1/auth/login` | Log in and receive a bearer token | — | LoginRequest | `200`, `422` · TokenResponse |
| `GET` | `/api/v1/auth/me` | Get the authenticated user's account | — | — | `200` · UserSummary |

## Student routes

| Method | Path | Summary | Parameters | Request | Responses |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/v1/me/assignments` | List assignments for the authenticated student's section | — | — | `200` · array of AssignmentResponse |
| `GET` | `/api/v1/me/attendance/courses/{course_id}/sessions` | List updated attendance sessions for one of the student's courses | `course_id` (path) | — | `200`, `422` · array of AttendanceSessionResponse |
| `GET` | `/api/v1/me/attendance/summary` | Get overall and course-wise attendance totals | — | — | `200` · AttendanceSummaryResponse |
| `GET` | `/api/v1/me/fees` | List the authenticated student's fee records | — | — | `200` · array of FeeRecordResponse |
| `GET` | `/api/v1/me/profile` | Get the authenticated student's profile and section | — | — | `200` · StudentProfileResponse |
| `GET` | `/api/v1/me/results` | List the authenticated student's published results | — | — | `200` · array of ResultResponse |

## Teacher routes

| Method | Path | Summary | Parameters | Request | Responses |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/api/v1/teacher/classes` | List the authenticated teacher's assigned classes | — | — | `200` · array of TeacherClassResponse |
| `GET` | `/api/v1/teacher/sessions` | List the authenticated teacher's class sessions with optional filters | `teaching_assignment_id` (query), `from` (query), `to` (query), `status` (query) | — | `200`, `422` · array of TeacherSessionListItem |
| `POST` | `/api/v1/teacher/sessions` | Create a scheduled session for one of the teacher's classes | — | SessionCreate | `201`, `422` · SessionResponse |
| `DELETE` | `/api/v1/teacher/sessions/{session_id}` | Delete a scheduled session that has no attendance records | `session_id` (path) | — | `204`, `422` |
| `GET` | `/api/v1/teacher/sessions/{session_id}` | Get an assigned class session | `session_id` (path) | — | `200`, `422` · SessionResponse |
| `PATCH` | `/api/v1/teacher/sessions/{session_id}` | Edit session details within the attendance edit window | `session_id` (path) | SessionPatch | `200`, `422` · SessionResponse |
| `PUT` | `/api/v1/teacher/sessions/{session_id}/attendance` | Preview or save a complete attendance roster for a class session | `session_id` (path), `dry_run` (query) | AttendanceRecordsPayload | AttendanceDefaultPayload | `200`, `422` · AttendanceSaveResponse |
| `GET` | `/api/v1/teacher/sessions/{session_id}/roster` | Get the complete section roster and current session attendance | `session_id` (path) | — | `200`, `422` · array of RosterStudent |

## System routes

| Method | Path | Summary | Parameters | Request | Responses |
| --- | --- | --- | --- | --- | --- |
| `GET` | `/` | Get API entry points | — | — | `200` · RootResponse |
| `GET` | `/health` | Check API availability | — | — | `200` · HealthResponse |

## OpenAPI schemas

### `AssignmentResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `course` | CourseIdentity | yes |  |
| `title` | string | yes |  |
| `description` | string | null | yes |  |
| `due_at` | string | yes |  |
| `max_marks` | string | yes |  |
| `status` | string | yes |  |
| `submitted_at` | string | null | yes |  |

### `AttendanceDefaultPayload`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `default_status` | string (present, absent) | yes |  |
| `absent_roll_nos` | array of string | no |  |

### `AttendanceRecordInput`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `roll_no` | string | yes |  |
| `status` | string (present, absent) | yes |  |

### `AttendanceRecordsPayload`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `records` | array of AttendanceRecordInput | yes |  |

### `AttendanceSaveResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `saved` | boolean | yes |  |
| `present` | integer | yes |  |
| `absent` | integer | yes |  |
| `total` | integer | yes |  |
| `diff` | array of object | yes |  |

### `AttendanceSessionResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `session_date` | string | yes |  |
| `start_time` | string | yes |  |
| `end_time` | string | yes |  |
| `topic` | string | null | yes |  |
| `outcome` | string | yes |  |

### `AttendanceSummaryResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `overall` | AttendanceTotals | yes |  |
| `courses` | array of CourseAttendanceSummary | yes |  |

### `AttendanceTotals`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `present` | integer | yes |  |
| `total` | integer | yes |  |
| `percent` | number | yes |  |
| `band` | string | yes |  |
| `shortage` | boolean | yes |  |
| `formula` | string | yes |  |

### `CourseAttendanceSummary`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `course` | CourseIdentity | yes |  |
| `kind` | string | yes |  |
| `present` | integer | yes |  |
| `total` | integer | yes |  |
| `percent` | number | yes |  |
| `band` | string | yes |  |
| `shortage` | boolean | yes |  |

### `CourseIdentity`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `code` | string | yes |  |
| `name` | string | yes |  |

### `FeeRecordResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `academic_year` | string | yes |  |
| `total_amount` | string | yes |  |
| `paid_amount` | string | yes |  |
| `fine_amount` | string | yes |  |
| `pending_amount` | string | yes |  |
| `due_date` | string | yes |  |

### `HTTPValidationError`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `detail` | array of ValidationError | no |  |

### `HealthResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `status` | string | yes |  |

### `LoginRequest`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `login_id` | string | yes |  |
| `password` | string | yes |  |

### `ResultResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `course` | CourseIdentity | yes |  |
| `exam_name` | string | yes |  |
| `max_marks` | string | yes |  |
| `marks_obtained` | string | yes |  |
| `published_at` | string | null | yes |  |

### `RootResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `service` | string | yes |  |
| `docs` | string | yes |  |
| `openapi` | string | yes |  |
| `health` | string | yes |  |

### `RosterStudent`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `student_id` | integer | yes |  |
| `roll_no` | string | yes |  |
| `full_name` | string | yes |  |
| `status` | string (present, absent) | null | yes |  |

### `SessionCreate`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `teaching_assignment_id` | integer | yes |  |
| `session_date` | string | yes |  |
| `start_time` | string | yes |  |
| `end_time` | string | yes |  |
| `topic` | string | null | no |  |

### `SessionPatch`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `session_date` | string | null | no |  |
| `start_time` | string | null | no |  |
| `end_time` | string | null | no |  |
| `topic` | string | null | no |  |

### `SessionResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `teaching_assignment_id` | integer | yes |  |
| `course` | TeacherCourse | yes |  |
| `section` | TeacherSection | yes |  |
| `session_date` | string | yes |  |
| `start_time` | string | yes |  |
| `end_time` | string | yes |  |
| `topic` | string | null | yes |  |
| `status` | string (scheduled, attendance_updated) | yes |  |
| `created_at` | string | yes |  |
| `attendance_updated_at` | string | null | yes |  |

### `StudentProfileResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `student_id` | integer | yes |  |
| `enrollment_no` | string | null | yes |  |
| `roll_no` | string | yes |  |
| `full_name` | string | yes |  |
| `gender` | string | null | yes |  |
| `email` | string | null | yes |  |
| `department_code` | string | yes |  |
| `program_name` | string | yes |  |
| `semester` | integer | yes |  |
| `section_name` | string | yes |  |
| `section_code` | string | yes |  |
| `academic_year` | string | yes |  |

### `TeacherClassResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `teaching_assignment_id` | integer | yes |  |
| `course` | TeacherCourse | yes |  |
| `section` | TeacherSection | yes |  |
| `last_session` | string | null | yes |  |
| `pending_attendance_count` | integer | yes |  |

### `TeacherCourse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `code` | string | yes |  |
| `name` | string | yes |  |
| `kind` | string | yes |  |

### `TeacherSection`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `name` | string | yes |  |
| `code` | string | yes |  |
| `semester` | integer | yes |  |
| `academic_year` | string | yes |  |

### `TeacherSessionListItem`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `teaching_assignment_id` | integer | yes |  |
| `course` | TeacherCourse | yes |  |
| `section` | TeacherSection | yes |  |
| `session_date` | string | yes |  |
| `start_time` | string | yes |  |
| `end_time` | string | yes |  |
| `topic` | string | null | yes |  |
| `status` | string (scheduled, attendance_updated) | yes |  |

### `TokenResponse`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `access_token` | string | yes |  |
| `token_type` | string | no |  |
| `role` | string | yes |  |
| `user` | UserSummary | yes |  |

### `UserSummary`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | integer | yes |  |
| `role` | string | yes |  |
| `login_id` | string | yes |  |
| `email` | string | null | yes |  |
| `department_id` | integer | yes |  |

### `ValidationError`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `loc` | array of string | integer | yes |  |
| `msg` | string | yes |  |
| `type` | string | yes |  |
| `input` | object | no |  |
| `ctx` | object | no |  |
