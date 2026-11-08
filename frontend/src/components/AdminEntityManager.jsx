import { useMemo, useState } from "react";

function buildEmpty(fields) {
  return Object.fromEntries(
    fields.map((field) => [
      field.key,
      field.defaultValue ?? (field.type === "checkbox" ? false : ""),
    ])
  );
}

function normalizePayload(form, fields) {
  const payload = {};
  fields.forEach((field) => {
    const raw = form[field.key];
    if (field.type === "number") {
      payload[field.key] = Number(raw);
    } else if (field.type === "checkbox") {
      payload[field.key] = Boolean(raw);
    } else if (field.nullable && typeof raw === "string" && !raw.trim()) {
      payload[field.key] = null;
    } else {
      payload[field.key] = typeof raw === "string" ? raw.trim() : raw;
    }
  });
  return payload;
}

export default function AdminEntityManager({
  title,
  singular,
  items,
  fields,
  createItem,
  updateItem,
  deleteItem,
  onRefresh,
  renderSummary,
}) {
  const emptyForm = useMemo(() => buildEmpty(fields), [fields]);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function reset() {
    setEditingId(null);
    setForm(emptyForm);
    setError("");
  }

  function edit(item) {
    const next = {};
    fields.forEach((field) => {
      next[field.key] = item[field.key] ?? (field.type === "checkbox" ? false : "");
    });
    setEditingId(item.id);
    setForm(next);
    setError("");
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const payload = normalizePayload(form, fields);
      if (editingId) await updateItem(editingId, payload);
      else await createItem(payload);
      reset();
      await onRefresh();
    } catch (err) {
      setError(err?.message || "Не вдалося зберегти зміни.");
    } finally {
      setBusy(false);
    }
  }

  async function remove(item) {
    if (!window.confirm(`Видалити «${item.name || item.code || `#${item.id}`}»?`)) return;
    setBusy(true);
    setError("");
    try {
      await deleteItem(item.id);
      if (editingId === item.id) reset();
      await onRefresh();
    } catch (err) {
      setError(err?.message || "Не вдалося видалити запис.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="admin-split">
      <form className="admin-form" onSubmit={submit}>
        <div className="admin-section-heading">
          <div>
            <p className="admin-kicker">{editingId ? "Редагування" : "Новий запис"}</p>
            <h3>{editingId ? `Змінити: ${singular}` : `Додати: ${singular}`}</h3>
          </div>
          {editingId && <button className="text-button" type="button" onClick={reset}>Скасувати</button>}
        </div>

        {fields.map((field) => {
          if (field.type === "checkbox") {
            return (
              <label className="admin-inline-check" key={field.key}>
                <input
                  type="checkbox"
                  checked={Boolean(form[field.key])}
                  onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.checked }))}
                />
                <span>{field.label}</span>
              </label>
            );
          }

          if (field.type === "textarea") {
            return (
              <label key={field.key}>
                {field.label}
                <textarea
                  rows={field.rows || 3}
                  value={form[field.key] ?? ""}
                  required={field.required}
                  maxLength={field.maxLength}
                  onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
                />
              </label>
            );
          }

          return (
            <label key={field.key}>
              {field.label}
              <input
                type={field.type || "text"}
                value={form[field.key] ?? ""}
                required={field.required}
                min={field.min}
                max={field.max}
                step={field.step}
                minLength={field.minLength}
                maxLength={field.maxLength}
                pattern={field.pattern}
                onChange={(event) => setForm((current) => ({ ...current, [field.key]: event.target.value }))}
              />
            </label>
          );
        })}

        {error && <p className="form-alert">{error}</p>}
        <button className="button" type="submit" disabled={busy}>
          {busy ? "Збереження..." : editingId ? "Зберегти" : "Додати"}
        </button>
      </form>

      <div className="admin-simple-list">
        {items.length ? items.map((item) => (
          <article className="admin-simple-card" key={item.id}>
            <div>
              <p className="admin-kicker">#{item.id}</p>
              <h3>{item.name || item.code}</h3>
              <p className="muted">{renderSummary ? renderSummary(item) : item.description || "Без опису"}</p>
            </div>
            <div className="admin-actions">
              <button className="button ghost small" type="button" onClick={() => edit(item)}>Редагувати</button>
              <button className="button danger small" type="button" onClick={() => remove(item)}>Видалити</button>
            </div>
          </article>
        )) : <div className="admin-empty">{title}: записів поки немає.</div>}
      </div>
    </div>
  );
}
