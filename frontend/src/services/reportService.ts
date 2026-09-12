import { apiRequest } from "./api";

export const reportService = {
  list: () => apiRequest<{ recent_assessments?: Array<unknown> }>("/api/v1/dashboard/overview"),
  get: (id: string) => apiRequest<unknown>(`/api/v1/infrastructure/${encodeURIComponent(id)}`),
  notifications: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
};
