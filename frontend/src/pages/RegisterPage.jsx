import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";

const initialForm = {
  full_name: "",
  phone: "",
  email: "",
  password: "",
  confirmPassword: "",
};

function validate(form) {
  if (form.full_name.trim().length < 2) return "Вкажіть ім’я довжиною щонайменше 2 символи.";
  if (!form.email.trim().includes("@")) return "Вкажіть коректний email.";
  if (form.password.length < 8) return "Пароль має містити щонайменше 8 символів.";
  if (form.password !== form.confirmPassword) return "Паролі не збігаються.";
  return "";
}

function messageForError(error) {
  if (error instanceof ApiError && error.status === 409) {
    return "Користувач із таким email уже зареєстрований.";
  }
  if (error instanceof ApiError && error.status === 422) {
    return "Перевірте правильність заповнення форми.";
  }
  return error?.message || "Не вдалося зареєструватися. Спробуйте ще раз.";
}

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [form, setForm] = useState(initialForm);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    const validationError = validate(form);
    if (validationError) {
      setError(validationError);
      return;
    }

    setSubmitting(true);
    try {
      await register({
        email: form.email,
        password: form.password,
        full_name: form.full_name,
        phone: form.phone,
      });
      navigate("/profile", { replace: true });
    } catch (err) {
      setError(messageForError(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card auth-card--wide">
      <div className="auth-heading">
        <p className="eyebrow">Новий клієнт</p>
        <h1>Реєстрація</h1>
        <p className="muted">Створи кабінет, щоб оформлювати замовлення й користуватися програмою лояльності.</p>
      </div>

      <form onSubmit={handleSubmit} className="form-stack" noValidate>
        <div className="form-grid">
          <label>
            Ім’я
            <input
              value={form.full_name}
              onChange={(event) => update("full_name", event.target.value)}
              autoComplete="name"
              maxLength="120"
              required
            />
          </label>

          <label>
            Телефон <span className="optional-label">необов’язково</span>
            <input
              value={form.phone}
              onChange={(event) => update("phone", event.target.value)}
              autoComplete="tel"
              maxLength="30"
              placeholder="+380..."
            />
          </label>
        </div>

        <label>
          Email
          <input
            type="email"
            value={form.email}
            onChange={(event) => update("email", event.target.value)}
            autoComplete="email"
            placeholder="name@example.com"
            required
          />
        </label>

        <div className="form-grid">
          <label>
            Пароль
            <span className="password-field">
              <input
                type={showPassword ? "text" : "password"}
                value={form.password}
                onChange={(event) => update("password", event.target.value)}
                autoComplete="new-password"
                minLength="8"
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

          <label>
            Повтори пароль
            <input
              type={showPassword ? "text" : "password"}
              value={form.confirmPassword}
              onChange={(event) => update("confirmPassword", event.target.value)}
              autoComplete="new-password"
              minLength="8"
              required
            />
          </label>
        </div>

        <p className="form-hint">Мінімум 8 символів.</p>

        {error && <p className="form-alert" role="alert">{error}</p>}

        <button className="button auth-submit" disabled={submitting} type="submit">
          {submitting ? "Створюємо акаунт..." : "Створити акаунт"}
        </button>
      </form>

      <p className="auth-switch muted">
        Уже є акаунт? <Link to="/login">Увійти</Link>
      </p>
    </section>
  );
}
