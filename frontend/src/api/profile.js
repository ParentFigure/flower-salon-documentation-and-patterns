import { api } from "./client";

export function getProfile() {
  return api.get("/api/profile");
}

export function updateProfile(payload) {
  return api.patch("/api/profile", payload);
}
