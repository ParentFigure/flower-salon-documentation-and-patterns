import { useMemo, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

function messageForError(error) {
  if (error instanceof ApiError && error.status === 401) {
    return "Неправильний email або пароль.";
  }
  return error?.message || "Не вдалося увійти. Спробуйте ще раз.";
}

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const returnTo = useMemo(() => {
    const pathname = location.state?.from?.pathname;
    return typeof pathname === "string" && pathname.startsWith("/")
      ? pathname
      : null;
  }, [location.state]);

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const normalizedEmail = email.trim().toLowerCase();
    if (!normalizedEmail || !password) {
      setError("Введіть email і пароль.");
      return;
    }

    setSubmitting(true);
    try {
      const currentUser = await login(normalizedEmail, password);
      navigate(returnTo || (currentUser.role === "ADMIN" ? "/admin" : "/profile"), {
        replace: true,
      });
    } catch (err) {
      setError(messageForError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <div className="auth-heading">
        <p className="eyebrow">Авторизація</p>
        <h1>Увійти</h1>
        <p className="muted">Замовлення, бонуси та повідомлення зберігаються у твоєму кабінеті.</p>
      </div>

      <form onSubmit={handleSubmit} className="form-stack" noValidate>
        <label>
          Email
          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            autoComplete="email"
            placeholder="name@example.com"
            required
          />
        </label>

        <label>
          Пароль
          <span className="password-field">
            <input
              type={showPassword ? "text" : "password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              autoComplete="current-password"
              required
            />
            <button
              className="password-toggle"
              type="button"
              onClick={() => setShowPassword((value) => !value)}
            >
              {showPassword ? "Сховати" : "Показати"}
            </button>
          </span>
        </label>

        {error && <p className="form-alert" role="alert">{error}</p>}

        <button className="button auth-submit" disabled={submitting} type="submit">
          {submitting ? "Входимо..." : "Увійти"}
        </button>
      </form>

      <p className="auth-switch muted">
        Немає акаунта? <Link to="/register">Зареєструватися</Link>
      </p>
    </section>
  );
}
