import React, { useState, useEffect, useRef } from "react";
import { Sparkles, Send, X, Bot, RefreshCw, AlertTriangle, ShieldCheck, CheckCircle2, CornerDownLeft } from "lucide-react";
import type { AssetSummary } from "../types/twin";
import { riskColor } from "../utils";

interface AiAssistantProps {
  asset?: AssetSummary | null;
  selectedAsset?: AssetSummary | null;
  isOpen: boolean;
  onClose: () => void;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  timestamp: string;
}

export function AiAssistantDrawer({ asset, selectedAsset, isOpen, onClose }: AiAssistantProps) {
  const currentAsset = selectedAsset || asset;
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const requestGeneration = useRef(0);

  // Auto-scroll to bottom of messages
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    if (isOpen) {
      scrollToBottom();
    }
  }, [messages, isOpen, loading]);

  // Set initial greeting when asset changes or opens
  useEffect(() => {
    requestGeneration.current++;
    setLoading(false);
    if (currentAsset) {
      setMessages([
        {
          role: "assistant",
          content: `SIMRAS Engineering Advisor is ready for **${currentAsset.name}** (\`${currentAsset.asset_code}\`). I will use available registry, assessment, inspection, maintenance, environmental, and source evidence and identify missing information rather than invent it.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } else {
      setMessages([
        {
          role: "assistant",
          content: `Welcome to the **SIMRAS AI Engineering Advisor**. Please select an infrastructure asset from the registry to begin engineering diagnosis, failure mode analysis, or CWC compliance verification.`,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    }
  }, [currentAsset?.asset_code, isOpen]);

  if (!isOpen) return null;

  const handleSend = async (queryText?: string) => {
    const text = queryText || input.trim();
    if (!text || loading || !currentAsset?.asset_code) return;
    const generation = requestGeneration.current;

    const userMsg: Message = {
      role: "user",
      content: text,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    if (!queryText) setInput("");
    setLoading(true);

    try {
      if (!currentAsset?.asset_code) throw new Error("Select an asset first");
      const assetCode = currentAsset.asset_code;
      const token = localStorage.getItem("simras_token");
      const res = await fetch(`/api/v1/ai/assets/${encodeURIComponent(assetCode)}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        body: JSON.stringify({ question: text, selected_asset_code: assetCode, history: messages.slice(1).map(({ role, content }) => ({ role, content })) }),
      });

      const data = await res.json();
      if (!res.ok) throw new Error(data.error || (res.status === 401 ? 'Please sign in again to use the advisor.' : 'The engineering advisor is currently unavailable.'));
      if (generation !== requestGeneration.current) return;
      const aiMsg: Message = {
        role: "assistant",
        content: data.answer || "No answer was returned. Please try again.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, aiMsg]);
    } catch (err: any) {
      if (generation !== requestGeneration.current) return;
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof TypeError ? 'Could not connect to the engineering advisor. Please check your connection and retry.' : err.message,
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        },
      ]);
    } finally {
      if (generation === requestGeneration.current) setLoading(false);
    }
  };

  const quickPrompts = [
    "Explain Health Score & Deterioration",
    "Explain Risk Level & Hydrologic Factors",
    "CWC Dam Safety Standards & Compliance",
    "Inspect 3D Dimensions & Engineering Specs",
    "Draft Preventive Maintenance Plan",
  ];

  return (
    <>
      {/* Dark backdrop overlay with blur (z-2000 guarantees it sits above Leaflet and all 3D canvases) */}
      <div
        className="fixed inset-0 bg-black/75 backdrop-blur-sm z-[2000] transition-opacity"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Drawer Container (z-2001 sits in front of backdrop) */}
      <aside
        className="fixed inset-y-0 right-0 z-[2001] w-full max-w-lg bg-[#07131e] border-l border-cyan-500/30 shadow-2xl flex flex-col text-white"
        role="dialog"
        aria-modal="true"
        aria-label="SIMRAS AI Engineering Advisor"
      >
        {/* Header */}
        <div className="p-4 border-b border-cyan-500/20 bg-[#0a1827] flex items-center justify-between shrink-0 shadow-md">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-400/40 flex items-center justify-center text-cyan-400 shadow-inner">
              <Sparkles className="w-5 h-5 text-cyan-400 animate-pulse" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-bold text-white tracking-wide">
                  SIMRAS AI Engineering Advisor
                </h3>
                <span className="text-[9px] font-bold px-1.5 py-0.2 rounded bg-cyan-900/80 text-cyan-300 border border-cyan-500/40">
                  EVIDENCE GROUNDED
                </span>
              </div>
              <p className="text-[11px] text-cyan-300/80 font-mono mt-0.5 truncate max-w-[280px]">
                Target: {currentAsset ? `${currentAsset.name} (${currentAsset.asset_code})` : "No asset selected"}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-white/10 transition"
            aria-label="Close Advisor"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Asset Context Strip (if asset selected) */}
        {currentAsset && (
          <div className="px-4 py-2 bg-[#0d1f33] border-b border-gray-800 text-xs flex items-center justify-between shrink-0">
            <div className="flex items-center gap-3 text-[11px]">
              <span className="text-gray-400">
                Health: <strong className="text-white">{currentAsset.health_score?.toFixed(1) ?? "—"}/100</strong>
              </span>
              <span className="text-gray-400">
                Risk:{" "}
                <strong style={{ color: riskColor(currentAsset.risk_level) }}>
                  {currentAsset.risk_score?.toFixed(0) ?? "—"}/100 ({currentAsset.risk_level ?? "UNAVAILABLE"})
                </strong>
              </span>
              <span className="text-gray-400">
                District: <strong className="text-cyan-300">{currentAsset.district}</strong>
              </span>
            </div>
            <span className="text-[10px] text-emerald-400 flex items-center gap-1 font-semibold">
              <CheckCircle2 className="w-3 h-3" /> Grounded
            </span>
          </div>
        )}

        {/* Quick Prompts Bar (Custom subtle scrollbar, no ugly browser bar) */}
        <div className="px-3 py-2.5 border-b border-gray-800 bg-[#081524] shrink-0 overflow-x-auto [scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden">
          <div className="flex items-center gap-2 w-max">
            <span className="text-[10px] uppercase font-bold text-gray-400 tracking-wider mr-1">
              Suggestions:
            </span>
            {quickPrompts.map((q) => (
              <button
                key={q}
                onClick={() => handleSend(q)}
                disabled={loading || !currentAsset}
                className="text-[11px] py-1 px-3 rounded-full bg-[#122538] hover:bg-cyan-950 border border-cyan-500/30 hover:border-cyan-400 text-cyan-200 transition whitespace-nowrap disabled:opacity-40 font-medium active:scale-95"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Chat Messages Scroll Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#07131e]">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === "user" ? "items-end" : "items-start"}`}
            >
              <div className="flex items-center gap-1.5 mb-1 text-[10px] text-gray-400">
                {m.role === "assistant" ? (
                  <span className="flex items-center gap-1 text-cyan-400 font-semibold">
                    <Bot className="w-3.5 h-3.5" /> SIMRAS Advisor
                  </span>
                ) : (
                  <span className="text-gray-300 font-semibold">Engineer Query</span>
                )}
                <span>· {m.timestamp}</span>
              </div>

              <div
                className={`p-3.5 rounded-2xl text-xs leading-relaxed max-w-[92%] whitespace-pre-wrap shadow-lg ${
                  m.role === "user"
                    ? "bg-cyan-600 text-black font-semibold rounded-tr-none"
                    : "bg-[#0c1c2e] border border-cyan-500/25 text-gray-200 rounded-tl-none"
                }`}
              >
                {m.content}
              </div>
            </div>
          ))}

          {loading && (
            <div className="flex items-center gap-2 text-xs text-cyan-400 p-3 rounded-xl bg-[#0c1c2e] border border-cyan-500/20 max-w-[85%]">
              <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
              <span>Analyzing structural telemetry, geotechnical baseline, and CWC safety guidelines...</span>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <div className="p-4 border-t border-cyan-500/20 bg-[#0a1827] shrink-0">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              handleSend();
            }}
            className="flex items-center gap-2"
          >
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder={
                asset
                  ? `Ask engineering question about ${asset.name}...`
                  : "Ask engineering assessment question..."
              }
              disabled={loading || !currentAsset}
              className="flex-1 bg-[#0f2134] border border-gray-700 focus:border-cyan-400 rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none transition"
            />
            <button
              type="submit"
              disabled={!input.trim() || loading || !currentAsset}
              className="px-3.5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-black font-bold transition disabled:opacity-40 flex items-center justify-center gap-1.5 text-xs"
            >
              <span>Send</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
          <div className="mt-2 text-[10px] text-gray-400 text-center">
            Decision support AI grounded in verified engineering parameters. Does not replace statutory physical audits.
          </div>
        </div>
      </aside>
    </>
  );
}
