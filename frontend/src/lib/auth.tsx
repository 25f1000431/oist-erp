import { createContext, useContext, useEffect, useMemo, useState } from "react";
import type { ReactNode } from "react";
import { api, type Role, type UserSummary } from "./api";

interface AuthValue {
  user: UserSummary | null;
  loading: boolean;
  signIn: (loginId: string, password: string) => Promise<UserSummary>;
  signOut: () => void;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserSummary | null>(() => {
    const raw = sessionStorage.getItem("oist_user");
    return raw ? (JSON.parse(raw) as UserSummary) : null;
  });
  const [loading, setLoading] = useState(Boolean(sessionStorage.getItem("oist_access_token")));

  useEffect(() => {
    if (!sessionStorage.getItem("oist_access_token")) return;
    api
      .me()
      .then((currentUser) => {
        setUser(currentUser);
        sessionStorage.setItem("oist_user", JSON.stringify(currentUser));
      })
      .catch(() => {
        sessionStorage.removeItem("oist_access_token");
        sessionStorage.removeItem("oist_user");
        setUser(null);
      })
      .finally(() => setLoading(false));
  }, []);

  const value = useMemo<AuthValue>(
    () => ({
      user,
      loading,
      async signIn(loginId, password) {
        const result = await api.login(loginId, password);
        sessionStorage.setItem("oist_access_token", result.access_token);
        sessionStorage.setItem("oist_user", JSON.stringify(result.user));
        setUser(result.user);
        return result.user;
      },
      signOut() {
        sessionStorage.removeItem("oist_access_token");
        sessionStorage.removeItem("oist_user");
        setUser(null);
      },
    }),
    [loading, user],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider.");
  return value;
}

export function homeForRole(role: Role): string {
  if (role === "student") return "/student";
  if (role === "teacher") return "/teacher";
  return "/access-unavailable";
}
