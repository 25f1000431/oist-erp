import { useState } from "react";
import type { FormEvent } from "react";
import { ArrowRight, LockKey, UserCircle } from "@phosphor-icons/react";
import { Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth, homeForRole } from "../lib/auth";
import type { ApiError } from "../lib/api";

export function LoginPage() {
  const { user, signIn, loading } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [loginId, setLoginId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [pending, setPending] = useState(false);
  if (loading) return <div className="login-loading">Checking your account…</div>;
  if (user) return <Navigate to={homeForRole(user.role)} replace />;

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setPending(true);
    try {
      const account = await signIn(loginId.trim(), password);
      const from = (location.state as { from?: string } | null)?.from;
      navigate(from && from !== "/login" ? from : homeForRole(account.role), { replace: true });
    } catch (cause) {
      const apiError = cause as ApiError;
      setError(apiError.status === 429 ? "Too many attempts. Wait a minute, then try again." : "Login failed. Check your ID and password.");
    } finally {
      setPending(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-aside">
        <div className="login-brand"><img src="/favicon-32.png" alt="" width="38" height="38" /><span><strong>OIST</strong><small>Academic portal</small></span></div>
        <div className="login-aside-copy">
          <span className="eyebrow">CSE · B.Tech · Semester V</span>
          <h1>Academic records, clearly kept.</h1>
          <p>Attendance, coursework, fees and results for students and faculty.</p>
        </div>
        <span className="login-aside-foot">OIST Mock ERP · 2026–27</span>
      </section>
      <section className="login-form-side">
        <div className="login-form-wrap">
          <span className="eyebrow">Secure sign in</span>
          <h2>Sign in to your account</h2>
          <p className="login-intro">Use your student roll number or faculty login ID.</p>
          <form className="form-stack login-form" onSubmit={submit}>
            <label className="field-label">Login ID
              <span className="input-with-icon"><UserCircle size={19} /><input autoComplete="username" value={loginId} onChange={(event) => setLoginId(event.target.value)} placeholder="Roll number or faculty ID" required /></span>
            </label>
            <label className="field-label">Password
              <span className="input-with-icon"><LockKey size={19} /><input autoComplete="current-password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="Enter your password" required /></span>
            </label>
            {error && <div className="notice notice-error" role="alert">{error}</div>}
            <button className="button button-primary login-submit" disabled={pending} type="submit">{pending ? "Signing in…" : "Sign in"}<ArrowRight size={17} /></button>
          </form>
          <p className="login-note">Demo accounts are issued by the department.</p>
        </div>
      </section>
    </main>
  );
}
