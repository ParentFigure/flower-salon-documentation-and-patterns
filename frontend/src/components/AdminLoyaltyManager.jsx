import { useMemo, useState } from "react";
import {
  accrueAdminBonus,
  getAdminLoyaltyCard,
  issueAdminLoyaltyCard,
  spendAdminBonus,
  updateAdminLoyaltyCard,
} from "../api/admin";

const CARD_LABELS = {
  gold: "Gold",
  bonus: "Бонусна",
  social: "Соціальна",
};

export default function AdminLoyaltyManager({ orders }) {
  const knownClientIds = useMemo(
    () => [...new Set(orders.map((order) => order.client_id))].sort((a, b) => a - b),
    [orders]
  );
  const [clientId, setClientId] = useState(knownClientIds[0] || "");
  const [cardType, setCardType] = useState("bonus");
  const [isActive, setIsActive] = useState(true);
  const [amount, setAmount] = useState("50");
  const [card, setCard] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  async function loadCard() {
    const id = Number(clientId);
    if (!id) return;
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await getAdminLoyaltyCard(id);
      setCard(data);
      setCardType(data.card_type);
      setIsActive(data.is_active);
    } catch (err) {
      setCard(null);
      setError(err?.message || "Картку не знайдено.");
    } finally {
      setBusy(false);
    }
  }

  async function issueCard() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await issueAdminLoyaltyCard({ client_id: Number(clientId), card_type: cardType });
      setCard(data);
      setIsActive(data.is_active);
      setMessage("Картку видано.");
    } catch (err) {
      setError(err?.message || "Не вдалося видати картку.");
    } finally {
      setBusy(false);
    }
  }

  async function saveCard() {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const data = await updateAdminLoyaltyCard(Number(clientId), { card_type: cardType, is_active: isActive });
      setCard(data);
      setMessage("Параметри картки оновлено.");
    } catch (err) {
      setError(err?.message || "Не вдалося оновити картку.");
    } finally {
      setBusy(false);
    }
  }

  async function changeBonus(direction) {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      const value = Number(amount);
      const data = direction === "add"
        ? await accrueAdminBonus(Number(clientId), value)
        : await spendAdminBonus(Number(clientId), value);
      setCard(data);
      setMessage(direction === "add" ? "Бонуси нараховано." : "Бонуси списано.");
    } catch (err) {
      setError(err?.message || "Не вдалося змінити бонусний баланс.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-split">
      <div className="admin-form">
        <div className="admin-section-heading">
          <div>
            <p className="admin-kicker">Loyalty</p>
            <h3>Картка клієнта</h3>
          </div>
        </div>

        <label>
          ID клієнта
          <input
            type="number"
            min="1"
            list="known-client-ids"
            value={clientId}
            onChange={(event) => setClientId(event.target.value)}
          />
          <datalist id="known-client-ids">
            {knownClientIds.map((id) => <option value={id} key={id} />)}
          </datalist>
        </label>

        <label>
          Тип картки
          <select value={cardType} onChange={(event) => setCardType(event.target.value)}>
            <option value="bonus">Бонусна</option>
            <option value="gold">Gold</option>
            <option value="social">Соціальна</option>
          </select>
        </label>

        <label className="admin-inline-check">
          <input type="checkbox" checked={isActive} onChange={(event) => setIsActive(event.target.checked)} />
          <span>Картка активна</span>
        </label>

        <div className="admin-actions admin-actions--flush">
          <button className="button ghost small" type="button" disabled={busy || !clientId} onClick={loadCard}>Завантажити</button>
          {!card ? (
            <button className="button small" type="button" disabled={busy || !clientId} onClick={issueCard}>Видати картку</button>
          ) : (
            <button className="button small" type="button" disabled={busy} onClick={saveCard}>Зберегти картку</button>
          )}
        </div>

        <label>
          Бонуси, грн
          <input type="number" min="0.01" step="0.01" value={amount} onChange={(event) => setAmount(event.target.value)} />
        </label>
        <div className="admin-actions admin-actions--flush">
          <button className="button ghost small" type="button" disabled={busy || !card} onClick={() => changeBonus("add")}>Нарахувати</button>
          <button className="button ghost small" type="button" disabled={busy || !card} onClick={() => changeBonus("spend")}>Списати</button>
        </div>

        {message && <p className="profile-success">{message}</p>}
        {error && <p className="form-alert">{error}</p>}
      </div>

      <div className="admin-simple-list">
        {card ? (
          <article className="admin-simple-card admin-loyalty-card">
            <div>
              <p className="admin-kicker">Клієнт #{card.client_id}</p>
              <h3>{CARD_LABELS[card.card_type] || card.card_type}</h3>
              <p className="muted">
                Баланс: {Number(card.bonus_balance).toFixed(2)} грн · знижка {card.discount_percent}%
                {card.free_delivery ? " · безкоштовна стандартна доставка" : ""}
              </p>
              <p className="muted">Статус: {card.is_active ? "активна" : "неактивна"}</p>
            </div>
          </article>
        ) : (
          <div className="admin-empty">Вкажи ID клієнта й завантаж або видай loyalty-картку.</div>
        )}
      </div>
    </div>
  );
}
