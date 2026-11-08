import { api } from "./client";

export function getBouquets(occasionSlug = "") {
  const query = occasionSlug
    ? `?occasion=${encodeURIComponent(occasionSlug)}`
    : "";
  return api.get(`/api/bouquets${query}`);
}

export function getOccasions() {
  return api.get("/api/occasions");
}
