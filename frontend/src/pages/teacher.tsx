import { useEffect, useMemo, useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";
import { ArrowLeft, ArrowUpRight, Check, Clock, MagnifyingGlass, Plus, WarningCircle } from "@phosphor-icons/react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  api,
  formatDate,
  formatTime,
  type AttendanceSaveResult,
  type RosterStudent,
  type TeacherClass,
  type TeacherSession,
} from "../lib/api";
import {
  EmptyNotice,
  ErrorNotice,
  LoadingBlock,
  PageHeading,
  Panel,
  SectionHeading,
} from "../components/ui";

function localDateInput(date = new Date()) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Kolkata",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).formatToParts(date);
  const get = (type: string) => parts.find((part) => part.type === type)?.value ?? "";
  return `${get("year")}-${get("month")}-${get("day")}`;
}

function shiftDate(value: string, offsetDays: number) {
  const [year, month, day] = value.split("-").map(Number);
  const shifted = new Date(Date.UTC(year, month - 1, day + offsetDays));
  return [
    shifted.getUTCFullYear(),
    String(shifted.getUTCMonth() + 1).padStart(2, "0"),
    String(shifted.getUTCDate()).padStart(2, "0"),
  ].join("-");
}

function sessionClassLine(session: TeacherSession) {
  return `${session.course.code} · Section ${session.section.name}`;
}

export function TeacherHome() {
  const classes = useQuery({ queryKey: ["teacher-classes"], queryFn: api.teacherClasses });
  const sessions = useQuery({ queryKey: ["teacher-sessions"], queryFn: () => api.teacherSessions() });
  if (classes.isLoading || sessions.isLoading) return <LoadingBlock label="Loading faculty classes" />;
  const error = classes.error ?? sessions.error;
  if (error) return <ErrorNotice message={error.message} />;
  const pending = sessions.data!.filter((session) => session.status === "scheduled");
  return (
    <>
      <PageHeading
        eyebrow="CSE · Semester V"
        title="My classes"
        description="Your assigned courses and sections for the current academic year."
        action={<Link className="button button-primary" to="/teacher/sessions"><Clock size={17} /> Session list</Link>}
      />
      {pending.length > 0 && (
        <Panel className="needs-attendance-strip">
          <div className="strip-icon"><WarningCircle size={20} /></div>
          <div className="strip-copy"><strong>Needs attendance</strong><span>{pending.length} session{pending.length === 1 ? "" : "s"} are still scheduled.</span></div>
          <div className="strip-links">{pending.slice(0, 4).map((session) => (
            <Link key={session.id} to={`/teacher/sessions/${session.id}/attendance`}>
              {session.course.code} · {session.section.name} <ArrowUpRight size={14} />
            </Link>
          ))}</div>
        </Panel>
      )}
      <Panel className="classes-panel">
        <SectionHeading title="Teaching assignments" detail={`${classes.data!.length} classes`} />
        {classes.data!.length ? (
          <div className="class-list">
            {classes.data!.map((item) => <TeacherClassRow key={item.teaching_assignment_id} item={item} />)}
          </div>
        ) : <EmptyNotice>No teaching assignments are attached to this account.</EmptyNotice>}
      </Panel>
    </>
  );
}

function TeacherClassRow({ item }: { item: TeacherClass }) {
  return (
    <div className="teacher-class-row">
      <div className="class-course-block">
        <span className="mono class-code">{item.course.code}</span>
        <strong>{item.course.name}</strong>
        <small>{item.course.kind} · Semester {item.section.semester}</small>
      </div>
      <div className="class-section-block">
        <span className="eyebrow">Section</span>
        <strong>{item.section.name}</strong>
        <small className="mono">{item.section.code}</small>
      </div>
      <div className="class-session-block">
        <span className="eyebrow">Last session</span>
        <strong>{item.last_session ? formatDate(item.last_session) : "None recorded"}</strong>
        <small>{item.pending_attendance_count ? `${item.pending_attendance_count} pending attendance` : "Up to date"}</small>
      </div>
      <Link className="button button-primary class-create" to={`/teacher/sessions/new?teaching_assignment_id=${item.teaching_assignment_id}`}>
        <Plus size={17} /> Create session
      </Link>
    </div>
  );
}

export function TeacherCreateSession() {
  const classes = useQuery({ queryKey: ["teacher-classes"], queryFn: api.teacherClasses });
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const requestedAssignment = params.get("teaching_assignment_id") ?? "";
  const [assignmentId, setAssignmentId] = useState(requestedAssignment);
  const [sessionDate, setSessionDate] = useState(localDateInput());
  const [startTime, setStartTime] = useState("09:00");
  const [endTime, setEndTime] = useState("10:00");
  const [topic, setTopic] = useState("");
  const [validation, setValidation] = useState("");
  const create = useMutation({
    mutationFn: api.createSession,
    onSuccess: async (session) => {
      await queryClient.invalidateQueries({ queryKey: ["teacher-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-classes"] });
      navigate(`/teacher/sessions/${session.id}/attendance`);
    },
  });
  const selected = classes.data?.find((item) => String(item.teaching_assignment_id) === assignmentId);
  const maxDate = localDateInput();
  const minDate = useMemo(() => shiftDate(maxDate, -14), [maxDate]);

  if (classes.isLoading) return <LoadingBlock label="Loading class list" />;
  if (classes.error) return <ErrorNotice message={classes.error.message} />;

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidation("");
    if (!assignmentId) return setValidation("Choose the class for this session.");
    if (sessionDate < minDate || sessionDate > maxDate) {
      return setValidation("Choose a date within the last 14 days, including today.");
    }
    if (endTime <= startTime) return setValidation("End time must be later than start time.");
    create.mutate({
      teaching_assignment_id: Number(assignmentId),
      session_date: sessionDate,
      start_time: startTime,
      end_time: endTime,
      topic: topic.trim() || null,
    });
  }

  return (
    <>
      <Link className="back-link" to="/teacher"><ArrowLeft size={17} /> My classes</Link>
      <PageHeading eyebrow="Faculty workspace · New class record" title="Create session" description="Record the class meeting before class or enter it after teaching." />
      <Panel className="form-panel">
        <form onSubmit={submit} className="form-stack">
          <label className="field-label">Class
            <select value={assignmentId} onChange={(event) => setAssignmentId(event.target.value)} required>
              <option value="">Choose a course and section</option>
              {classes.data!.map((item) => (
                <option key={item.teaching_assignment_id} value={item.teaching_assignment_id}>
                  {item.course.code} · {item.course.name} — Section {item.section.name}
                </option>
              ))}
            </select>
          </label>
          {selected && <div className="class-context"><span className="mono">{selected.section.code}</span><span>{selected.section.academic_year} · Semester {selected.section.semester}</span></div>}
          <div className="form-row">
            <label className="field-label">Date
              <input type="date" value={sessionDate} min={minDate} max={maxDate} onChange={(event) => setSessionDate(event.target.value)} required />
              <small>Today or up to 14 days back.</small>
            </label>
            <label className="field-label">Topic <span className="optional">Optional</span>
              <input type="text" maxLength={2000} value={topic} onChange={(event) => setTopic(event.target.value)} placeholder="e.g. Normalization and keys" />
            </label>
          </div>
          <div className="form-row time-row">
            <label className="field-label">Start time
              <input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} required />
            </label>
            <label className="field-label">End time
              <input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} required />
            </label>
          </div>
          {(validation || create.error) && <ErrorNotice message={validation || create.error!.message} />}
          <div className="form-actions">
            <Link className="button button-quiet" to="/teacher">Cancel</Link>
            <button className="button button-primary" type="submit" disabled={create.isPending}>
              <Plus size={17} /> {create.isPending ? "Creating…" : "Create session"}
            </button>
          </div>
        </form>
      </Panel>
    </>
  );
}

export function TeacherSessions() {
  const classes = useQuery({ queryKey: ["teacher-classes"], queryFn: api.teacherClasses });
  const [classId, setClassId] = useState("");
  const [from, setFrom] = useState("");
  const [to, setTo] = useState("");
  const [status, setStatus] = useState("");
  const filters = {
    teaching_assignment_id: classId ? Number(classId) : undefined,
    from: from || undefined,
    to: to || undefined,
    status: (status || undefined) as "scheduled" | "attendance_updated" | undefined,
  };
  const sessions = useQuery({
    queryKey: ["teacher-sessions", filters],
    queryFn: () => api.teacherSessions(filters),
  });
  const queryClient = useQueryClient();
  const [editSession, setEditSession] = useState<TeacherSession | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<TeacherSession | null>(null);
  const remove = useMutation({
    mutationFn: api.deleteSession,
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["teacher-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-classes"] });
      setDeleteTarget(null);
    },
  });
  if (classes.isLoading) return <LoadingBlock label="Loading class list" />;
  if (classes.error) return <ErrorNotice message={classes.error.message} />;
  return (
    <>
      <PageHeading eyebrow="Faculty workspace · Records" title="Sessions" description="Review class meetings and complete attendance." action={<Link className="button button-primary" to="/teacher/sessions/new"><Plus size={17} /> Create session</Link>} />
      <Panel className="filters-panel">
        <label className="field-label">Class
          <select value={classId} onChange={(event) => setClassId(event.target.value)}>
            <option value="">All classes</option>
            {classes.data!.map((item) => <option key={item.teaching_assignment_id} value={item.teaching_assignment_id}>{item.course.code} · Section {item.section.name}</option>)}
          </select>
        </label>
        <label className="field-label">From<input type="date" value={from} onChange={(event) => setFrom(event.target.value)} /></label>
        <label className="field-label">To<input type="date" value={to} onChange={(event) => setTo(event.target.value)} /></label>
        <label className="field-label">Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">All statuses</option><option value="scheduled">Needs attendance</option><option value="attendance_updated">Updated</option>
          </select>
        </label>
      </Panel>
      {sessions.isLoading ? <LoadingBlock label="Loading sessions" /> : sessions.error ? <ErrorNotice message={sessions.error.message} /> : (
        <Panel className="sessions-panel">
          <SectionHeading title="Class sessions" detail={`${sessions.data!.length} records`} />
          {sessions.data!.length ? <div className="session-list">
            {sessions.data!.map((session) => (
              <div className="session-row" key={session.id}>
                <div className="session-date-block"><strong>{formatDate(session.session_date, { year: undefined })}</strong><span className="mono">{formatTime(session.start_time)}–{formatTime(session.end_time)}</span></div>
                <div className="session-description"><strong>{sessionClassLine(session)}</strong><span>{session.course.name}{session.topic ? ` · ${session.topic}` : ""}</span></div>
                <span className={`session-state ${session.status === "scheduled" ? "state-scheduled" : "state-updated"}`}>
                  {session.status === "scheduled" ? "Needs attendance" : "Updated"}
                </span>
                <div className="session-actions">
                  <Link className="table-link" to={`/teacher/sessions/${session.id}/attendance`}>
                    {session.status === "scheduled" ? "Mark attendance" : "View / edit"} <ArrowUpRight size={15} />
                  </Link>
                  <button type="button" className="button button-small button-quiet" onClick={() => setEditSession(session)}>Edit details</button>
                  {session.status === "scheduled" && <button type="button" className="text-button text-danger" onClick={() => setDeleteTarget(session)}>Delete</button>}
                </div>
              </div>
            ))}
          </div> : <EmptyNotice>No sessions match these filters.</EmptyNotice>}
        </Panel>
      )}
      {editSession && <SessionEditDialog session={editSession} onClose={() => setEditSession(null)} />}
      {deleteTarget && <ConfirmDialog
        title="Delete scheduled session?"
        description={`${sessionClassLine(deleteTarget)} · ${formatDate(deleteTarget.session_date)}. This action cannot be undone.`}
        confirmLabel={remove.isPending ? "Deleting…" : "Delete session"}
        error={remove.error?.message}
        onCancel={() => setDeleteTarget(null)}
        onConfirm={() => remove.mutate(deleteTarget.id)}
      />}
    </>
  );
}

function SessionEditDialog({ session, onClose }: { session: TeacherSession; onClose: () => void }) {
  const queryClient = useQueryClient();
  const [sessionDate, setSessionDate] = useState(session.session_date);
  const [startTime, setStartTime] = useState(session.start_time.slice(0, 5));
  const [endTime, setEndTime] = useState(session.end_time.slice(0, 5));
  const [topic, setTopic] = useState(session.topic ?? "");
  const update = useMutation({
    mutationFn: () => api.updateSession(session.id, { session_date: sessionDate, start_time: startTime, end_time: endTime, topic: topic || null }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["teacher-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-classes"] });
      onClose();
    },
  });
  return (
    <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && onClose()}>
      <section className="dialog-panel" role="dialog" aria-modal="true" aria-labelledby="edit-session-title">
        <div className="dialog-heading"><div><span className="eyebrow">{sessionClassLine(session)}</span><h2 id="edit-session-title">Edit session details</h2></div><button className="icon-button" onClick={onClose} type="button" aria-label="Close">×</button></div>
        <div className="form-stack">
          <label className="field-label">Date<input type="date" value={sessionDate} onChange={(event) => setSessionDate(event.target.value)} /></label>
          <div className="form-row time-row"><label className="field-label">Start time<input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} /></label><label className="field-label">End time<input type="time" value={endTime} onChange={(event) => setEndTime(event.target.value)} /></label></div>
          <label className="field-label">Topic<input value={topic} onChange={(event) => setTopic(event.target.value)} maxLength={2000} /></label>
          {update.error && <ErrorNotice message={update.error.message} />}
          <div className="form-actions"><button className="button button-quiet" onClick={onClose} type="button">Cancel</button><button className="button button-primary" onClick={() => update.mutate()} disabled={update.isPending} type="button">{update.isPending ? "Saving…" : "Save changes"}</button></div>
        </div>
      </section>
    </div>
  );
}

export function TeacherAttendance() {
  const { id: rawId } = useParams();
  const sessionId = Number(rawId);
  const session = useQuery({ queryKey: ["teacher-session", sessionId], queryFn: () => api.session(sessionId), enabled: Number.isInteger(sessionId) });
  const roster = useQuery({ queryKey: ["teacher-roster", sessionId], queryFn: () => api.roster(sessionId), enabled: Number.isInteger(sessionId) });
  const queryClient = useQueryClient();
  const [statuses, setStatuses] = useState<Record<number, "present" | "absent">>({});
  const [search, setSearch] = useState("");
  const [absentInput, setAbsentInput] = useState("");
  const [absentError, setAbsentError] = useState("");
  const [preview, setPreview] = useState<AttendanceSaveResult | null>(null);
  const [saved, setSaved] = useState(false);
  const rowRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const previewMutation = useMutation({
    mutationFn: (records: { roll_no: string; status: "present" | "absent" }[]) => api.previewAttendance(sessionId, records),
    onSuccess: setPreview,
  });
  const saveMutation = useMutation({
    mutationFn: (records: { roll_no: string; status: "present" | "absent" }[]) => api.saveAttendance(sessionId, records),
    onSuccess: async () => {
      setPreview(null);
      setSaved(true);
      await queryClient.invalidateQueries({ queryKey: ["teacher-roster", sessionId] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-session", sessionId] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-sessions"] });
      await queryClient.invalidateQueries({ queryKey: ["teacher-classes"] });
    },
  });

  useEffect(() => {
    if (!roster.data) return;
    setStatuses((current) => {
      const next = { ...current };
      roster.data!.forEach((student) => {
        if (!next[student.student_id]) next[student.student_id] = student.status ?? "present";
      });
      return next;
    });
  }, [roster.data]);

  if (session.isLoading || roster.isLoading) return <LoadingBlock label="Loading class roster" />;
  const error = session.error ?? roster.error;
  if (error) return <ErrorNotice message={error.message} />;
  const currentSession = session.data!;
  const students = [...roster.data!].sort((left, right) =>
    left.roll_no.localeCompare(right.roll_no, undefined, { numeric: true, sensitivity: "base" }),
  );
  const filteredStudents = students.filter((student) =>
    `${student.roll_no} ${student.full_name}`.toLowerCase().includes(search.toLowerCase().trim()),
  );
  const counts = students.reduce(
    (result, student) => {
      if (statuses[student.student_id] === "present") result.present += 1;
      else if (statuses[student.student_id] === "absent") result.absent += 1;
      return result;
    },
    { present: 0, absent: 0 },
  );
  const records = students.map((student) => ({
    roll_no: student.roll_no,
    status: statuses[student.student_id] ?? "present",
  }));

  function setAllPresent() {
    setStatuses(Object.fromEntries(students.map((student) => [student.student_id, "present"])));
    setAbsentInput("");
    setAbsentError("");
  }

  function applyAbsentRolls(value: string) {
    setAbsentInput(value);
    const absentRolls = new Set(value.split(",").map((roll) => roll.trim()).filter(Boolean));
    const rolls = new Set(students.map((student) => student.roll_no));
    const unknown = [...absentRolls].filter((roll) => !rolls.has(roll));
    if (unknown.length) {
      setAbsentError(`Roll number${unknown.length === 1 ? "" : "s"} ${unknown.join(", ")} ${unknown.length === 1 ? "is" : "are"} not in this section.`);
      return;
    }
    setAbsentError("");
    setStatuses(Object.fromEntries(students.map((student) => [
      student.student_id,
      absentRolls.has(student.roll_no) ? "absent" : "present",
    ])) as Record<number, "present" | "absent">);
  }

  function toggleStudent(student: RosterStudent) {
    const nextStatus = statuses[student.student_id] === "present" ? "absent" : "present";
    setStatuses((current) => ({ ...current, [student.student_id]: nextStatus }));
  }

  function onRosterKey(event: KeyboardEvent<HTMLButtonElement>, index: number, student: RosterStudent) {
    if (event.key === "ArrowDown" || event.key === "ArrowUp") {
      event.preventDefault();
      const direction = event.key === "ArrowDown" ? 1 : -1;
      rowRefs.current[index + direction]?.focus();
    } else if (event.key === " " || event.key === "Enter") {
      event.preventDefault();
      toggleStudent(student);
    }
  }

  return (
    <>
      <div className="attendance-sticky">
        <Link className="back-link" to="/teacher/sessions"><ArrowLeft size={17} /> Session list</Link>
        <div className="attendance-session-bar">
          <div className="attendance-session-info">
            <span className="mono">{currentSession.course.code} · Section {currentSession.section.name}</span>
            <strong>{formatDate(currentSession.session_date)} · {formatTime(currentSession.start_time)}–{formatTime(currentSession.end_time)}</strong>
            {currentSession.topic && <small>{currentSession.topic}</small>}
          </div>
          <div className="live-counts"><span className="count-present"><Check size={15} /> Present {counts.present}</span><span className="count-absent">Absent {counts.absent}</span></div>
        </div>
      </div>
      {saved ? (
        <Panel className="saved-confirmation">
          <div className="saved-mark"><Check size={20} /></div>
          <div><strong>Attendance saved</strong><span>{counts.present} present · {counts.absent} absent</span></div>
          <Link className="text-link" to="/teacher/sessions">Return to session list <ArrowUpRight size={16} /></Link>
        </Panel>
      ) : (
        <>
          <PageHeading eyebrow="Attendance entry" title="Section roster" description={`${students.length} students · choose P or A for each roll number.`} />
          <Panel className="roster-tools">
            <label className="search-field"><MagnifyingGlass size={18} /><input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search roll number or name" /></label>
            <button className="button button-quiet" type="button" onClick={setAllPresent}>Mark all present</button>
            <label className="absent-roll-field">Absent roll numbers
              <input type="text" value={absentInput} onChange={(event) => applyAbsentRolls(event.target.value)} placeholder="12, 31" aria-describedby="absent-help" />
              <small id="absent-help">Enter comma-separated roll numbers; changes apply as you type.</small>
              {absentError && <small className="inline-error" role="alert">{absentError}</small>}
            </label>
          </Panel>
          {previewMutation.error && <ErrorNotice message={previewMutation.error.message} />}
          {saveMutation.error && <ErrorNotice message={saveMutation.error.message} />}
          <div className="roster-header"><span>Roll no.</span><span>Student name</span><span>Attendance</span></div>
          <div className="roster-list">
            {filteredStudents.map((student, visibleIndex) => {
              const current = statuses[student.student_id] ?? "present";
              return <div className="roster-row" key={student.student_id}>
                <span className="mono roster-roll">{student.roll_no}</span>
                <span className="roster-name">{student.full_name}</span>
                <button
                  ref={(node) => { rowRefs.current[visibleIndex] = node; }}
                  className={`attendance-toggle is-${current}`}
                  type="button"
                  role="switch"
                  aria-checked={current === "present"}
                  aria-label={`${student.roll_no}, ${student.full_name}: ${current}`}
                  onClick={() => toggleStudent(student)}
                  onKeyDown={(event) => onRosterKey(event, visibleIndex, student)}
                >
                  <span className={current === "present" ? "selected" : ""}>P <small>Present</small></span>
                  <span className={current === "absent" ? "selected" : ""}>A <small>Absent</small></span>
                </button>
              </div>;
            })}
            {!filteredStudents.length && <EmptyNotice>No students match this search.</EmptyNotice>}
          </div>
          <div className="attendance-save-bar">
            <span className="mono">Present {counts.present} · Absent {counts.absent}</span>
            <button className="button button-primary" type="button" disabled={previewMutation.isPending || students.length === 0} onClick={() => { setSaved(false); previewMutation.mutate(records); }}>
              {previewMutation.isPending ? "Checking changes…" : "Review and save"}
            </button>
          </div>
          {preview && <AttendanceConfirmDialog
            result={preview}
            onCancel={() => setPreview(null)}
            onConfirm={() => saveMutation.mutate(records)}
            saving={saveMutation.isPending}
          />}
        </>
      )}
    </>
  );
}

function AttendanceConfirmDialog({
  result,
  onCancel,
  onConfirm,
  saving,
}: {
  result: AttendanceSaveResult;
  onCancel: () => void;
  onConfirm: () => void;
  saving: boolean;
}) {
  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="dialog-panel attendance-confirm" role="dialog" aria-modal="true" aria-labelledby="confirm-attendance-title">
        <span className="eyebrow">Review changes · {result.diff.length} changed</span>
        <h2 id="confirm-attendance-title">Save {result.present} present, {result.absent} absent?</h2>
        {result.diff.length ? (
          <div className="diff-list">
            {result.diff.slice(0, 7).map((item) => (
              <div key={item.roll_no}><span className="mono">{item.roll_no}</span><span>{item.name}</span><span>{item.from ?? "—"} → <strong>{item.to}</strong></span></div>
            ))}
            {result.diff.length > 7 && <small>And {result.diff.length - 7} more changed records.</small>}
          </div>
        ) : <EmptyNotice>There are no changes from the saved roster.</EmptyNotice>}
        <p className="quiet-note">The full section roster will be saved together.</p>
        <div className="form-actions"><button className="button button-quiet" type="button" onClick={onCancel}>Keep editing</button><button className="button button-primary" type="button" onClick={onConfirm} disabled={saving}>{saving ? "Saving…" : "Confirm save"}</button></div>
      </section>
    </div>
  );
}

function ConfirmDialog({
  title,
  description,
  confirmLabel,
  error,
  onCancel,
  onConfirm,
}: {
  title: string;
  description: string;
  confirmLabel: string;
  error?: string;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  return (
    <div className="dialog-backdrop" role="presentation">
      <section className="dialog-panel" role="dialog" aria-modal="true" aria-labelledby="confirm-title">
        <span className="eyebrow">Confirm action</span><h2 id="confirm-title">{title}</h2><p>{description}</p>
        {error && <ErrorNotice message={error} />}
        <div className="form-actions"><button className="button button-quiet" type="button" onClick={onCancel}>Cancel</button><button className="button button-danger" type="button" onClick={onConfirm}>{confirmLabel}</button></div>
      </section>
    </div>
  );
}
