import React, {useEffect,useState} from 'react';
import {authorizationHeaders,fetchSession,type SessionUser} from '../services/session';

export function RegistrationReviewQueue({ onReviewed }: { onReviewed?: () => Promise<unknown> }) {
  const [items,setItems] = useState<any[]>([]);
  const [user,setUser] = useState<SessionUser|null>(null);
  const [error,setError] = useState('');
  const [comments,setComments] = useState<Record<string,string>>({});
  const [busy,setBusy] = useState(false);
  const load = async () => {
    try {
      const session = await fetchSession(); setUser(session);
      const response = await fetch('/api/v1/registrations',{headers:authorizationHeaders()});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || 'Cannot load asset registrations');
      setItems(data); setError('');
    } catch(e) { setError((e as Error).message); }
  };
  useEffect(() => { void load(); },[]);
  const review = async (code:string,status:string) => {
    setBusy(true);
    try {
      const response = await fetch(`/api/v1/registrations/${encodeURIComponent(code)}`,{method:'PATCH',headers:{...authorizationHeaders(),'Content-Type':'application/json'},body:JSON.stringify({status,comments:comments[code] ?? ''})});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || data.detail || 'Review failed');
      await load();
      await onReviewed?.();
    } catch(e) { setError((e as Error).message); }
    finally { setBusy(false); }
  };
  return <section className="space-y-3 rounded-xl border border-gray-700 bg-[#0b1723] p-4">
    <h3 className="font-bold text-white">Asset Registrations — Review Queue</h3>
    {error && <p role="alert" className="text-red-400">{error}</p>}
    {!items.length && !error && <p className="text-gray-400">No asset registrations awaiting review.</p>}
    {items.map(asset => <article key={asset.asset_code} className="rounded border border-gray-700 p-3 text-sm text-gray-300">
      <p className="font-semibold text-white">{asset.name} — {asset.asset_code}</p>
      <p>{asset.status} · {asset.district} · Submitted by {asset.created_by} · {asset.created_at}</p>
      <p>Assessment: WITHHELD pending sufficient evidence.</p>
      {user && ['REVIEWER','ADMIN'].includes(user.role) && asset.created_by !== user.id && asset.status === 'PENDING_REVIEW' && <div className="mt-2 flex flex-wrap gap-2">
        <input aria-label={`Review comments for ${asset.asset_code}`} value={comments[asset.asset_code] ?? ''} onChange={e => setComments({...comments,[asset.asset_code]:e.target.value})} placeholder="Required review comments" className="bg-slate-900 border border-gray-600 p-2 rounded"/>
        <button disabled={busy || !comments[asset.asset_code]?.trim()} onClick={() => void review(asset.asset_code,'APPROVED')} className="px-3 py-2 bg-emerald-800 rounded disabled:opacity-40">Approve registration</button>
        <button disabled={busy || !comments[asset.asset_code]?.trim()} onClick={() => void review(asset.asset_code,'REJECTED')} className="px-3 py-2 bg-red-900 rounded disabled:opacity-40">Reject registration</button>
      </div>}
    </article>)}
  </section>;
}
