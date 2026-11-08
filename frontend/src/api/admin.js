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
  return api.get("/api/occasions/admin/all");
}

export function createAdminOccasion(payload) {
  return api.post("/api/occasions", payload);
}

export function updateAdminOccasion(id, payload) {
  return api.put(`/api/occasions/${id}`, payload);
}

export function deleteAdminOccasion(id) {
  return api.delete(`/api/occasions/${id}`);
}

export function getAdminPackaging() {
  return api.get("/api/packaging/admin/all");
}

export function createAdminPackaging(payload) {
  return api.post("/api/packaging", payload);
}

export function updateAdminPackaging(id, payload) {
  return api.put(`/api/packaging/${id}`, payload);
}

export function deleteAdminPackaging(id) {
  return api.delete(`/api/packaging/${id}`);
}

export function getAdminSalons() {
  return api.get("/api/salons/admin/all");
}

export function createAdminSalon(payload) {
  return api.post("/api/salons", payload);
}

export function updateAdminSalon(id, payload) {
  return api.put(`/api/salons/${id}`, payload);
}

export function deleteAdminSalon(id) {
  return api.delete(`/api/salons/${id}`);
}

export function getAdminDeliveryMethods() {
  return api.get("/api/delivery-methods/admin/all");
}

export function createAdminDeliveryMethod(payload) {
  return api.post("/api/delivery-methods", payload);
}

export function updateAdminDeliveryMethod(id, payload) {
  return api.put(`/api/delivery-methods/${id}`, payload);
}

export function deleteAdminDeliveryMethod(id) {
  return api.delete(`/api/delivery-methods/${id}`);
}

export function getAdminLoyaltyCard(clientId) {
  return api.get(`/api/loyalty/clients/${clientId}/card`);
}

export function issueAdminLoyaltyCard(payload) {
  return api.post("/api/loyalty/cards", payload);
}

export function updateAdminLoyaltyCard(clientId, payload) {
  return api.put(`/api/loyalty/clients/${clientId}/card`, payload);
}

export function accrueAdminBonus(clientId, amount) {
  return api.post(`/api/loyalty/clients/${clientId}/bonus/accrue`, { amount });
}

export function spendAdminBonus(clientId, amount) {
  return api.post(`/api/loyalty/clients/${clientId}/bonus/spend`, { amount });
}
