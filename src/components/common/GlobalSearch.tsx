import { Search } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { moveSearchIndex, shouldSearch, type SearchGroups, type SearchResult } from "./searchModel";

const emptyGroups: SearchGroups = { assets: [], inspections: [], maintenance: [], reports: [] };

export function GlobalSearch({ onSelect }: { onSelect: (result: SearchResult) => void }) {
  const [query, setQuery] = useState("");
  const [groups, setGroups] = useState<SearchGroups>(emptyGroups);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeIndex, setActiveIndex] = useState(-1);
  const results = useMemo(() => [...groups.assets, ...groups.inspections, ...groups.maintenance, ...groups.reports], [groups]);

  useEffect(() => {
    if (!shouldSearch(query)) {
      setGroups(emptyGroups);
      setLoading(false);
      setError("");
      return;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(async () => {
      setLoading(true);
      setError("");
      try {
        const token = localStorage.getItem("simras_token");
        const response = await fetch(`/api/v1/search?q=${encodeURIComponent(query.trim())}`, {
          signal: controller.signal,
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!response.ok) throw new Error("Search is unavailable");
        const payload = await response.json();
        setGroups(payload.groups ?? emptyGroups);
        setActiveIndex(-1);
      } catch (caught) {
        if (!controller.signal.aborted) setError(caught instanceof Error ? caught.message : "Search failed");
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }, 250);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [query]);

  const choose = (result: SearchResult) => {
    onSelect(result);
    setQuery("");
    setGroups(emptyGroups);
  };

  const showPanel = shouldSearch(query);
  return (
    <div className="relative w-full">
      <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-slate-400" />
      <input
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Escape") { setQuery(""); setGroups(emptyGroups); }
          if (event.key === "ArrowDown") { event.preventDefault(); setActiveIndex((index) => moveSearchIndex(index, 1, results.length)); }
          if (event.key === "ArrowUp") { event.preventDefault(); setActiveIndex((index) => moveSearchIndex(index, -1, results.length)); }
          if (event.key === "Enter" && activeIndex >= 0 && results[activeIndex]) choose(results[activeIndex]);
        }}
        placeholder="Search assets, work orders, inspections…"
        className="w-full rounded-md border border-[#16689A]/50 bg-[#082946]/80 py-2 pl-9 pr-4 text-xs text-white placeholder-slate-400 focus:border-[#18A8D8] focus:outline-none focus:ring-1 focus:ring-[#18A8D8]"
      />
      {showPanel && (
        <div className="absolute left-0 right-0 top-full z-50 mt-2 max-h-[70vh] overflow-y-auto rounded-lg border border-slate-200 bg-white p-2 text-slate-800 shadow-2xl">
          {loading && <p className="p-3 text-xs text-slate-500">Searching SIMRAS records…</p>}
          {error && <p className="p-3 text-xs font-semibold text-red-600">{error}</p>}
          {!loading && !error && results.length === 0 && <p className="p-3 text-xs text-slate-500">No results found</p>}
          {(["assets", "inspections", "maintenance", "reports"] as const).map((groupName) => groups[groupName].length > 0 && (
            <section key={groupName} className="mb-2 last:mb-0">
              <h3 className="px-2 py-1 text-[10px] font-bold uppercase tracking-wider text-[#0875BE]">{groupName === "maintenance" ? "Maintenance / Work Orders" : groupName}</h3>
              {groups[groupName].map((result) => {
                const index = results.indexOf(result);
                return <button key={`${result.type}-${result.id}`} type="button" onMouseEnter={() => setActiveIndex(index)} onClick={() => choose(result)} className={`block w-full rounded px-2 py-2 text-left ${activeIndex === index ? "bg-blue-50" : "hover:bg-slate-50"}`}><span className="block text-xs font-bold text-slate-800">{result.title}</span><span className="block text-[10px] text-slate-500">{result.subtitle}</span></button>;
              })}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
