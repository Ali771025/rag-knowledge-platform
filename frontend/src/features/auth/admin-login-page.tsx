import { FormEvent, useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { loginAdmin } from "@/services/auth/authService";
import { useAdminAuthStore } from "@/state/auth-store";
import { appRoutes } from "@/app/routes/contracts";

interface AdminLoginLocationState {
  from?: {
    pathname?: string;
  };
}

export function AdminLoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = useAdminAuthStore((state) => state.isAuthenticated);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const nextPath = (location.state as AdminLoginLocationState | null)?.from?.pathname ?? appRoutes.admin.knowledge;

  useEffect(() => {
    if (isAuthenticated) {
      navigate(nextPath, { replace: true });
    }
  }, [isAuthenticated, navigate, nextPath]);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setErrorMessage(null);
    setIsSubmitting(true);

    try {
      await loginAdmin({ email: email.trim(), password });
      navigate(nextPath, { replace: true });
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Login failed.");
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="mx-auto flex min-h-dvh w-full max-w-md items-center px-4">
      <section className="w-full rounded-2xl border border-border bg-background p-6 shadow-sm">
        <h1 className="text-xl font-semibold text-foreground">Admin Sign In</h1>
        <p className="mt-1 text-sm text-muted-foreground">Use your admin email and password to access knowledge management.</p>

        <form onSubmit={onSubmit} className="mt-5 space-y-4">
          <label className="block space-y-1 text-sm">
            <span className="text-foreground">Email</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-primary"
              autoComplete="email"
              required
            />
          </label>

          <label className="block space-y-1 text-sm">
            <span className="text-foreground">Password</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              className="w-full rounded-lg border border-border bg-background px-3 py-2 outline-none focus-visible:ring-2 focus-visible:ring-primary"
              autoComplete="current-password"
              minLength={8}
              required
            />
          </label>

          {errorMessage ? (
            <p className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">{errorMessage}</p>
          ) : null}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full rounded-lg border border-border bg-primary px-3 py-2 text-sm font-medium text-primary-foreground disabled:cursor-not-allowed disabled:opacity-60"
          >
            {isSubmitting ? "Signing in..." : "Sign In"}
          </button>
        </form>
      </section>
    </main>
  );
}
