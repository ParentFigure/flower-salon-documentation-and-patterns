import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  getBuilderOccasions,
  getFlowers,
  getPackagingOptions,
  previewCustomBouquet,
} from "../api/customBouquet";
import { saveCheckoutDraft } from "../utils/checkoutDraft";

const GREETING_CARD_ESTIMATE = 25;

function formatMoney(value) {
  return new Intl.NumberFormat("uk-UA", {
    style: "currency",
    currency: "UAH",
    maximumFractionDigits: 2,
  }).format(Number(value || 0));
}

function normalizeApiError(error) {
  if (Array.isArray(error?.data?.detail)) {
    return error.data.detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" · ");
  }
  return error?.message || "Не вдалося розрахувати букет.";
}

export default function CustomBouquetPage() {
  const navigate = useNavigate();
  const [flowers, setFlowers] = useState([]);
  const [packaging, setPackaging] = useState([]);
  const [occasions, setOccasions] = useState([]);
  const [name, setName] = useState("Мій авторський букет");
  const [quantities, setQuantities] = useState({});
  const [packagingId, setPackagingId] = useState("");
  const [occasionIds, setOccasionIds] = useState([]);
  const [greetingCardText, setGreetingCardText] = useState("");
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState("");
  const [preview, setPreview] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let active = true;

    async function loadBuilderData() {
      setLoading(true);
      setLoadError("");
      try {
        const [flowerData, packagingData, occasionData] = await Promise.all([
          getFlowers(),
          getPackagingOptions(),
          getBuilderOccasions(),
        ]);
        if (!active) return;
        setFlowers(flowerData);
        setPackaging(packagingData);
        setOccasions(occasionData);
      } catch (error) {
        if (active) {
          setLoadError(error?.message || "Не вдалося завантажити дані конструктора.");
        }
      } finally {
        if (active) setLoading(false);
      }
    }

    loadBuilderData();
    return () => { active = false; };
  }, [reloadKey]);

  const selectedFlowers = useMemo(
    () => flowers
      .map((flower) => ({ ...flower, quantity: Number(quantities[flower.id] || 0) }))
      .filter((flower) => flower.quantity > 0),
    [flowers, quantities],
  );

  const selectedPackaging = useMemo(
    () => packaging.find((item) => item.id === Number(packagingId)) || null,
    [packaging, packagingId],
  );

  const estimatedTotal = useMemo(() => {
    const flowersTotal = selectedFlowers.reduce(
      (sum, flower) => sum + Number(flower.unit_price) * flower.quantity,
      0,
    );
    const packagingTotal = selectedPackaging ? Number(selectedPackaging.price) : 0;
    const cardTotal = greetingCardText.trim() ? GREETING_CARD_ESTIMATE : 0;
    return flowersTotal + packagingTotal + cardTotal;
  }, [selectedFlowers, selectedPackaging, greetingCardText]);

  function invalidatePreview() {
    setPreview(null);
    setFormError("");
  }

  function updateFlowerQuantity(flower, nextValue) {
    const raw = Math.max(0, Number(nextValue) || 0);
    const quantity = Math.min(raw, flower.stock_qty);
    setQuantities((current) => ({ ...current, [flower.id]: quantity }));
    invalidatePreview();
  }

  function toggleOccasion(id) {
    setOccasionIds((current) => (
      current.includes(id)
        ? current.filter((item) => item !== id)
        : [...current, id]
    ));
    invalidatePreview();
  }

  function handleCheckout() {
    if (!preview) return;

    saveCheckoutDraft({
      kind: "custom",
      quantity: 1,
      custom_bouquet: {
        name: name.trim(),
        flowers: selectedFlowers.map((flower) => ({
          flower_id: flower.id,
          quantity: flower.quantity,
        })),
        packaging_id: packagingId ? Number(packagingId) : null,
        greeting_card_text: greetingCardText.trim() || null,
        occasion_ids: occasionIds,
      },
      preview: {
        name: preview.name,
        total_price: preview.total_price,
        packaging_name: preview.packaging_name || null,
      },
    });
    navigate("/checkout");
  }

  async function handlePreview(event) {
    event.preventDefault();
    setFormError("");
    setPreview(null);

    if (name.trim().length < 2) {
      setFormError("Назва букета повинна містити щонайменше 2 символи.");
      return;
    }
    if (selectedFlowers.length === 0) {
      setFormError("Оберіть хоча б одну квітку.");
      return;
    }

    const payload = {
      name: name.trim(),
      flowers: selectedFlowers.map((flower) => ({
        flower_id: flower.id,
        quantity: flower.quantity,
      })),
      packaging_id: packagingId ? Number(packagingId) : null,
      greeting_card_text: greetingCardText.trim() || null,
      occasion_ids: occasionIds,
    };

    setSubmitting(true);
    try {
      const data = await previewCustomBouquet(payload);
      setPreview(data);
    } catch (error) {
      setFormError(normalizeApiError(error));
    } finally {
      setSubmitting(false);
    }
  }

  if (loading) {
    return (
      <section className="page-section builder-page">
        <div className="builder-header-skeleton" />
        <div className="builder-layout">
          <div className="builder-panel builder-panel--skeleton" />
          <div className="builder-panel builder-panel--skeleton" />
        </div>
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="page-section builder-page">
        <div className="catalog-message error-panel" role="alert">
          <strong>Конструктор не завантажився</strong>
          <span>{loadError}</span>
          <button className="button small" type="button" onClick={() => setReloadKey((value) => value + 1)}>
            Спробувати ще раз
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="page-section builder-page">
      <div className="builder-hero">
        <div>
          <p className="eyebrow">Конструктор букета</p>
          <h1>Збери свій букет</h1>
          <p className="muted builder-intro">
            Оберіть квіти, упаковку та подію. Після перевірки буде показано остаточну вартість композиції.
          </p>
        </div>
        <div className="builder-price-badge">
          <span>Орієнтовно</span>
          <strong>{formatMoney(estimatedTotal)}</strong>
        </div>
      </div>

      <form className="builder-layout" onSubmit={handlePreview}>
        <div className="builder-main">
          <section className="builder-panel">
            <div className="builder-section-heading">
              <div>
                <span className="builder-step">01</span>
                <h2>Назва букета</h2>
              </div>
            </div>
            <label className="builder-field">
              <span>Як назвемо композицію?</span>
              <input
                maxLength="120"
                minLength="2"
                value={name}
                onChange={(event) => { setName(event.target.value); invalidatePreview(); }}
              />
            </label>
          </section>

          <section className="builder-panel">
            <div className="builder-section-heading">
              <div>
                <span className="builder-step">02</span>
                <h2>Квіти</h2>
              </div>
              <span className="builder-selection-count">Обрано: {selectedFlowers.length}</span>
            </div>

            {flowers.length === 0 ? (
              <p className="muted">У каталозі ще немає квітів. Їх може додати адміністратор.</p>
            ) : (
              <div className="flower-choice-grid">
                {flowers.map((flower) => {
                  const quantity = Number(quantities[flower.id] || 0);
                  const selected = quantity > 0;
                  const unavailable = flower.stock_qty <= 0;
                  return (
                    <article className={`flower-choice ${selected ? "selected" : ""} ${unavailable ? "disabled" : ""}`} key={flower.id}>
                      <div className="flower-choice__icon" aria-hidden="true">🌷</div>
                      <div className="flower-choice__info">
                        <strong>{flower.name}</strong>
                        <span>{formatMoney(flower.unit_price)} / шт.</span>
                        <small>{unavailable ? "Немає в наявності" : `В наявності: ${flower.stock_qty}`}</small>
                      </div>
                      <div className="quantity-control" aria-label={`Кількість ${flower.name}`}>
                        <button
                          type="button"
                          disabled={!selected}
                          onClick={() => updateFlowerQuantity(flower, quantity - 1)}
                          aria-label={`Зменшити кількість ${flower.name}`}
                        >−</button>
                        <input
                          aria-label={`Кількість ${flower.name}`}
                          disabled={unavailable}
                          min="0"
                          max={flower.stock_qty}
                          type="number"
                          value={quantity}
                          onChange={(event) => updateFlowerQuantity(flower, event.target.value)}
                        />
                        <button
                          type="button"
                          disabled={unavailable || quantity >= flower.stock_qty}
                          onClick={() => updateFlowerQuantity(flower, quantity + 1)}
                          aria-label={`Збільшити кількість ${flower.name}`}
                        >+</button>
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </section>

          <section className="builder-panel">
            <div className="builder-section-heading">
              <div>
                <span className="builder-step">03</span>
                <h2>Упаковка</h2>
              </div>
            </div>
            <div className="builder-option-grid">
              <label className={`builder-option ${packagingId === "" ? "selected" : ""}`}>
                <input
                  checked={packagingId === ""}
                  name="packaging"
                  type="radio"
                  value=""
                  onChange={() => { setPackagingId(""); invalidatePreview(); }}
                />
                <span><strong>Без упаковки</strong><small>+ {formatMoney(0)}</small></span>
              </label>
              {packaging.map((item) => (
                <label className={`builder-option ${Number(packagingId) === item.id ? "selected" : ""}`} key={item.id}>
                  <input
                    checked={Number(packagingId) === item.id}
                    name="packaging"
                    type="radio"
                    value={item.id}
                    onChange={() => { setPackagingId(String(item.id)); invalidatePreview(); }}
                  />
                  <span>
                    <strong>{item.name}</strong>
                    <small>+ {formatMoney(item.price)}</small>
                    {item.description && <em>{item.description}</em>}
                  </span>
                </label>
              ))}
            </div>
          </section>

          <section className="builder-panel">
            <div className="builder-section-heading">
              <div>
                <span className="builder-step">04</span>
                <h2>Подія</h2>
              </div>
              <span className="builder-selection-count">Можна обрати кілька</span>
            </div>
            <div className="occasion-filter builder-occasion-filter">
              {occasions.map((occasion) => (
                <button
                  className={`filter-chip ${occasionIds.includes(occasion.id) ? "active" : ""}`}
                  key={occasion.id}
                  type="button"
                  onClick={() => toggleOccasion(occasion.id)}
                >
                  {occasion.name}
                </button>
              ))}
              {occasions.length === 0 && <span className="muted">Події ще не додані.</span>}
            </div>
          </section>

          <section className="builder-panel">
            <div className="builder-section-heading">
              <div>
                <span className="builder-step">05</span>
                <h2>Листівка</h2>
              </div>
              <span className="builder-selection-count">до 250 символів</span>
            </div>
            <label className="builder-field">
              <span>Текст побажання <small className="optional-label">необов’язково</small></span>
              <textarea
                maxLength="250"
                placeholder="Наприклад: З днем народження!"
                rows="4"
                value={greetingCardText}
                onChange={(event) => { setGreetingCardText(event.target.value); invalidatePreview(); }}
              />
              <small className="builder-character-count">{greetingCardText.length}/250</small>
            </label>
          </section>
        </div>

        <aside className="builder-summary">
          <div className="builder-summary-card">
            <p className="eyebrow">Твоя композиція</p>
            <h2>{name.trim() || "Авторський букет"}</h2>

            <div className="builder-summary-list">
              {selectedFlowers.length === 0 ? (
                <p className="muted">Додай квіти, щоб сформувати букет.</p>
              ) : selectedFlowers.map((flower) => (
                <div key={flower.id}>
                  <span>{flower.name} × {flower.quantity}</span>
                  <strong>{formatMoney(Number(flower.unit_price) * flower.quantity)}</strong>
                </div>
              ))}
              {selectedPackaging && (
                <div><span>{selectedPackaging.name}</span><strong>{formatMoney(selectedPackaging.price)}</strong></div>
              )}
              {greetingCardText.trim() && (
                <div><span>Листівка</span><strong>{formatMoney(GREETING_CARD_ESTIMATE)}</strong></div>
              )}
            </div>

            <div className="builder-summary-total">
              <span>{preview ? "Остаточна сума" : "Орієнтовна сума"}</span>
              <strong>{formatMoney(preview?.total_price ?? estimatedTotal)}</strong>
            </div>

            {formError && <p className="form-alert" role="alert">{formError}</p>}

            {preview && (
              <div className="builder-preview-success" role="status">
                <strong>✓ Букет перевірено</strong>
                <span>
                  Композиція доступна для замовлення. Остаточну вартість розраховано.
                </span>
                {preview.packaging_name && <small>Упаковка: {preview.packaging_name}</small>}
                {preview.greeting_card_text && <small>Листівка: {formatMoney(preview.greeting_card_price)}</small>}
              </div>
            )}

            <button className="button builder-submit" disabled={submitting || selectedFlowers.length === 0} type="submit">
              {submitting ? "Перевіряємо…" : "Перевірити й розрахувати"}
            </button>
            {preview && (
              <button className="button secondary builder-checkout" type="button" onClick={handleCheckout}>
                Перейти до оформлення
              </button>
            )}
            <p className="builder-server-note">
              До підтвердження вартість композиції є орієнтовною.
            </p>
          </div>
        </aside>
      </form>
    </section>
  );
}
