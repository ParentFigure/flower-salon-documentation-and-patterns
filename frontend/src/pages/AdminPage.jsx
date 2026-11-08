import { useCallback, useEffect, useMemo, useState } from "react";
import {
  createAdminBouquet,
  createAdminFlower,
  deleteAdminBouquet,
  deleteAdminFlower,
  getAdminBouquets,
  getAdminFlowers,
  getAdminOccasions,
  getAdminOrders,
  updateAdminBouquet,
  updateAdminFlower,
  updateAdminOrderStatus,
} from "../api/admin";

const ORDER_ACTIONS = {
  created: [
    { status: "confirmed", label: "Підтвердити" },
    { status: "cancelled", label: "Скасувати", danger: true },
  ],
  confirmed: [
    { status: "preparing", label: "Почати готувати" },
    { status: "cancelled", label: "Скасувати", danger: true },
  ],
  preparing: [{ status: "ready", label: "Готове" }],
  ready: [{ status: "delivering", label: "Передати в доставку" }],
  delivering: [{ status: "completed", label: "Завершити" }],
  completed: [],
  cancelled: [],
};

const STATUS_LABELS = {
  created: "Створено",
  confirmed: "Підтверджено",
  preparing: "Готується",
  ready: "Готове",
  delivering: "Доставляється",
  completed: "Завершено",
  cancelled: "Скасовано",
};

const EMPTY_FLOWER = { name: "", unit_price: "", stock_qty: 0 };
const EMPTY_BOUQUET = {
  name: "",
  description: "",
  base_price: "",
  occasion_ids: [],
  composition: {},
};

function money(value) {
  return `${Number(value || 0).toFixed(2)} грн`;
}

function displayError(error) {
  if (typeof error?.message === "string") return error.message;
  return "Не вдалося виконати операцію.";
}

function AdminOrders({ orders, onStatusChange, busyId }) {
  if (!orders.length) {
    return <div className="admin-empty">Замовлень поки немає.</div>;
  }

  return (
    <div className="admin-order-list">
      {orders.map((order) => (
        <article className="admin-order-card" key={order.id}>
          <div className="admin-order-card__top">
            <div>
              <p className="admin-kicker">Замовлення #{order.id}</p>
              <h3>Клієнт #{order.client_id}</h3>
              <p className="muted">
                {new Date(order.created_at).toLocaleString("uk-UA")} · {order.delivery_type}
              </p>
            </div>
            <div className="admin-order-meta">
              <span className={`status-badge status-${order.status}`}>
                {STATUS_LABELS[order.status] || order.status}
              </span>
              <strong>{money(order.total_price)}</strong>
            </div>
          </div>

          <div className="admin-order-items">
            {order.items.map((item) => (
              <div key={item.id}>
                <span>{item.item_name || `Букет #${item.bouquet_id}`}</span>
                <strong>{item.quantity} × {money(item.unit_price)}</strong>
              </div>
            ))}
          </div>

          <div className="admin-order-details">
            <span>Знижка: {money(order.discount_amount)}</span>
            <span>Доставка: {money(order.delivery_cost)}</span>
            {order.delivery_address && <span>Адреса: {order.delivery_address}</span>}
            {order.pickup_salon_id && <span>Салон #{order.pickup_salon_id}</span>}
          </div>

          {!!ORDER_ACTIONS[order.status]?.length && (
            <div className="admin-actions">
              {ORDER_ACTIONS[order.status].map((action) => (
                <button
                  key={action.status}
                  type="button"
                  className={action.danger ? "button danger small" : "button small"}
                  disabled={busyId === order.id}
                  onClick={() => onStatusChange(order.id, action.status)}
                >
                  {busyId === order.id ? "Збереження..." : action.label}
                </button>
              ))}
            </div>
          )}
        </article>
      ))}
    </div>
  );
}

function FlowerManager({ flowers, onRefresh }) {
  const [form, setForm] = useState(EMPTY_FLOWER);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function startEdit(flower) {
    setEditingId(flower.id);
    setForm({
      name: flower.name,
      unit_price: String(flower.unit_price),
      stock_qty: flower.stock_qty,
    });
    setError("");
  }

  function reset() {
    setEditingId(null);
    setForm(EMPTY_FLOWER);
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const payload = {
      name: form.name.trim(),
      unit_price: Number(form.unit_price),
      stock_qty: Number(form.stock_qty),
    };
    try {
      if (editingId) await updateAdminFlower(editingId, payload);
      else await createAdminFlower(payload);
      reset();
      await onRefresh();
    } catch (err) {
      setError(displayError(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(flower) {
    if (!window.confirm(`Видалити квітку «${flower.name}»?`)) return;
    setError("");
    try {
      await deleteAdminFlower(flower.id);
      if (editingId === flower.id) reset();
      await onRefresh();
    } catch (err) {
      setError(displayError(err));
    }
  }

  return (
    <div className="admin-split">
      <form className="admin-form" onSubmit={submit}>
        <div className="admin-section-heading">
          <div>
            <p className="admin-kicker">{editingId ? "Редагування" : "Нова позиція"}</p>
            <h3>{editingId ? "Змінити квітку" : "Додати квітку"}</h3>
          </div>
          {editingId && <button className="text-button" type="button" onClick={reset}>Скасувати</button>}
        </div>
        <label>
          Назва
          <input required minLength="2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
        </label>
        <div className="admin-form-grid">
          <label>
            Ціна, грн
            <input required min="0.01" step="0.01" type="number" value={form.unit_price} onChange={(e) => setForm({ ...form, unit_price: e.target.value })} />
          </label>
          <label>
            Залишок
            <input required min="0" step="1" type="number" value={form.stock_qty} onChange={(e) => setForm({ ...form, stock_qty: e.target.value })} />
          </label>
        </div>
        {error && <p className="form-alert">{error}</p>}
        <button className="button" disabled={busy} type="submit">{busy ? "Збереження..." : editingId ? "Зберегти" : "Додати квітку"}</button>
      </form>

      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead><tr><th>Квітка</th><th>Ціна</th><th>Залишок</th><th></th></tr></thead>
          <tbody>
            {flowers.map((flower) => (
              <tr key={flower.id}>
                <td><strong>{flower.name}</strong><small>#{flower.id}</small></td>
                <td>{money(flower.unit_price)}</td>
                <td>{flower.stock_qty}</td>
                <td className="admin-row-actions">
                  <button type="button" className="text-button" onClick={() => startEdit(flower)}>Редагувати</button>
                  <button type="button" className="text-button danger-text" onClick={() => remove(flower)}>Видалити</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BouquetManager({ bouquets, flowers, occasions, onRefresh }) {
  const [form, setForm] = useState(EMPTY_BOUQUET);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    setEditingId(null);
    setForm(EMPTY_BOUQUET);
    setError("");
  }

  function startEdit(bouquet) {
    const composition = {};
    bouquet.composition.forEach((item) => { composition[item.flower_id] = item.quantity; });
    setEditingId(bouquet.id);
    setForm({
      name: bouquet.name,
      description: bouquet.description || "",
      base_price: String(bouquet.base_price),
      occasion_ids: bouquet.occasions.map((occasion) => occasion.id),
      composition,
    });
    setError("");
  }

  function toggleOccasion(id) {
    setForm((current) => ({
      ...current,
      occasion_ids: current.occasion_ids.includes(id)
        ? current.occasion_ids.filter((item) => item !== id)
        : [...current.occasion_ids, id],
    }));
  }

  function setFlowerQuantity(id, value) {
    const quantity = Math.max(0, Number(value) || 0);
    setForm((current) => ({
      ...current,
      composition: { ...current.composition, [id]: quantity },
    }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const payload = {
      name: form.name.trim(),
      description: form.description.trim() || null,
      base_price: Number(form.base_price),
      is_custom: false,
      occasion_ids: form.occasion_ids,
      composition: Object.entries(form.composition)
        .filter(([, quantity]) => Number(quantity) > 0)
        .map(([flowerId, quantity]) => ({ flower_id: Number(flowerId), quantity: Number(quantity) })),
    };
    try {
      if (editingId) await updateAdminBouquet(editingId, payload);
      else await createAdminBouquet(payload);
      reset();
      await onRefresh();
    } catch (err) {
      setError(displayError(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(bouquet) {
    if (!window.confirm(`Видалити букет «${bouquet.name}»?`)) return;
    setError("");
    try {
      await deleteAdminBouquet(bouquet.id);
      if (editingId === bouquet.id) reset();
      await onRefresh();
    } catch (err) {
      setError(displayError(err));
    }
  }

  return (
    <div className="admin-bouquet-layout">
      <form className="admin-form admin-bouquet-form" onSubmit={submit}>
        <div className="admin-section-heading">
          <div>
            <p className="admin-kicker">{editingId ? "Редагування" : "Каталог"}</p>
            <h3>{editingId ? "Змінити букет" : "Новий готовий букет"}</h3>
          </div>
          {editingId && <button className="text-button" type="button" onClick={reset}>Скасувати</button>}
        </div>

        <label>Назва<input required minLength="2" value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></label>
        <label>Опис<textarea rows="3" value={form.description} onChange={(e) => setForm({ ...form, description: e.target.value })} /></label>
        <label>Ціна букета, грн<input required min="0.01" step="0.01" type="number" value={form.base_price} onChange={(e) => setForm({ ...form, base_price: e.target.value })} /></label>

        <fieldset className="admin-fieldset">
          <legend>Події</legend>
          <div className="admin-chip-grid">
            {occasions.map((occasion) => (
              <label className={form.occasion_ids.includes(occasion.id) ? "admin-check-chip selected" : "admin-check-chip"} key={occasion.id}>
                <input type="checkbox" checked={form.occasion_ids.includes(occasion.id)} onChange={() => toggleOccasion(occasion.id)} />
                {occasion.name}
              </label>
            ))}
          </div>
        </fieldset>

        <fieldset className="admin-fieldset">
          <legend>Склад</legend>
          <div className="admin-composition-grid">
            {flowers.map((flower) => (
              <label key={flower.id}>
                <span>{flower.name}<small>залишок {flower.stock_qty}</small></span>
                <input min="0" max="999" step="1" type="number" value={form.composition[flower.id] || 0} onChange={(e) => setFlowerQuantity(flower.id, e.target.value)} />
              </label>
            ))}
          </div>
        </fieldset>

        {error && <p className="form-alert">{error}</p>}
        <button className="button" disabled={busy} type="submit">{busy ? "Збереження..." : editingId ? "Зберегти букет" : "Додати букет"}</button>
      </form>

      <div className="admin-bouquet-list">
        {bouquets.map((bouquet) => (
          <article className="admin-bouquet-card" key={bouquet.id}>
            <div>
              <p className="admin-kicker">Букет #{bouquet.id}</p>
              <h3>{bouquet.name}</h3>
              <p className="muted">{bouquet.description || "Без опису"}</p>
            </div>
            <strong className="admin-bouquet-price">{money(bouquet.base_price)}</strong>
            <div className="tag-list">
              {bouquet.occasions.map((occasion) => <span className="tag" key={occasion.id}>{occasion.name}</span>)}
            </div>
            <p className="admin-composition-summary">
              {bouquet.composition.length
                ? bouquet.composition.map((item) => `${item.flower_name} × ${item.quantity}`).join(" · ")
                : "Склад не задано"}
            </p>
            <div className="admin-actions">
              <button type="button" className="button ghost small" onClick={() => startEdit(bouquet)}>Редагувати</button>
              <button type="button" className="button danger small" onClick={() => remove(bouquet)}>Видалити</button>
            </div>
          </article>
        ))}
      </div>
    </div>
  );
}

export default function AdminPage() {
  const [activeTab, setActiveTab] = useState("orders");
  const [orders, setOrders] = useState([]);
  const [flowers, setFlowers] = useState([]);
  const [bouquets, setBouquets] = useState([]);
  const [occasions, setOccasions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busyOrderId, setBusyOrderId] = useState(null);

  const loadAll = useCallback(async () => {
    setError("");
    const [orderData, flowerData, bouquetData, occasionData] = await Promise.all([
      getAdminOrders(),
      getAdminFlowers(),
      getAdminBouquets(),
      getAdminOccasions(),
    ]);
    setOrders(orderData);
    setFlowers(flowerData);
    setBouquets(bouquetData);
    setOccasions(occasionData);
  }, []);

  useEffect(() => {
    setLoading(true);
    loadAll().catch((err) => setError(displayError(err))).finally(() => setLoading(false));
  }, [loadAll]);

  const stats = useMemo(() => ({
    activeOrders: orders.filter((order) => !["completed", "cancelled"].includes(order.status)).length,
    flowers: flowers.length,
    bouquets: bouquets.length,
  }), [orders, flowers, bouquets]);

  async function changeStatus(orderId, status) {
    setBusyOrderId(orderId);
    setError("");
    try {
      const updated = await updateAdminOrderStatus(orderId, status);
      setOrders((current) => current.map((order) => order.id === orderId ? updated : order));
    } catch (err) {
      setError(displayError(err));
    } finally {
      setBusyOrderId(null);
    }
  }

  if (loading) {
    return <div className="page-state">Завантаження адмін-панелі...</div>;
  }

  return (
    <section className="page-section admin-page">
      <div className="admin-hero">
        <div>
          <p className="eyebrow">Адмін-панель</p>
          <h1>Керування мережею</h1>
          <p className="muted">Каталог, запаси та життєвий цикл замовлень в одному місці.</p>
        </div>
        <div className="admin-stat-grid">
          <div><strong>{stats.activeOrders}</strong><span>активних замовлень</span></div>
          <div><strong>{stats.flowers}</strong><span>видів квітів</span></div>
          <div><strong>{stats.bouquets}</strong><span>готових букетів</span></div>
        </div>
      </div>

      {error && <div className="form-alert admin-global-alert">{error}</div>}

      <div className="admin-tabs" role="tablist" aria-label="Розділи адмін-панелі">
        <button className={activeTab === "orders" ? "active" : ""} onClick={() => setActiveTab("orders")} type="button">Замовлення <span>{orders.length}</span></button>
        <button className={activeTab === "flowers" ? "active" : ""} onClick={() => setActiveTab("flowers")} type="button">Квіти <span>{flowers.length}</span></button>
        <button className={activeTab === "bouquets" ? "active" : ""} onClick={() => setActiveTab("bouquets")} type="button">Букети <span>{bouquets.length}</span></button>
      </div>

      <div className="admin-panel">
        {activeTab === "orders" && <AdminOrders orders={orders} onStatusChange={changeStatus} busyId={busyOrderId} />}
        {activeTab === "flowers" && <FlowerManager flowers={flowers} onRefresh={loadAll} />}
        {activeTab === "bouquets" && <BouquetManager bouquets={bouquets} flowers={flowers} occasions={occasions} onRefresh={loadAll} />}
      </div>
    </section>
  );
}
