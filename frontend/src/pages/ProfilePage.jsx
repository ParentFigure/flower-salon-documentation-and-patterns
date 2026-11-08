import { useAuth } from "../context/AuthContext";

export default function ProfilePage() {
  const { user } = useAuth();
  return (
    <section className="page-section">
      <p className="eyebrow">Персональний кабінет</p>
      <h1>Привіт, {user?.email}</h1>
      <p className="muted">
        Тут з’являться дані `/api/profile`: картка лояльності, бонуси,
        останні замовлення та повідомлення.
      </p>
    </section>
  );
}
