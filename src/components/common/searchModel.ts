export type SearchResultType = "asset" | "inspection" | "maintenance" | "report";

export interface SearchResult {
  type: SearchResultType;
  id: string;
  title: string;
  subtitle: string;
  asset_code?: string;
  action_url: string;
}

export interface SearchGroups {
  assets: SearchResult[];
  inspections: SearchResult[];
  maintenance: SearchResult[];
  reports: SearchResult[];
}

export function shouldSearch(query: string) {
  return query.trim().length >= 2;
}

export function groupSearchResults(results: SearchResult[]): SearchGroups {
  return {
    assets: results.filter((item) => item.type === "asset"),
    inspections: results.filter((item) => item.type === "inspection"),
    maintenance: results.filter((item) => item.type === "maintenance"),
    reports: results.filter((item) => item.type === "report"),
  };
}

export function moveSearchIndex(current: number, delta: number, count: number) {
  if (count === 0) return -1;
  return (current + delta + count) % count;
}
