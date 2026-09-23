import { useState, useEffect } from 'react';
import { useAuth } from '../../contexts/AuthContext';

interface ProfileData {
  name: string;
  phone: string | null;
  department: string | null;
  designation: string | null;
  district: string | null;
}

export default function OfficerProfile() {
  const { user, logout } = useAuth();
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [profile, setProfile] = useState<ProfileData>({
    name: user?.name || '',
    phone: user?.phone || '',
    department: user?.department || '',
    designation: user?.designation || '',
    district: user?.district || '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setMessage('');

    try {
      const response = await fetch('/api/v1/auth/me', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(profile),
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      setMessage('Profile updated successfully');
    } catch (error) {
      setMessage(error instanceof Error ? error.message : 'Update failed');
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setProfile({
      ...profile,
      [e.target.name]: e.target.value,
    });
  };

  const handleLogout = async () => {
    await logout();
  };

  return (
    <div className="max-w-4xl mx-auto p-6">
      <div className="bg-slate-800 rounded-lg shadow-xl p-8">
        <h1 className="text-2xl font-bold text-white mb-6">Officer Profile</h1>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
          <div className="bg-slate-700 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-white mb-4">Identity</h2>
            <div className="space-y-2 text-slate-300">
              <p><span className="text-slate-400">Officer ID:</span> {user?.officer_id}</p>
              <p><span className="text-slate-400">Email:</span> {user?.email}</p>
              <p><span className="text-slate-400">Role:</span> {user?.role}</p>
              <p><span className="text-slate-400">Last Login:</span> {user?.last_login ? new Date(user.last_login).toLocaleString() : 'Never'}</p>
            </div>
          </div>

          <div className="bg-slate-700 rounded-lg p-4">
            <h2 className="text-lg font-semibold text-white mb-4">Statistics</h2>
            <div className="space-y-2 text-slate-300">
              <p><span className="text-slate-400">Assets Assigned:</span> 0</p>
              <p><span className="text-slate-400">Reviews Completed:</span> 0</p>
              <p><span className="text-slate-400">Plans Submitted:</span> 0</p>
              <p><span className="text-slate-400">Evidence Added:</span> 0</p>
            </div>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="space-y-6">
          {message && (
            <div className={`p-4 rounded ${message.includes('success') ? 'bg-green-900/50 text-green-100' : 'bg-red-900/50 text-red-100'}`}>
              {message}
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Name</label>
              <input
                name="name"
                type="text"
                value={profile.name}
                onChange={handleChange}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Phone</label>
              <input
                name="phone"
                type="tel"
                value={profile.phone || ''}
                onChange={handleChange}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Department</label>
              <input
                name="department"
                type="text"
                value={profile.department || ''}
                onChange={handleChange}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">Designation</label>
              <input
                name="designation"
                type="text"
                value={profile.designation || ''}
                onChange={handleChange}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">District</label>
              <input
                name="district"
                type="text"
                value={profile.district || ''}
                onChange={handleChange}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white"
              />
            </div>
          </div>

          <div className="flex gap-4">
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-lg disabled:opacity-50"
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </button>

            <button
              type="button"
              onClick={handleLogout}
              className="bg-red-600 hover:bg-red-700 text-white font-medium py-2 px-4 rounded-lg"
            >
              Logout
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
