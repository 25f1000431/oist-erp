import { Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { useAuth, homeForRole } from "./lib/auth";
import { AppShell } from "./components/ui";
import { LoginPage } from "./pages/login";
import {
  StudentAssignments,
  StudentAttendance,
  StudentCourseAttendance,
  StudentFees,
  StudentHome,
  StudentResults,
} from "./pages/student";
import {
  TeacherAttendance,
  TeacherCreateSession,
  TeacherHome,
  TeacherSessions,
} from "./pages/teacher";

function RequireRole({ role }: { role: "student" | "teacher" }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="route-loading">Opening your workspace…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== role) return <Navigate to={homeForRole(user.role)} replace />;
  return <Outlet />;
}

function AccessUnavailable() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();
  return (
    <main className="access-unavailable">
      <img src="/favicon-32.png" alt="" width="34" height="34" />
      <span className="eyebrow">OIST Academic portal</span>
      <h1>This workspace is not part of this demo.</h1>
      <p>The signed-in role is <strong>{user?.role}</strong>. Student and teacher views are available.</p>
      <button className="button button-primary" onClick={() => { signOut(); navigate("/login", { replace: true }); }} type="button">Sign out</button>
    </main>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/access-unavailable" element={<AccessUnavailable />} />
      <Route element={<RequireRole role="student" />}>
        <Route element={<AppShell role="student" />}>
          <Route path="/student" element={<StudentHome />} />
          <Route path="/student/attendance" element={<StudentAttendance />} />
          <Route path="/student/attendance/:courseId" element={<StudentCourseAttendance />} />
          <Route path="/student/fees" element={<StudentFees />} />
          <Route path="/student/results" element={<StudentResults />} />
          <Route path="/student/assignments" element={<StudentAssignments />} />
        </Route>
      </Route>
      <Route element={<RequireRole role="teacher" />}>
        <Route element={<AppShell role="teacher" />}>
          <Route path="/teacher" element={<TeacherHome />} />
          <Route path="/teacher/sessions" element={<TeacherSessions />} />
          <Route path="/teacher/sessions/new" element={<TeacherCreateSession />} />
          <Route path="/teacher/sessions/:id/attendance" element={<TeacherAttendance />} />
        </Route>
      </Route>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
