const CHECKOUT_DRAFT_KEY = "flower_salon_checkout_draft";

export function saveCheckoutDraft(draft) {
  sessionStorage.setItem(CHECKOUT_DRAFT_KEY, JSON.stringify(draft));
}

export function getCheckoutDraft() {
  const raw = sessionStorage.getItem(CHECKOUT_DRAFT_KEY);
  if (!raw) return null;

  try {
    const draft = JSON.parse(raw);
    if (!draft || !["catalog", "custom"].includes(draft.kind)) {
      clearCheckoutDraft();
      return null;
    }
    return draft;
  } catch {
    clearCheckoutDraft();
    return null;
  }
}

export function clearCheckoutDraft() {
  sessionStorage.removeItem(CHECKOUT_DRAFT_KEY);
}
