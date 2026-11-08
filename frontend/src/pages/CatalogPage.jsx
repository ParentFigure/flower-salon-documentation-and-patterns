export default function CatalogPage() {
  return (
    <section className="page-section">
      <p className="eyebrow">Каталог</p>
      <h1>Букети</h1>
      <p className="muted">
        Основа сторінки готова. Завантаження, фільтри за подіями та картки букетів
        підключимо наступним frontend-комітом.
      </p>
      <div className="placeholder-grid">
        {[1, 2, 3].map((item) => <div className="placeholder-card" key={item} />)}
      </div>
    </section>
  );
}
