import React, { useEffect, useState } from "react";
import { Save, RotateCcw } from "lucide-react";
import { defaultPreferences, mergePreferences, type Preferences } from "./settingsModel";

const labels: Record<string, string> = { general: "General", notifications: "Notifications", gis: "GIS", twin: "Digital Twin", reports: "Reports & exports", ai: "AI assistant", accessibility: "Accessibility" };
const fieldLabel = (key: string) => key.replace(/([A-Z])/g, " $1").replace(/^./, (letter) => letter.toUpperCase());
const choices: Record<string, string[]> = { landingPage: ["dashboard", "assets", "gis"], assetCategory: ["ALL", "DAM", "BARRAGE", "BRIDGE"], dateFormat: ["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"], timeFormat: ["24h", "12h"], units: ["metric", "imperial"], defaultLayer: ["street", "satellite", "terrain"], defaultRiskFilter: ["ALL", "HIGH", "MEDIUM", "LOW"], defaultCamera: ["perspective", "top", "front"], renderingQuality: ["auto", "high", "performance"], exportType: ["PDF", "CSV"], responseDetail: ["concise", "standard", "detailed"], textSize: ["default", "large", "larger"] };
const auth = () => { const token = localStorage.getItem("simras_token"); return token ? { Authorization: `Bearer ${token}` } : {}; };

export function SettingsPage() {
  const [saved, setSaved] = useState<Preferences>(defaultPreferences);
  const [draft, setDraft] = useState<Preferences>(defaultPreferences);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { fetch("/api/v1/preferences", { headers: auth() }).then((response) => response.ok ? response.json() : {}).then((value) => { const merged = mergePreferences(defaultPreferences, value); setSaved(merged); setDraft(merged); }).catch(() => setMessage("Saved settings could not be loaded.")); }, []);
  const update = (section: keyof Preferences, key: string, value: string | boolean) => setDraft({ ...draft, [section]: { ...draft[section], [key]: value } } as Preferences);
  const save = async () => {
    setBusy(true); setMessage("");
    try { const response = await fetch("/api/v1/preferences", { method: "PATCH", headers: { "Content-Type": "application/json", ...auth() }, body: JSON.stringify(draft) }); const value = await response.json(); if (!response.ok) throw new Error(value.error || "Settings could not be saved"); const merged = mergePreferences(defaultPreferences, value); setSaved(merged); setDraft(merged); setMessage("Settings saved."); } catch (error: any) { setMessage(error.message); } finally { setBusy(false); }
  };
  return <section className="max-w-5xl space-y-5">
    <div><h1 className="text-xl font-bold text-slate-900">Officer settings</h1><p className="text-sm text-slate-500">Preferences are saved to your authenticated account.</p></div>
    <div className="grid gap-4 lg:grid-cols-2">{Object.entries(draft).map(([section, values]) => <div key={section} className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm"><h2 className="mb-3 text-sm font-bold text-slate-900">{labels[section]}</h2><div className="space-y-3">{Object.entries(values).map(([key, value]) => <label key={key} className="flex items-center justify-between gap-3 text-xs text-slate-700"><span>{fieldLabel(key)}</span>{typeof value === "boolean" ? <input type="checkbox" checked={value} onChange={(event) => update(section as keyof Preferences, key, event.target.checked)} className="h-4 w-4 accent-sky-600" /> : choices[key] ? <select value={String(value)} onChange={(event) => update(section as keyof Preferences, key, event.target.value)} className="rounded border border-slate-300 bg-white px-2 py-1.5 text-xs">{choices[key].map((choice) => <option key={choice}>{choice}</option>)}</select> : <input value={String(value)} onChange={(event) => update(section as keyof Preferences, key, event.target.value)} className="w-32 rounded border border-slate-300 px-2 py-1.5 text-xs" />}</label>)}</div></div>)}</div>
    {message && <p role="status" className="text-xs text-sky-700">{message}</p>}
    <div className="flex gap-2"><button disabled={busy} onClick={save} className="flex items-center gap-2 rounded bg-[#0875BE] px-4 py-2 text-xs font-bold text-white disabled:opacity-50"><Save className="h-4 w-4" />Save settings</button><button onClick={() => { setDraft(saved); setMessage(""); }} className="flex items-center gap-2 rounded border border-slate-300 px-4 py-2 text-xs font-bold text-slate-700"><RotateCcw className="h-4 w-4" />Cancel changes</button></div>
  </section>;
}
