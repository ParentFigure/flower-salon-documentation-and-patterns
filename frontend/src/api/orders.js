import { api } from "./client";

export function getDeliveryMethods() {
  return api.get("/api/delivery-methods");
}

export function getSalons() {
  return api.get("/api/salons");
}

export function createOrder(payload) {
  return api.post("/api/orders", payload);
}
