import { api } from "./client";

export function getClientNotifications(clientId, unreadOnly = false) {
  const query = unreadOnly ? "?unread_only=true" : "";
  return api.get(`/api/notifications/client/${clientId}${query}`);
}

export function markNotificationRead(notificationId) {
  return api.patch(`/api/notifications/${notificationId}/read`, {});
}

export function markAllNotificationsRead(clientId) {
  return api.patch(`/api/notifications/client/${clientId}/read-all`, {});
}
