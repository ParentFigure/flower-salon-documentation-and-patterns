import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAuth } from "../context/AuthContext";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [form, setForm] = useState({ email: "", password: "", full_name: "", phone: "" });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(name, value) {
    setForm((current) => ({ ...current, [name]: value }));
  }

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await api.post("/api/auth/register", form);
      await login(form.email, form.password);
      navigate("/profile", { replace: true });
    } catch (err) {
      setError(err.message || "Не вдалося зареєструватися");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-card">
      <p className="eyebrow">Новий клієнт</p>
      <h1>Реєстрація</h1>
      <form onSubmit={handleSubmit} className="form-stack">
        <label>Ім’я<input value={form.full_name} onChange={(e) => update("full_name", e.target.value)} required /></label>
        <label>Телефон<input value={form.phone} onChange={(e) => update("phone", e.target.value)} required /></label>
        <label>Email<input type="email" value={form.email} onChange={(e) => update("email", e.target.value)} required /></label>
        <label>Пароль<input type="password" value={form.password} onChange={(e) => update("password", e.target.value)} minLength="8" required /></label>
        {error && <p className="error-text">{error}</p>}
        <button className="button" disabled={submitting} type="submit">
          {submitting ? "Створення..." : "Створити акаунт"}
        </button>
      </form>
    </section>
  );
}
