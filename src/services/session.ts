export interface SessionUser { id:string; name:string; email:string; role:'PUBLIC'|'OFFICER'|'REVIEWER'|'ADMIN'; department:string; }
export function authorizationHeaders(): Record<string,string> {
  const token = localStorage.getItem('simras_token');
  return token ? {Authorization:`Bearer ${token}`} : {};
}
export async function fetchSession(): Promise<SessionUser> {
  const response = await fetch('/api/v1/auth/me',{headers:authorizationHeaders(),cache:'no-store'});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) { localStorage.removeItem('simras_token'); localStorage.removeItem('simras_user'); }
    throw new Error(data.error || 'Unable to verify your session. Sign in again.');
  }
  // Cached profile is display-only. Every authorization decision is server-side.
  localStorage.setItem('simras_user',JSON.stringify(data));
  return data;
}
