import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { getProfile, updateProfile } from "../api/profile";
import {
  getClientNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "../api/notifications";

const STATUS_LABELS = {
  created: "Створено",
  confirmed: "Підтверджено",
  preparing: "Готується",
  ready: "Готове",
  delivering: "Доставляється",
  completed: "Завершено",
  cancelled: "Скасовано",
};


const NOTIFICATION_LABELS = {
  order_ready: "Замовлення готове",
  bonus_accrued: "Нараховано бонуси",
  new_arrival: "Новинка каталогу",
};

const CARD_LABELS = {
  gold: "Gold",
  bonus: "Бонусна",
  social: "Соціальна",
};

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

function dateTime(value) {
  if (!value) return "—";
  return new Intl.DateTimeFormat("uk-UA", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function OrderCard({ order }) {
  const itemSummary = order.items
    ?.map((item) => `${item.item_name || `Букет #${item.bouquet_id}`} × ${item.quantity}`)
    .join(", ");

  return (
    <article className="profile-order-card">
      <div className="profile-order-card__top">
        <div>
          <p className="profile-order-card__number">Замовлення #{order.id}</p>
          <p className="muted profile-order-card__date">{dateTime(order.created_at)}</p>
        </div>
        <span className={`order-status order-status--${order.status}`}>
          {STATUS_LABELS[order.status] || order.status}
        </span>
      </div>
      <p className="profile-order-card__items">{itemSummary || "Позиції не вказано"}</p>
      <div className="profile-order-card__bottom">
        <span className="muted">
          {order.delivery_type === "pickup" ? "Самовивіз" : "Доставка"}
        </span>
        <strong>{money(order.total_price)}</strong>
      </div>
    </article>
  );
}

export default function ProfilePage() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({ full_name: "", phone: "" });
  const [success, setSuccess] = useState("");
  const [reloadKey, setReloadKey] = useState(0);
  const [notifications, setNotifications] = useState([]);
  const [notificationsBusy, setNotificationsBusy] = useState(false);

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError("");
      try {
        const data = await getProfile();
        if (!active) return;
        setProfile(data);
        const notificationData = await getClientNotifications(data.client_id);
        if (!active) return;
        setNotifications(notificationData);
        setForm({
          full_name: data.full_name || "",
          phone: data.phone || "",
        });
      } catch (err) {
        if (active) setError(err?.message || "Не вдалося завантажити профіль.");
      } finally {
        if (active) setLoading(false);
      }
    }

    load();
    return () => {
      active = false;
    };
  }, [reloadKey]);

  const loyaltyTitle = useMemo(() => {
    if (!profile?.loyalty_card) return "Картки ще немає";
    return CARD_LABELS[profile.loyalty_card.card_type] || profile.loyalty_card.card_type;
  }, [profile]);

  async function handleSubmit(event) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setSuccess("");

    try {
      const updated = await updateProfile({
        full_name: form.full_name.trim(),
        phone: form.phone.trim() || null,
      });
      setProfile(updated);
      setForm({
        full_name: updated.full_name || "",
        phone: updated.phone || "",
      });
      setEditing(false);
      setSuccess("Профіль оновлено.");
    } catch (err) {
      setError(err?.message || "Не вдалося оновити профіль.");
    } finally {
      setSaving(false);
    }
  }

  async function markOneRead(notificationId) {
    setNotificationsBusy(true);
    setError("");
    try {
      const updated = await markNotificationRead(notificationId);
      setNotifications((current) =>
        current.map((item) => item.id === notificationId ? updated : item)
      );
      setProfile((current) => current ? {
        ...current,
        unread_notifications_count: Math.max(0, current.unread_notifications_count - 1),
      } : current);
    } catch (err) {
      setError(err?.message || "Не вдалося позначити повідомлення прочитаним.");
    } finally {
      setNotificationsBusy(false);
    }
  }

  async function markAllRead() {
    if (!profile) return;
    setNotificationsBusy(true);
    setError("");
    try {
      await markAllNotificationsRead(profile.client_id);
      setNotifications((current) => current.map((item) => ({ ...item, is_read: true })));
      setProfile((current) => current ? { ...current, unread_notifications_count: 0 } : current);
    } catch (err) {
      setError(err?.message || "Не вдалося позначити повідомлення прочитаними.");
    } finally {
      setNotificationsBusy(false);
    }
  }

  if (loading) {
    return (
      <section className="page-section profile-page">
        <div className="profile-header-skeleton" />
        <div className="profile-stat-grid">
          {[1, 2, 3].map((item) => <div className="profile-stat-skeleton" key={item} />)}
        </div>
      </section>
    );
  }

  if (error && !profile) {
    return (
      <section className="page-section profile-page">
        <div className="catalog-message error-panel" role="alert">
          <strong>Не вдалося завантажити кабінет</strong>
          <span>{error}</span>
          <button className="button small" type="button" onClick={() => setReloadKey((value) => value + 1)}>
            Спробувати ще раз
          </button>
        </div>
      </section>
    );
  }

  return (
    <section className="page-section profile-page">
      <div className="profile-hero">
        <div>
          <p className="eyebrow">Персональний кабінет</p>
          <h1>{profile.full_name}</h1>
          <p className="muted profile-email">{profile.email}</p>
        </div>
        <button
          className="button secondary"
          type="button"
          onClick={() => {
            setEditing((value) => !value);
            setSuccess("");
            setError("");
          }}
        >
          {editing ? "Закрити" : "Редагувати профіль"}
        </button>
      </div>

      <div className="profile-quick-actions" aria-label="Швидкі дії клієнта">
        <Link className="button" to="/catalog">Замовити готовий букет</Link>
        <Link className="button secondary" to="/builder">Створити свій букет</Link>
      </div>

      {success && <p className="profile-success" role="status">{success}</p>}
      {error && profile && <p className="form-alert" role="alert">{error}</p>}

      {editing && (
        <form className="profile-edit-card" onSubmit={handleSubmit}>
          <div className="profile-edit-grid">
            <label>
              Ім’я
              <input
                type="text"
                value={form.full_name}
                minLength={1}
                maxLength={120}
                required
                onChange={(event) => setForm((current) => ({ ...current, full_name: event.target.value }))}
              />
            </label>
            <label>
              Телефон
              <input
                type="tel"
                value={form.phone}
                maxLength={30}
                placeholder="+380..."
                onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              />
            </label>
          </div>
          <div className="profile-edit-actions">
            <button className="button" type="submit" disabled={saving}>
              {saving ? "Зберігаємо…" : "Зберегти"}
            </button>
            <button
              className="button ghost"
              type="button"
              disabled={saving}
              onClick={() => {
                setForm({ full_name: profile.full_name || "", phone: profile.phone || "" });
                setEditing(false);
              }}
            >
              Скасувати
            </button>
          </div>
        </form>
      )}

      <div className="profile-stat-grid">
        <article className="profile-stat-card profile-stat-card--loyalty">
          <span className="profile-stat-card__label">Картка клієнта</span>
          <strong>{loyaltyTitle}</strong>
          {profile.loyalty_card ? (
            <small>
              {Number(profile.loyalty_card.discount_percent) > 0
                ? `${profile.loyalty_card.discount_percent}% знижки`
                : "Накопичувальна програма"}
              {profile.loyalty_card.free_delivery ? " · безкоштовна доставка" : ""}
            </small>
          ) : (
            <small>Картку може видати адміністратор салону</small>
          )}
        </article>

        <article className="profile-stat-card">
          <span className="profile-stat-card__label">Бонусний баланс</span>
          <strong>{money(profile.bonus_balance)}</strong>
          <small>Доступно для наступних замовлень</small>
        </article>

        <article className="profile-stat-card">
          <span className="profile-stat-card__label">Замовлення</span>
          <strong>{profile.total_orders}</strong>
          <small>Усього в історії</small>
        </article>

        <article className="profile-stat-card">
          <span className="profile-stat-card__label">Нові повідомлення</span>
          <strong>{profile.unread_notifications_count}</strong>
          <small>{profile.unread_notifications_count ? "Є непрочитані" : "Усе прочитано"}</small>
        </article>
      </div>

      <div className="profile-content-grid">
        <div className="profile-panel profile-orders-panel">
          <div className="profile-panel__heading">
            <div>
              <p className="eyebrow">Історія</p>
              <h2>Останні замовлення</h2>
            </div>
            <span className="muted">Показуємо до 5 останніх</span>
          </div>

          {profile.recent_orders.length ? (
            <div className="profile-order-list">
              {profile.recent_orders.map((order) => <OrderCard key={order.id} order={order} />)}
            </div>
          ) : (
            <div className="profile-empty-state">
              <strong>Замовлень ще немає</strong>
              <span>Після першого оформлення воно з’явиться тут.</span>
            </div>
          )}
        </div>

        <div className="profile-panel profile-notifications-panel">
          <div className="profile-panel__heading">
            <div>
              <p className="eyebrow">Сповіщення</p>
              <h2>Повідомлення</h2>
            </div>
            {profile.unread_notifications_count > 0 && (
              <button
                className="text-button"
                type="button"
                disabled={notificationsBusy}
                onClick={markAllRead}
              >
                Прочитати всі
              </button>
            )}
          </div>

          {notifications.length ? (
            <div className="profile-notification-list">
              {notifications.map((notification) => (
                <article
                  className={notification.is_read ? "profile-notification is-read" : "profile-notification"}
                  key={notification.id}
                >
                  <div>
                    <strong>{NOTIFICATION_LABELS[notification.type] || "Повідомлення"}</strong>
                    <p>{notification.message}</p>
                    <small>{dateTime(notification.created_at)}</small>
                  </div>
                  {!notification.is_read && (
                    <button
                      type="button"
                      className="text-button"
                      disabled={notificationsBusy}
                      onClick={() => markOneRead(notification.id)}
                    >
                      Прочитано
                    </button>
                  )}
                </article>
              ))}
            </div>
          ) : (
            <div className="profile-empty-state profile-empty-state--compact">
              <strong>Повідомлень ще немає</strong>
              <span>Новинки, готові замовлення та бонуси з’являться тут.</span>
            </div>
          )}
        </div>

        <aside className="profile-panel profile-contact-panel">
          <p className="eyebrow">Контакти</p>
          <h2>Дані клієнта</h2>
          <dl className="profile-details">
            <div>
              <dt>Email</dt>
              <dd>{profile.email}</dd>
            </div>
            <div>
              <dt>Телефон</dt>
              <dd>{profile.phone || "Не вказано"}</dd>
            </div>
            <div>
              <dt>ID клієнта</dt>
              <dd>#{profile.client_id}</dd>
            </div>
          </dl>
        </aside>
      </div>
    </section>
  );
}
