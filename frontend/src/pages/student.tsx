import { ArrowLeft, ArrowUpRight, CalendarBlank, WarningCircle } from "@phosphor-icons/react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  api,
  formatDate,
  formatMoney,
  formatTime,
  type Assignment,
  type CourseAttendance,
} from "../lib/api";
import {
  BandLabel,
  ClassLabel,
  EmptyNotice,
  ErrorNotice,
  LoadingBlock,
  PageHeading,
  Panel,
  SectionHeading,
} from "../components/ui";

function useStudentDashboard() {
  const profile = useQuery({ queryKey: ["profile"], queryFn: api.profile });
  const attendance = useQuery({ queryKey: ["attendance"], queryFn: api.attendance });
  const fees = useQuery({ queryKey: ["fees"], queryFn: api.fees });
  const assignments = useQuery({ queryKey: ["assignments"], queryFn: api.assignments });
  return { profile, attendance, fees, assignments };
}

export function StudentHome() {
  const { profile, attendance, fees, assignments } = useStudentDashboard();
  const isLoading = profile.isLoading || attendance.isLoading || fees.isLoading || assignments.isLoading;
  const error = profile.error ?? attendance.error ?? fees.error ?? assignments.error;
  if (isLoading) return <LoadingBlock label="Opening student record" />;
  if (error) return <ErrorNotice message={error.message} />;

  const student = profile.data!;
  const overall = attendance.data!.overall;
  const fee = fees.data?.[0];
  const pendingAssignments = assignments.data?.filter((item) => item.status === "pending") ?? [];
  const today = new Intl.DateTimeFormat("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    timeZone: "Asia/Kolkata",
  }).format(new Date());

  return (
    <>
      <PageHeading
        eyebrow={`${student.program_name} · Semester ${student.semester}`}
        title={student.full_name}
        description={`${student.section_code} · Roll ${student.roll_no} · Academic year ${student.academic_year}`}
      />
      <div className="student-home-grid">
        <Panel className="attendance-feature">
          <div className="feature-topline">
            <span className="eyebrow">Attendance · Overall</span>
            <BandLabel band={overall.band} shortage={overall.shortage} />
          </div>
          <div className="feature-figure-row">
            <span className="feature-figure">{overall.percent.toFixed(2)}%</span>
            <span className="feature-formula mono">{overall.formula}</span>
          </div>
          <div className="progress-track" aria-label={`${overall.percent}% attendance`}>
            <span style={{ width: `${Math.min(overall.percent, 100)}%` }} />
          </div>
          <Link className="text-link" to="/student/attendance">
            View course-wise attendance <ArrowUpRight size={16} />
          </Link>
        </Panel>

        <Panel className="fee-feature">
          <div className="eyebrow">Fees · {fee?.academic_year ?? student.academic_year}</div>
          {fee ? (
            <>
              <div className="fee-pending">{formatMoney(fee.pending_amount)}</div>
              <div className="fee-caption">Pending balance</div>
              <div className="fee-line">
                <span>Total</span><strong>{formatMoney(fee.total_amount)}</strong>
                <span>Paid</span><strong>{formatMoney(fee.paid_amount)}</strong>
              </div>
              <Link className="text-link" to="/student/fees">Fee details <ArrowUpRight size={16} /></Link>
            </>
          ) : (
            <EmptyNotice>No fee record is available for this year.</EmptyNotice>
          )}
        </Panel>
      </div>

      <div className="home-section-grid">
        <Panel>
          <SectionHeading title="Today’s sessions" detail={today} />
          <div className="day-empty">
            <CalendarBlank size={20} />
            <span>No sessions scheduled today.</span>
          </div>
          <p className="quiet-note">The student timetable is not published in this demo yet.</p>
        </Panel>
        <Panel>
          <SectionHeading
            title="Assignments to submit"
            detail={`${pendingAssignments.length} pending`}
            action={<Link className="text-link" to="/student/assignments">All work <ArrowUpRight size={16} /></Link>}
          />
          {pendingAssignments.length ? (
            <ul className="compact-list">
              {pendingAssignments.slice(0, 4).map((item) => (
                <li key={item.id}>
                  <span className="list-marker" aria-hidden="true" />
                  <div>
                    <strong>{item.title}</strong>
                    <small>{item.course.code} · Due {formatDate(item.due_at)}</small>
                  </div>
                  <span className="mono list-marks">/{item.max_marks}</span>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyNotice>There are no pending assignments.</EmptyNotice>
          )}
        </Panel>
      </div>
    </>
  );
}

export function StudentAttendance() {
  const attendance = useQuery({ queryKey: ["attendance"], queryFn: api.attendance });
  if (attendance.isLoading) return <LoadingBlock label="Loading attendance" />;
  if (attendance.error) return <ErrorNotice message={attendance.error.message} />;
  const data = attendance.data!;
  return (
    <>
      <PageHeading
        eyebrow="Student record · Attendance"
        title="Attendance by course"
        description="Only sessions with saved attendance count toward these totals."
      />
      <Panel className="overall-strip">
        <div>
          <span className="eyebrow">Overall attendance</span>
          <div className="overall-number">{data.overall.percent.toFixed(2)}%</div>
          <span className="mono muted-copy">{data.overall.formula}</span>
        </div>
        <BandLabel band={data.overall.band} shortage={data.overall.shortage} />
      </Panel>
      <div className="course-attendance-list">
        {data.courses.map((course) => <CourseAttendanceRow key={course.course.id} row={course} />)}
      </div>
      <Panel className="attendance-table-panel">
        <SectionHeading title="Session totals" detail="Updated attendance only" />
        <div className="table-scroll">
          <table className="data-table">
            <thead><tr><th>Course</th><th>Type</th><th>Sessions updated</th><th>Outcome</th><th>Sessions</th></tr></thead>
            <tbody>
              {data.courses.map((row) => (
                <tr key={row.course.id}>
                  <td><ClassLabel code={row.course.code} name={row.course.name} /></td>
                  <td className="capitalize" data-label="Type">{row.kind}</td>
                  <td className="mono" data-label="Sessions updated">{row.total}</td>
                  <td data-label="Outcome"><span className="mono">{row.present} / {row.total} present</span></td>
                  <td data-label="Sessions"><Link className="table-link" to={`/student/attendance/${row.course.id}`}>View <ArrowUpRight size={14} /></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </>
  );
}

function CourseAttendanceRow({ row }: { row: CourseAttendance }) {
  return (
    <Panel className="course-attendance-row">
      <div className="course-attendance-main">
        <ClassLabel code={row.course.code} name={row.course.name} />
        <span className="type-label">{row.kind}</span>
      </div>
      <div className="course-attendance-bar">
        <div className="progress-track"><span style={{ width: `${Math.min(row.percent, 100)}%` }} /></div>
        <span className="mono">{row.present}/{row.total}</span>
      </div>
      <div className="course-attendance-result">
        <strong className="mono">{row.percent.toFixed(2)}%</strong>
        <BandLabel band={row.band} shortage={row.shortage} />
      </div>
      <Link className="row-open" to={`/student/attendance/${row.course.id}`} aria-label={`View ${row.course.code} sessions`}>
        <ArrowUpRight size={18} />
      </Link>
    </Panel>
  );
}

export function StudentCourseAttendance() {
  const { courseId } = useParams();
  const id = Number(courseId);
  const summary = useQuery({ queryKey: ["attendance"], queryFn: api.attendance });
  const sessions = useQuery({ queryKey: ["course-sessions", id], queryFn: () => api.courseSessions(id), enabled: Number.isInteger(id) });
  if (summary.isLoading || sessions.isLoading) return <LoadingBlock label="Loading session history" />;
  const error = summary.error ?? sessions.error;
  if (error) return <ErrorNotice message={error.message} />;
  const course = summary.data!.courses.find((row) => row.course.id === id);
  if (!course) return <ErrorNotice message="This course is not part of your section." />;
  return (
    <>
      <Link className="back-link" to="/student/attendance"><ArrowLeft size={17} /> Attendance overview</Link>
      <PageHeading eyebrow={`${course.course.code} · ${course.kind}`} title={course.course.name} description="Session attendance history" />
      <Panel className="course-history-summary">
        <div><span className="eyebrow">Attendance</span><strong>{course.percent.toFixed(2)}%</strong></div>
        <BandLabel band={course.band} shortage={course.shortage} />
        <span className="mono muted-copy">Present {course.present} / Total {course.total}</span>
      </Panel>
      <Panel className="history-panel">
        <SectionHeading title="Updated sessions" detail={`${sessions.data!.length} sessions`} />
        {sessions.data!.length ? (
          <div className="table-scroll">
            <table className="data-table history-table">
              <thead><tr><th>Date</th><th>Time</th><th>Topic</th><th>Outcome</th></tr></thead>
              <tbody>{sessions.data!.map((session, index) => (
                <tr key={`${session.session_date}-${session.start_time}-${index}`}>
                  <td data-label="Date">{formatDate(session.session_date)}</td>
                  <td className="mono" data-label="Time">{formatTime(session.start_time)}–{formatTime(session.end_time)}</td>
                  <td data-label="Topic">{session.topic || "—"}</td>
                  <td data-label="Outcome"><span className={`outcome outcome-${session.outcome.toLowerCase()}`}>{session.outcome}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        ) : <EmptyNotice>No attendance has been updated for this course yet.</EmptyNotice>}
      </Panel>
    </>
  );
}

export function StudentFees() {
  const fees = useQuery({ queryKey: ["fees"], queryFn: api.fees });
  if (fees.isLoading) return <LoadingBlock label="Loading fee record" />;
  if (fees.error) return <ErrorNotice message={fees.error.message} />;
  const fee = fees.data?.[0];
  return (
    <>
      <PageHeading eyebrow="Student record · Accounts" title="Fees" description="Current academic year fee summary." />
      {!fee ? <EmptyNotice>No fee record is available.</EmptyNotice> : (
        <Panel className="fee-ledger">
          <SectionHeading title={`Academic year ${fee.academic_year}`} detail={`Due date · ${formatDate(fee.due_date)}`} />
          <dl className="ledger-list">
            <div><dt>Total fee</dt><dd>{formatMoney(fee.total_amount)}</dd></div>
            <div><dt>Paid</dt><dd>{formatMoney(fee.paid_amount)}</dd></div>
            <div><dt>Fine</dt><dd>{formatMoney(fee.fine_amount)}</dd></div>
            <div className="ledger-total"><dt>Pending balance</dt><dd>{formatMoney(fee.pending_amount)}</dd></div>
          </dl>
          {fee.pending_amount > 0 && <div className="notice notice-warning"><WarningCircle size={18} /> Please contact the accounts office for payment options.</div>}
        </Panel>
      )}
    </>
  );
}

export function StudentResults() {
  const results = useQuery({ queryKey: ["results"], queryFn: api.results });
  if (results.isLoading) return <LoadingBlock label="Loading results" />;
  if (results.error) return <ErrorNotice message={results.error.message} />;
  return (
    <>
      <PageHeading eyebrow="Student record · Assessment" title="Results" description="Published internal assessment marks." />
      <Panel className="data-panel">
        <SectionHeading title="Internal assessments" detail={`${results.data!.length} published marks`} />
        {results.data!.length ? (
          <div className="table-scroll"><table className="data-table">
            <thead><tr><th>Course</th><th>Assessment</th><th>Marks</th><th>Published</th></tr></thead>
            <tbody>{results.data!.map((result, index) => (
              <tr key={`${result.course.id}-${result.exam_name}-${index}`}>
                <td data-label="Course"><ClassLabel code={result.course.code} name={result.course.name} /></td>
                <td data-label="Assessment">{result.exam_name}</td>
                <td className="mono marks-cell" data-label="Marks">{result.marks_obtained} <span>/ {result.max_marks}</span></td>
                <td data-label="Published">{result.published_at ? formatDate(result.published_at) : "Not published"}</td>
              </tr>
            ))}</tbody>
          </table></div>
        ) : <EmptyNotice>No results have been published yet.</EmptyNotice>}
      </Panel>
    </>
  );
}

export function StudentAssignments() {
  const assignments = useQuery({ queryKey: ["assignments"], queryFn: api.assignments });
  if (assignments.isLoading) return <LoadingBlock label="Loading assignments" />;
  if (assignments.error) return <ErrorNotice message={assignments.error.message} />;
  const items = assignments.data!;
  const pending = items.filter((item) => item.status === "pending");
  return (
    <>
      <PageHeading eyebrow="Student record · Coursework" title="Assignments" description="Due dates and submission status for your section." />
      <div className="assignment-count-line"><span>{pending.length} pending</span><span>{items.length - pending.length} submitted</span></div>
      <div className="assignment-list">
        {items.length ? items.map((item) => <AssignmentCard item={item} key={item.id} />) : <EmptyNotice>No assignments have been posted yet.</EmptyNotice>}
      </div>
    </>
  );
}

function AssignmentCard({ item }: { item: Assignment }) {
  return (
    <Panel className="assignment-card">
      <div className="assignment-main">
        <div className="eyebrow">{item.course.code} · {item.course.name}</div>
        <h2>{item.title}</h2>
        {item.description && <p>{item.description}</p>}
      </div>
      <div className="assignment-meta">
        <span className="assignment-status"><span className={`status-square ${item.status === "pending" ? "is-pending" : "is-done"}`} />{item.status}</span>
        <span>Due {formatDate(item.due_at, { year: undefined })}</span>
        <span className="mono">Max {item.max_marks}</span>
      </div>
      {item.status !== "pending" && item.submitted_at && <div className="submitted-note">Submitted {formatDate(item.submitted_at)}</div>}
      {item.status === "pending" && <div className="quiet-note">Online submission is not enabled in this demo.</div>}
    </Panel>
  );
}
