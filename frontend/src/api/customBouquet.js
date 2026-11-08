import { api } from "./client";

export function getFlowers() {
  return api.get("/api/flowers");
}

export function getPackagingOptions() {
  return api.get("/api/packaging");
}

export function getBuilderOccasions() {
  return api.get("/api/occasions");
}

export function previewCustomBouquet(payload) {
  return api.post("/api/bouquets/custom", payload);
}
