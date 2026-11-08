import { api } from "./client";

export function getAdminOrders() {
  return api.get("/api/orders");
}

export function updateAdminOrderStatus(orderId, status) {
  return api.patch(`/api/orders/${orderId}/status`, { status });
}

export function getAdminFlowers() {
  return api.get("/api/flowers");
}

export function createAdminFlower(payload) {
  return api.post("/api/flowers", payload);
}

export function updateAdminFlower(flowerId, payload) {
  return api.put(`/api/flowers/${flowerId}`, payload);
}

export function deleteAdminFlower(flowerId) {
  return api.delete(`/api/flowers/${flowerId}`);
}

export function getAdminBouquets() {
  return api.get("/api/bouquets");
}

export function createAdminBouquet(payload) {
  return api.post("/api/bouquets", payload);
}

export function updateAdminBouquet(bouquetId, payload) {
  return api.put(`/api/bouquets/${bouquetId}`, payload);
}

export function deleteAdminBouquet(bouquetId) {
  return api.delete(`/api/bouquets/${bouquetId}`);
}

export function getAdminOccasions() {
  return api.get("/api/occasions");
}
