import { useEffect, useState } from "react";
import { getBouquets, getOccasions } from "../api/catalog";
import BouquetCard from "../components/BouquetCard";

export default function CatalogPage() {
  const [bouquets, setBouquets] = useState([]);
  const [occasions, setOccasions] = useState([]);
  const [selectedOccasion, setSelectedOccasion] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadOccasions() {
      try {
        const data = await getOccasions();
        if (active) setOccasions(data);
      } catch {
        if (active) setOccasions([]);
      }
    }

    loadOccasions();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;

    async function loadBouquets() {
      setLoading(true);
      setError("");
      try {
        const data = await getBouquets(selectedOccasion);
        if (active) setBouquets(data);
      } catch (err) {
        if (active) {
          setBouquets([]);
          setError(err?.message || "Не вдалося завантажити каталог.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadBouquets();
    return () => { active = false; };
  }, [selectedOccasion, reloadKey]);

  return (
    <section className="page-section catalog-page">
      <div className="catalog-hero">
        <div>
          <p className="eyebrow">Каталог</p>
          <h1>Букети для ваших моментів</h1>
          <p className="muted catalog-intro">
            Оберіть готову композицію або відфільтруйте букети за подією.
            Склад і ціна завантажуються напряму з FastAPI.
          </p>
        </div>
        <div className="catalog-count" aria-live="polite">
          <strong>{loading ? "…" : bouquets.length}</strong>
          <span>{bouquets.length === 1 ? "букет" : "букетів"}</span>
        </div>
      </div>

      <div className="occasion-filter" aria-label="Фільтр за подією">
        <button
          className={`filter-chip ${selectedOccasion === "" ? "active" : ""}`}
          type="button"
          onClick={() => setSelectedOccasion("")}
        >
          Усі
        </button>
        {occasions.map((occasion) => (
          <button
            className={`filter-chip ${selectedOccasion === occasion.slug ? "active" : ""}`}
            type="button"
            key={occasion.id}
            onClick={() => setSelectedOccasion(occasion.slug)}
          >
            {occasion.name}
          </button>
        ))}
      </div>

      {loading && (
        <div className="bouquet-grid" aria-label="Завантаження каталогу">
          {[1, 2, 3].map((item) => (
            <div className="catalog-skeleton" key={item} />
          ))}
        </div>
      )}

      {!loading && error && (
        <div className="catalog-message error-panel" role="alert">
          <strong>Не вдалося завантажити каталог</strong>
          <span>{error}</span>
          <button className="button small" type="button" onClick={() => setReloadKey((value) => value + 1)}>
            Спробувати ще раз
          </button>
        </div>
      )}

      {!loading && !error && bouquets.length === 0 && (
        <div className="catalog-message">
          <strong>Для цієї події поки немає букетів</strong>
          <span>Оберіть іншу категорію або перегляньте весь каталог.</span>
          {selectedOccasion && (
            <button className="button secondary small" type="button" onClick={() => setSelectedOccasion("")}>Показати всі</button>
          )}
        </div>
      )}

      {!loading && !error && bouquets.length > 0 && (
        <div className="bouquet-grid">
          {bouquets.map((bouquet) => (
            <BouquetCard bouquet={bouquet} key={bouquet.id} />
          ))}
        </div>
      )}
    </section>
  );
}
