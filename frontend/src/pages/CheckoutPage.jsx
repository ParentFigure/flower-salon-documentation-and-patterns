import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { createOrder, getDeliveryMethods, getSalons } from "../api/orders";
import { useAuth } from "../context/AuthContext";
import { clearCheckoutDraft, getCheckoutDraft } from "../utils/checkoutDraft";

function money(value) {
  const number = Number(value ?? 0);
  return Number.isFinite(number)
    ? new Intl.NumberFormat("uk-UA", {
        style: "currency",
        currency: "UAH",
        maximumFractionDigits: 2,
      }).format(number)
    : "—";
}

function apiErrorMessage(error) {
  const detail = error?.data?.detail;
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg).filter(Boolean).join(" · ");
  }
  if (typeof detail === "string") return detail;
  return error?.message || "Не вдалося створити замовлення.";
}

export default function CheckoutPage() {
  const { user } = useAuth();
  const [draft] = useState(() => getCheckoutDraft());
  const [deliveryMethods, setDeliveryMethods] = useState([]);
  const [salons, setSalons] = useState([]);
  const [deliveryMethodId, setDeliveryMethodId] = useState("");
  const [salonId, setSalonId] = useState("");
  const [address, setAddress] = useState("");
  const [quantity, setQuantity] = useState(() => Math.max(1, Number(draft?.quantity || 1)));
  const [loading, setLoading] = useState(Boolean(draft));
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [createdOrder, setCreatedOrder] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    if (!draft) return undefined;
    let active = true;

    async function loadOptions() {
      setLoading(true);
      setError("");
      try {
        const [methods, salonList] = await Promise.all([
          getDeliveryMethods(),
          getSalons(),
        ]);
        if (!active) return;
        setDeliveryMethods(methods);
        setSalons(salonList);

        const preferred = methods.find((item) => item.code === "pickup") || methods[0];
        if (preferred) setDeliveryMethodId(String(preferred.id));
        if (salonList[0]) setSalonId(String(salonList[0].id));
      } catch (err) {
        if (active) setError(apiErrorMessage(err));
      } finally {
        if (active) setLoading(false);
      }
    }

    loadOptions();
    return () => { active = false; };
  }, [draft, reloadKey]);

  const selectedMethod = useMemo(
    () => deliveryMethods.find((item) => item.id === Number(deliveryMethodId)) || null,
    [deliveryMethods, deliveryMethodId],
  );

  const itemName = draft?.kind === "catalog"
    ? draft?.bouquet?.name
    : draft?.preview?.name || draft?.custom_bouquet?.name;

  const unitPrice = Number(
    draft?.kind === "catalog"
      ? draft?.bouquet?.base_price
      : draft?.preview?.total_price,
  ) || 0;

  const estimatedItemsTotal = unitPrice * quantity;
  const estimatedDelivery = Number(selectedMethod?.base_price || 0);
  const estimatedTotal = estimatedItemsTotal + estimatedDelivery;

  async function handleSubmit(event) {
    event.preventDefault();
    setError("");

    if (!user?.client_id) {
      setError("Для оформлення замовлення потрібен профіль клієнта.");
      return;
    }
    if (!selectedMethod) {
      setError("Оберіть спосіб отримання замовлення.");
      return;
    }
    if (selectedMethod.code === "pickup" && !salonId) {
      setError("Оберіть салон для самовивозу.");
      return;
    }
    if (selectedMethod.requires_address && !address.trim()) {
      setError("Вкажіть адресу доставки.");
      return;
    }

    const item = draft.kind === "catalog"
      ? { bouquet_id: draft.bouquet.id, quantity }
      : { custom_bouquet: draft.custom_bouquet, quantity };

    const payload = {
      client_id: user.client_id,
      items: [item],
      delivery_type: selectedMethod.code,
      delivery_method_id: selectedMethod.id,
      pickup_salon_id: selectedMethod.code === "pickup" ? Number(salonId) : null,
      delivery_address: selectedMethod.requires_address ? address.trim() : null,
      discount_type: "none",
    };

    setSubmitting(true);
    try {
      const order = await createOrder(payload);
      setCreatedOrder(order);
      clearCheckoutDraft();
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!draft && !createdOrder) {
    return (
      <section className="page-section checkout-page">
        <div className="checkout-empty">
          <p className="eyebrow">Оформлення</p>
          <h1>Немає вибраного букета</h1>
          <p className="muted">Спочатку обери готовий букет у каталозі або створи власний.</p>
          <div className="checkout-empty__actions">
            <Link className="button" to="/catalog">До каталогу</Link>
            <Link className="button secondary" to="/builder">Створити свій</Link>
          </div>
        </div>
      </section>
    );
  }

  if (createdOrder) {
    return (
      <section className="page-section checkout-page">
        <div className="order-success-card">
          <div className="order-success-card__icon" aria-hidden="true">✓</div>
          <p className="eyebrow">Замовлення створено</p>
          <h1>Дякуємо! Замовлення #{createdOrder.id}</h1>
          <p className="muted">
            Воно вже збережене в системі та відображатиметься у персональному кабінеті.
          </p>
          <div className="order-success-total">
            <span>До сплати</span>
            <strong>{money(createdOrder.total_price)}</strong>
          </div>
          <div className="checkout-empty__actions">
            <Link className="button" to="/profile">Відкрити кабінет</Link>
            <Link className="button secondary" to="/catalog">Продовжити вибір</Link>
          </div>
        </div>
      </section>
    );
  }

  if (loading) {
    return (
      <section className="page-section checkout-page">
        <div className="checkout-header-skeleton" />
        <div className="checkout-layout">
          <div className="checkout-panel checkout-panel--skeleton" />
          <div className="checkout-panel checkout-panel--skeleton" />
        </div>
      </section>
    );
  }

  return (
    <section className="page-section checkout-page">
      <div className="checkout-hero">
        <div>
          <p className="eyebrow">Замовлення</p>
          <h1>Оформлення замовлення</h1>
          <p className="muted">Оберіть спосіб отримання. Доступні переваги програми лояльності застосуються автоматично.</p>
        </div>
      </div>

      {error && deliveryMethods.length === 0 ? (
        <div className="catalog-message error-panel" role="alert">
          <strong>Не вдалося завантажити способи доставки</strong>
          <span>{error}</span>
          <button className="button small" type="button" onClick={() => setReloadKey((value) => value + 1)}>
            Спробувати ще раз
          </button>
        </div>
      ) : (
        <form className="checkout-layout" onSubmit={handleSubmit}>
          <div className="checkout-main">
            <section className="checkout-panel">
              <div className="checkout-section-heading">
                <span className="builder-step">01</span>
                <div>
                  <h2>Твій букет</h2>
                  <p className="muted">{draft.kind === "custom" ? "Авторська композиція" : "Готовий букет з каталогу"}</p>
                </div>
              </div>

              <div className="checkout-product">
                <div className="checkout-product__visual" aria-hidden="true">🌷</div>
                <div className="checkout-product__info">
                  <strong>{itemName}</strong>
                  <span>{money(unitPrice)} / букет</span>
                </div>
                <label className="checkout-quantity">
                  <span>Кількість</span>
                  <input
                    type="number"
                    min="1"
                    max="20"
                    value={quantity}
                    onChange={(event) => setQuantity(Math.min(20, Math.max(1, Number(event.target.value) || 1)))}
                  />
                </label>
              </div>
            </section>

            <section className="checkout-panel">
              <div className="checkout-section-heading">
                <span className="builder-step">02</span>
                <div>
                  <h2>Спосіб отримання</h2>
                  <p className="muted">Вартість залежить від обраного способу отримання.</p>
                </div>
              </div>

              <div className="delivery-choice-grid">
                {deliveryMethods.map((method) => (
                  <label className={`delivery-choice ${Number(deliveryMethodId) === method.id ? "selected" : ""}`} key={method.id}>
                    <input
                      type="radio"
                      name="delivery-method"
                      checked={Number(deliveryMethodId) === method.id}
                      onChange={() => {
                        setDeliveryMethodId(String(method.id));
                        setError("");
                      }}
                    />
                    <span>
                      <strong>{method.name}</strong>
                      <small>{Number(method.base_price) === 0 ? "Безкоштовно" : money(method.base_price)}</small>
                      {method.description && <em>{method.description}</em>}
                    </span>
                  </label>
                ))}
              </div>

              {selectedMethod?.code === "pickup" && (
                <label className="checkout-field">
                  <span>Салон для самовивозу</span>
                  <select value={salonId} onChange={(event) => setSalonId(event.target.value)} required>
                    <option value="">Оберіть салон</option>
                    {salons.map((salon) => (
                      <option value={salon.id} key={salon.id}>{salon.name} — {salon.address}</option>
                    ))}
                  </select>
                </label>
              )}

              {selectedMethod?.requires_address && (
                <label className="checkout-field">
                  <span>Адреса доставки</span>
                  <input
                    type="text"
                    maxLength="255"
                    value={address}
                    onChange={(event) => setAddress(event.target.value)}
                    placeholder="м. Львів, вул. ..., буд. ..."
                    required
                  />
                </label>
              )}
            </section>
          </div>

          <aside className="checkout-summary">
            <div className="checkout-summary-card">
              <p className="eyebrow">Підсумок</p>
              <h2>{itemName}</h2>
              <div className="checkout-price-lines">
                <div><span>Букети × {quantity}</span><strong>{money(estimatedItemsTotal)}</strong></div>
                <div><span>{selectedMethod?.name || "Доставка"}</span><strong>{money(estimatedDelivery)}</strong></div>
              </div>
              <div className="checkout-total">
                <span>Орієнтовно</span>
                <strong>{money(estimatedTotal)}</strong>
              </div>
              <p className="checkout-note">
                Остаточна сума врахує доступні знижки та умови обраної доставки.
              </p>
              {error && <p className="form-alert" role="alert">{error}</p>}
              <button className="button checkout-submit" type="submit" disabled={submitting || !selectedMethod}>
                {submitting ? "Створюємо замовлення…" : "Підтвердити замовлення"}
              </button>
            </div>
          </aside>
        </form>
      )}
    </section>
  );
}
