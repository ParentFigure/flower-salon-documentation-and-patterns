import { Link } from "react-router-dom";

export default function HomePage() {
  return (
    <section className="hero">
      <div>
        <p className="eyebrow">Мережа квіткових салонів</p>
        <h1>Букети для важливих моментів</h1>
        <p className="lead">
          Обирай готовий букет або створи власний. Доставка, самовивіз,
          бонуси та персональний кабінет — в одному сервісі.
        </p>
        <div className="actions">
          <Link className="button" to="/catalog">Перейти до каталогу</Link>
          <Link className="button secondary" to="/register">Створити акаунт</Link>
        </div>
      </div>
      <div className="hero-card" aria-hidden="true">
        <span>🌷</span><span>🌹</span><span>🌿</span>
      </div>
    </section>
  );
}
