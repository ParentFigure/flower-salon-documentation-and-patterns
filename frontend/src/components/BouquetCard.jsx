function formatPrice(value) {
  const amount = Number(value);
  if (!Number.isFinite(amount)) return value;
  return new Intl.NumberFormat("uk-UA", {
    style: "currency",
    currency: "UAH",
    maximumFractionDigits: 2,
  }).format(amount);
}

export default function BouquetCard({ bouquet }) {
  return (
    <article className="bouquet-card">
      <div className="bouquet-card__visual" aria-hidden="true">
        <span>🌷</span>
        <span>🌿</span>
      </div>

      <div className="bouquet-card__body">
        <div className="bouquet-card__heading">
          <div>
            <p className="bouquet-card__type">
              {bouquet.is_custom ? "Авторський букет" : "Букет з каталогу"}
            </p>
            <h2>{bouquet.name}</h2>
          </div>
          <strong className="bouquet-card__price">
            {formatPrice(bouquet.base_price)}
          </strong>
        </div>

        {bouquet.description && (
          <p className="bouquet-card__description">{bouquet.description}</p>
        )}

        {bouquet.occasions?.length > 0 && (
          <div className="tag-list" aria-label="Події">
            {bouquet.occasions.map((occasion) => (
              <span className="tag" key={occasion.id}>{occasion.name}</span>
            ))}
          </div>
        )}

        <details className="bouquet-details">
          <summary>Склад букета</summary>
          {bouquet.composition?.length > 0 ? (
            <ul className="composition-list">
              {bouquet.composition.map((item) => (
                <li key={item.flower_id}>
                  <span>{item.flower_name}</span>
                  <strong>× {item.quantity}</strong>
                </li>
              ))}
            </ul>
          ) : (
            <p className="muted bouquet-card__empty">Склад не вказано.</p>
          )}
        </details>
      </div>
    </article>
  );
}
