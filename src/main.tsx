import React, { Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import "leaflet/dist/leaflet.css";

interface ErrorBoundaryProps {
  children: ReactNode;
}

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("SIMRAS Application Error:", error, errorInfo);
    this.setState({ errorInfo });
  }

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: 40, color: "#e2e8f0", background: "#06121e", minHeight: "100vh", fontFamily: "system-ui, sans-serif" }}>
          <div style={{ maxWidth: 800, margin: "0 auto", background: "#0b1b2b", border: "1px solid rgba(239, 68, 68, 0.4)", borderRadius: 12, padding: 24, boxShadow: "0 20px 40px rgba(0,0,0,0.5)" }}>
            <h2 style={{ margin: "0 0 12px", color: "#f87171", fontSize: 20 }}>SIMRAS Operational Alert</h2>
            <p style={{ color: "#94a3b8", fontSize: 14, margin: "0 0 16px" }}>
              The application encountered an unhandled interface exception. Diagnostic telemetry is detailed below:
            </p>
            <div style={{ background: "#040a12", padding: 14, borderRadius: 8, overflow: "auto", fontSize: 12, color: "#38bdf8", fontFamily: "monospace", maxHeight: 300, border: "1px solid #1e293b" }}>
              {this.state.error?.toString()}
              {"\n\n"}
              {this.state.error?.stack}
            </div>
            <button
              onClick={() => window.location.reload()}
              style={{ marginTop: 20, padding: "10px 20px", background: "#06b6d4", color: "#000", border: 0, borderRadius: 8, cursor: "pointer", fontWeight: 700, fontSize: 13 }}
            >
              Restart Platform
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

const rootElement = document.getElementById("root");
if (rootElement) {
  createRoot(rootElement).render(
    <ErrorBoundary>
      <App />
    </ErrorBoundary>
  );
}

