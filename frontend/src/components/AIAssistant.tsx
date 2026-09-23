import { useState } from 'react';

interface AIAssistantProps {
  assetCode: string;
}

export default function AIAssistant({ assetCode }: AIAssistantProps) {
  const [question, setQuestion] = useState('');
  const [response, setResponse] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const quickActions = [
    { label: 'Explain Health', value: 'explain-health' },
    { label: 'Explain Risk', value: 'explain-risk' },
    { label: 'Explain RUL', value: 'explain-rul' },
    { label: 'Generate Summary', value: 'summary' },
    { label: 'Draft Maintenance Plan', value: 'draft-plan' },
  ];

  const handleQuickAction = async (action: string) => {
    setLoading(true);
    setError('');
    setResponse(null);

    try {
      const endpoint = action === 'draft-plan' ? 'draft-plan' : action;
      const res = await fetch(`/api/v1/reports/${assetCode}/assistant/${endpoint}`, {
        method: 'POST',
        credentials: 'include',
      });

      if (!res.ok) {
        throw new Error('Failed to get AI response');
      }

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get AI response');
    } finally {
      setLoading(false);
    }
  };

  const handleAsk = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim()) return;

    setLoading(true);
    setError('');
    setResponse(null);

    try {
      const res = await fetch(`/api/v1/reports/${assetCode}/assistant`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ question }),
      });

      if (!res.ok) {
        throw new Error('Failed to get AI response');
      }

      const data = await res.json();
      setResponse(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to get AI response');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg p-6 mt-6">
      <h2 className="text-xl font-bold text-white mb-4">SIMRAS AI Assistant</h2>

      <div className="mb-4">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Quick Actions
        </label>
        <div className="flex flex-wrap gap-2">
          {quickActions.map((action) => (
            <button
              key={action.value}
              onClick={() => handleQuickAction(action.value)}
              disabled={loading}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-300 rounded text-sm disabled:opacity-50"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      <form onSubmit={handleAsk} className="mb-4">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Ask about this asset...
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Type your question here..."
            className="flex-1 px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400"
            disabled={loading}
          />
          <button
            type="submit"
            disabled={loading || !question.trim()}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg disabled:opacity-50"
          >
            {loading ? 'Thinking...' : 'Ask'}
          </button>
        </div>
      </form>

      {error && (
        <div className="bg-red-900/50 border border-red-700 text-red-100 px-4 py-3 rounded mb-4">
          {error}
        </div>
      )}

      {response && (
        <div className="bg-slate-700 rounded-lg p-4">
          <h3 className="text-lg font-semibold text-white mb-2">Answer</h3>
          <p className="text-slate-300 mb-4">{response.answer}</p>

          {response.evidence_used && response.evidence_used.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-400 mb-1">Evidence Used:</h4>
              <ul className="list-disc list-inside text-slate-300 text-sm">
                {response.evidence_used.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {response.assessment_basis && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-400 mb-1">Assessment Basis:</h4>
              <p className="text-slate-300 text-sm">{response.assessment_basis}</p>
            </div>
          )}

          {response.limitations && response.limitations.length > 0 && (
            <div className="mb-4">
              <h4 className="text-sm font-semibold text-slate-400 mb-1">Limitations:</h4>
              <ul className="list-disc list-inside text-slate-300 text-sm">
                {response.limitations.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {response.sources && response.sources.length > 0 && (
            <div>
              <h4 className="text-sm font-semibold text-slate-400 mb-1">Sources:</h4>
              <ul className="list-disc list-inside text-slate-300 text-sm">
                {response.sources.map((item: string, idx: number) => (
                  <li key={idx}>{item}</li>
                ))}
              </ul>
            </div>
          )}

          {response.disclaimer && (
            <div className="mt-4 pt-4 border-t border-slate-600">
              <p className="text-yellow-400 text-xs">{response.disclaimer}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
