import React, { useEffect, useState } from "react";
import { Camera, Save, Trash2, User } from "lucide-react";
import { validateProfilePatch, validateProfilePhoto } from "./profileValidation";

type Profile = {
  id: string; officer_id?: string; name: string; email: string; role: string;
  department: string; phone?: string; district?: string; photo_url?: string;
  created_at?: string; last_login?: string;
};

const auth = () => {
  const token = localStorage.getItem("simras_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
};

export function ProfilePage({ onUserUpdate }: { onUserUpdate?: (profile: Profile) => void }) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [draft, setDraft] = useState({ name: "", phone: "", district: "" });
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    fetch("/api/v1/profile", { headers: auth() }).then(async (response) => {
      if (!response.ok) throw new Error((await response.json()).error || "Profile could not be loaded");
      return response.json();
    }).then((value: Profile) => {
      setProfile(value);
      setDraft({ name: value.name ?? "", phone: value.phone ?? "", district: value.district ?? "" });
    }).catch((error) => setMessage(error.message));
  }, []);

  const reset = (value = profile) => value && setDraft({ name: value.name ?? "", phone: value.phone ?? "", district: value.district ?? "" });
  const save = async () => {
    const errors = validateProfilePatch(draft);
    if (Object.keys(errors).length) { setMessage(Object.values(errors)[0]); return; }
    setBusy(true); setMessage("");
    try {
      const response = await fetch("/api/v1/profile", { method: "PATCH", headers: { "Content-Type": "application/json", ...auth() }, body: JSON.stringify(draft) });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error || "Profile could not be saved");
      setProfile(value); reset(value); onUserUpdate?.(value); setMessage("Profile saved.");
    } catch (error: any) { setMessage(error.message); } finally { setBusy(false); }
  };
  const upload = async (file?: File) => {
    if (!file) return;
    const error = validateProfilePhoto(file);
    if (error) { setMessage(error); return; }
    setBusy(true); setMessage("");
    try {
      const response = await fetch("/api/v1/profile/photo", { method: "POST", headers: { "Content-Type": file.type, ...auth() }, body: file });
      const value = await response.json();
      if (!response.ok) throw new Error(value.error || "Photo could not be uploaded");
      setProfile(value); onUserUpdate?.(value); setMessage("Photo updated.");
    } catch (uploadError: any) { setMessage(uploadError.message); } finally { setBusy(false); }
  };
  const removePhoto = async () => {
    const response = await fetch("/api/v1/profile/photo", { method: "DELETE", headers: auth() });
    const value = await response.json();
    if (response.ok) { setProfile(value); onUserUpdate?.(value); setMessage("Photo removed."); }
  };

  if (!profile) return <div className="text-sm text-slate-600">{message || "Loading profile…"}</div>;
  const immutable = [["Officer ID", profile.officer_id ?? profile.id], ["Email", profile.email], ["Role", profile.role], ["Department", profile.department], ["Last login", profile.last_login ?? "NOT AVAILABLE"]];
  return <section className="max-w-4xl space-y-5">
    <div><h1 className="text-xl font-bold text-slate-900">Officer profile</h1><p className="text-sm text-slate-500">Manage your contact details and profile image.</p></div>
    <div className="grid gap-5 lg:grid-cols-[220px_1fr]">
      <div className="rounded-lg border border-slate-200 bg-white p-5 text-center shadow-sm">
        <div className="mx-auto mb-3 grid h-24 w-24 place-items-center overflow-hidden rounded-full bg-sky-50 text-sky-700">
          {profile.photo_url ? <img src={profile.photo_url} alt="Officer profile" className="h-full w-full object-cover" /> : <User className="h-10 w-10" />}
        </div>
        <label className="inline-flex cursor-pointer items-center gap-2 rounded bg-[#0875BE] px-3 py-2 text-xs font-semibold text-white"><Camera className="h-4 w-4" />Upload photo<input type="file" accept="image/jpeg,image/png,image/webp" className="hidden" onChange={(event) => upload(event.target.files?.[0])} /></label>
        {profile.photo_url && <button onClick={removePhoto} className="mt-2 flex w-full items-center justify-center gap-1 text-xs text-red-600"><Trash2 className="h-3 w-3" />Remove photo</button>}
        <p className="mt-3 text-[11px] text-slate-500">JPEG, PNG or WebP · maximum 2 MB</p>
      </div>
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <div className="grid gap-4 sm:grid-cols-2">
          {[{ key: "name", label: "Full name" }, { key: "phone", label: "Phone" }, { key: "district", label: "District / office" }].map(({ key, label }) => <label key={key} className="text-xs font-semibold text-slate-700">{label}<input value={draft[key as keyof typeof draft]} onChange={(event) => setDraft({ ...draft, [key]: event.target.value })} className="mt-1 w-full rounded border border-slate-300 px-3 py-2 text-sm font-normal outline-none focus:border-sky-500" /></label>)}
        </div>
        <div className="mt-5 grid gap-3 border-t border-slate-100 pt-5 sm:grid-cols-2">{immutable.map(([label, value]) => <div key={label}><span className="text-[10px] font-bold uppercase text-slate-400">{label}</span><p className="text-sm text-slate-700">{value}</p></div>)}</div>
        {message && <p role="status" className="mt-4 text-xs text-sky-700">{message}</p>}
        <div className="mt-5 flex gap-2"><button disabled={busy} onClick={save} className="flex items-center gap-2 rounded bg-[#0875BE] px-4 py-2 text-xs font-bold text-white disabled:opacity-50"><Save className="h-4 w-4" />Save</button><button onClick={() => { reset(); setMessage(""); }} className="rounded border border-slate-300 px-4 py-2 text-xs font-bold text-slate-700">Cancel</button></div>
      </div>
    </div>
  </section>;
}
