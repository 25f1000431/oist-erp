export type Role = "student" | "teacher" | "hod" | "admin";

export interface UserSummary {
  id: number;
  role: Role;
  login_id: string;
  email: string | null;
  department_id: number;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  role: Role;
  user: UserSummary;
}

export interface StudentProfile {
  student_id: number;
  enrollment_no: string | null;
  roll_no: string;
  full_name: string;
  gender: string | null;
  email: string | null;
  department_code: string;
  program_name: string;
  semester: number;
  section_name: string;
  section_code: string;
  academic_year: string;
}

export interface CourseIdentity {
  id: number;
  code: string;
  name: string;
}

export interface AttendanceTotals {
  present: number;
  total: number;
  percent: number;
  band: "Critical" | "Watch" | "Safe";
  shortage: boolean;
  formula: string;
}

export interface CourseAttendance {
  course: CourseIdentity;
  kind: string;
  present: number;
  total: number;
  percent: number;
  band: "Critical" | "Watch" | "Safe";
  shortage: boolean;
}

export interface AttendanceSummary {
  overall: AttendanceTotals;
  courses: CourseAttendance[];
}

export interface AttendanceSession {
  session_date: string;
  start_time: string;
  end_time: string;
  topic: string | null;
  outcome: "P" | "A";
}

export interface FeeRecord {
  academic_year: string;
  total_amount: number;
  paid_amount: number;
  fine_amount: number;
  pending_amount: number;
  due_date: string;
}

export interface AssessmentResult {
  course: CourseIdentity;
  exam_name: string;
  max_marks: number;
  marks_obtained: number;
  published_at: string | null;
}

export interface Assignment {
  id: number;
  course: CourseIdentity;
  title: string;
  description: string | null;
  due_at: string;
  max_marks: number;
  status: string;
  submitted_at: string | null;
}

export interface TeacherClass {
  teaching_assignment_id: number;
  course: CourseIdentity & { kind: string };
  section: {
    id: number;
    name: string;
    code: string;
    semester: number;
    academic_year: string;
  };
  last_session: string | null;
  pending_attendance_count: number;
}

export interface TeacherSession {
  id: number;
  teaching_assignment_id: number;
  course: CourseIdentity & { kind: string };
  section: TeacherClass["section"];
  session_date: string;
  start_time: string;
  end_time: string;
  topic: string | null;
  status: "scheduled" | "attendance_updated";
}

export interface RosterStudent {
  student_id: number;
  roll_no: string;
  full_name: string;
  status: "present" | "absent" | null;
}

export interface AttendanceDiff {
  roll_no: string;
  name: string;
  from: "present" | "absent" | null;
  to: "present" | "absent";
}

export interface AttendanceSaveResult {
  saved: boolean;
  present: number;
  absent: number;
  total: number;
  diff: AttendanceDiff[];
}

export interface SessionCreatePayload {
  teaching_assignment_id: number;
  session_date: string;
  start_time: string;
  end_time: string;
  topic: string | null;
}

const baseUrl = (import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1").replace(
  /\/$/,
  "",
);

export class ApiError extends Error {
  status: number;
  code: string;

  constructor(message: string, status: number, code = "request_error") {
    super(message);
    this.status = status;
    this.code = code;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = sessionStorage.getItem("oist_access_token");
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(`${baseUrl}${path}`, { ...options, headers });
  if (!response.ok) {
    const data = (await response.json().catch(() => null)) as
      | { error?: { message?: string; code?: string } }
      | null;
    throw new ApiError(
      data?.error?.message ?? `Request failed (${response.status}).`,
      response.status,
      data?.error?.code,
    );
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function queryString(values: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => {
    if (value !== undefined && value !== "") params.set(key, String(value));
  });
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  login: (login_id: string, password: string) =>
    request<AuthResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ login_id, password }),
    }),
  me: () => request<UserSummary>("/auth/me"),
  profile: () => request<StudentProfile>("/me/profile"),
  attendance: () => request<AttendanceSummary>("/me/attendance/summary"),
  courseSessions: (courseId: number) =>
    request<AttendanceSession[]>(`/me/attendance/courses/${courseId}/sessions`),
  fees: () => request<FeeRecord[]>("/me/fees"),
  results: () => request<AssessmentResult[]>("/me/results"),
  assignments: () => request<Assignment[]>("/me/assignments"),
  teacherClasses: () => request<TeacherClass[]>("/teacher/classes"),
  teacherSessions: (filters: {
    teaching_assignment_id?: number;
    from?: string;
    to?: string;
    status?: "scheduled" | "attendance_updated";
  } = {}) => request<TeacherSession[]>(`/teacher/sessions${queryString(filters)}`),
  createSession: (payload: SessionCreatePayload) =>
    request<TeacherSession>("/teacher/sessions", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  updateSession: (
    id: number,
    payload: Partial<Pick<SessionCreatePayload, "session_date" | "start_time" | "end_time" | "topic">>,
  ) =>
    request<TeacherSession>(`/teacher/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(payload),
    }),
  session: (id: number) => request<TeacherSession & { created_at: string }>(`/teacher/sessions/${id}`),
  roster: (id: number) => request<RosterStudent[]>(`/teacher/sessions/${id}/roster`),
  previewAttendance: (id: number, records: { roll_no: string; status: "present" | "absent" }[]) =>
    request<AttendanceSaveResult>(`/teacher/sessions/${id}/attendance?dry_run=true`, {
      method: "PUT",
      body: JSON.stringify({ records }),
    }),
  saveAttendance: (id: number, records: { roll_no: string; status: "present" | "absent" }[]) =>
    request<AttendanceSaveResult>(`/teacher/sessions/${id}/attendance`, {
      method: "PUT",
      body: JSON.stringify({ records }),
    }),
  deleteSession: (id: number) =>
    request<void>(`/teacher/sessions/${id}`, { method: "DELETE" }),
};

export function formatDate(value: string, options?: Intl.DateTimeFormatOptions): string {
  return new Intl.DateTimeFormat("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Kolkata",
    ...options,
  }).format(new Date(`${value.slice(0, 10)}T00:00:00+05:30`));
}

export function formatTime(value: string): string {
  const [hour, minute] = value.split(":").map(Number);
  return new Intl.DateTimeFormat("en-IN", {
    hour: "numeric",
    minute: "2-digit",
    hour12: true,
    timeZone: "Asia/Kolkata",
  }).format(new Date(Date.UTC(2020, 0, 1, hour - 5, minute - 30)));
}

export function formatMoney(value: number): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(value);
}
