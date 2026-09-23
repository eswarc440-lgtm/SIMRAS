import { apiRequest } from "./api";

export const analyticsService = {
  healthTrend: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
  riskDistribution: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
  regional: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
  categories: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
  totals: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
  activity: () => apiRequest<unknown>("/api/v1/dashboard/overview"),
};
