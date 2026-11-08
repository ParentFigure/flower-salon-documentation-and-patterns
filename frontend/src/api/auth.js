import { api } from "./client";

export function loginUser(email, password) {
  return api.post("/api/auth/login", {
    email: email.trim().toLowerCase(),
    password,
  });
}

export function registerClient({ email, password, full_name, phone }) {
  return api.post("/api/auth/register", {
    email: email.trim().toLowerCase(),
    password,
    full_name: full_name.trim(),
    phone: phone.trim() || null,
  });
}

export function getCurrentUser() {
  return api.get("/api/auth/me");
}
