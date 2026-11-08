export default function AdminPage() {
  return (
    <section className="page-section">
      <p className="eyebrow">Адмін-панель</p>
      <h1>Керування мережею</h1>
      <div className="dashboard-grid">
        {['Букети', 'Квіти', 'Замовлення', 'Салони', 'Доставка', 'Лояльність'].map((name) => (
          <article className="dashboard-card" key={name}><h2>{name}</h2><p>Модуль буде підключено до REST API.</p></article>
        ))}
      </div>
    </section>
  );
}
