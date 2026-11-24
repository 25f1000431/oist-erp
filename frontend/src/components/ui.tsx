import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import type { ReactNode } from "react";
import { useQueryClient } from "@tanstack/react-query";
import {
  BookOpen,
  CalendarCheck,
  ChalkboardTeacher,
  House,
  Notebook,
  SignOut,
  Wallet,
} from "@phosphor-icons/react";
import type { Icon } from "@phosphor-icons/react";
import { useAuth } from "../lib/auth";

interface NavItem {
  to: string;
  label: string;
  icon: Icon;
}

const studentNav: NavItem[] = [
  { to: "/student", label: "Overview", icon: House },
  { to: "/student/attendance", label: "Attendance", icon: CalendarCheck },
  { to: "/student/fees", label: "Fees", icon: Wallet },
  { to: "/student/results", label: "Results", icon: BookOpen },
  { to: "/student/assignments", label: "Assignments", icon: Notebook },
];

const teacherNav: NavItem[] = [
  { to: "/teacher", label: "My classes", icon: ChalkboardTeacher },
  { to: "/teacher/sessions", label: "Sessions", icon: CalendarCheck },
];

export function AppShell({ role }: { role: "student" | "teacher" }) {
  const { user, signOut } = useAuth();
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const location = useLocation();
  const nav = role === "student" ? studentNav : teacherNav;
  const roleTitle = role === "student" ? "Student record" : "Faculty workspace";

  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Main navigation">
        <NavLink to={role === "student" ? "/student" : "/teacher"} className="brand">
          <img src="/favicon-32.png" alt="" width="34" height="34" />
          <span>
            <strong>OIST</strong>
            <small>Academic portal</small>
          </span>
        </NavLink>
        <div className="sidebar-label">{roleTitle}</div>
        <nav className="side-nav">
          {nav.map(({ to, label, icon: IconComponent }) => (
            <NavLink
              key={to}
              to={to}
              end={to === "/student" || to === "/teacher"}
              className={({ isActive }) => `nav-link${isActive ? " is-active" : ""}`}
            >
              <IconComponent size={19} weight="regular" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-bottom">
          <div className="account-block">
            <span className="account-mark" aria-hidden="true">
              {(user?.login_id ?? "U").slice(0, 1).toUpperCase()}
            </span>
            <span className="account-meta">
              <strong>{user?.login_id ?? "Account"}</strong>
              <small>{role === "student" ? "Student" : "Teacher"}</small>
            </span>
            <button
              className="icon-button signout-button"
              type="button"
              aria-label="Sign out"
              title="Sign out"
              onClick={() => {
                signOut();
                queryClient.clear();
                navigate("/login", { replace: true, state: { from: location.pathname } });
              }}
            >
              <SignOut size={18} />
            </button>
          </div>
        </div>
      </aside>
      <div className="mobile-topbar">
        <NavLink to={role === "student" ? "/student" : "/teacher"} className="brand compact-brand">
          <img src="/favicon-32.png" alt="" width="30" height="30" />
          <strong>OIST</strong>
        </NavLink>
        <button
          className="icon-button"
          type="button"
          aria-label="Sign out"
          onClick={() => {
            signOut();
            queryClient.clear();
            navigate("/login", { replace: true });
          }}
        >
          <SignOut size={19} />
        </button>
      </div>
      <main className="main-content">
        <div className="desktop-topline">
          <span>{roleTitle}</span>
          <span className="mono">{user?.login_id}</span>
        </div>
        <Outlet />
      </main>
      <nav className="mobile-nav" aria-label="Mobile navigation">
        {nav.map(({ to, label, icon: IconComponent }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/student" || to === "/teacher"}
            className={({ isActive }) => `mobile-nav-link${isActive ? " is-active" : ""}`}
            aria-label={label}
          >
            <IconComponent size={21} weight="regular" />
            <span>{label}</span>
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description?: string;
  action?: ReactNode;
}) {
  return (
    <header className="page-heading">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {description && <p>{description}</p>}
      </div>
      {action && <div className="page-heading-action">{action}</div>}
    </header>
  );
}

export function Panel({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <section className={`panel ${className}`}>{children}</section>;
}

export function SectionHeading({
  title,
  detail,
  action,
}: {
  title: string;
  detail?: string;
  action?: ReactNode;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {detail && <p>{detail}</p>}
      </div>
      {action}
    </div>
  );
}

export function BandLabel({ band, shortage = false }: { band: string; shortage?: boolean }) {
  return (
    <span className={`band-label band-${band.toLowerCase()}`}>
      <span className="band-dot" aria-hidden="true" />
      {band}
      {shortage && <span className="short-flag">Short</span>}
    </span>
  );
}

export function LoadingBlock({ label = "Loading record" }: { label?: string }) {
  return (
    <div className="loading-block" role="status">
      <span className="loading-rule" /> {label}…
    </div>
  );
}

export function ErrorNotice({ message }: { message: string }) {
  return (
    <div className="notice notice-error" role="alert">
      {message}
    </div>
  );
}

export function EmptyNotice({ children }: { children: ReactNode }) {
  return <div className="empty-notice">{children}</div>;
}

export function ClassLabel({ code, name }: { code: string; name: string }) {
  return (
    <span className="course-label">
      <span className="mono">{code}</span>
      <span>{name}</span>
    </span>
  );
}
