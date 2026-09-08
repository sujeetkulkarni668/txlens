"use client";

import { useState, useEffect } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export default function SettingsPage() {
  const defaultApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

  const [shieldOverTabs, setShieldOverTabs] = useState(true);
  const [autoIntercept, setAutoIntercept] = useState(true);
  const [alertThreshold, setAlertThreshold] = useState("all");
  const [selectedChain, setSelectedChain] = useState("base-sepolia");
  const [apiUrl, setApiUrl] = useState(defaultApiUrl);
  const [isTestingApi, setIsTestingApi] = useState(false);
  const [apiStatus, setApiStatus] = useState<"idle" | "connected" | "failed">("idle");
  const [saveSuccess, setSaveSuccess] = useState(false);

  // Load from localStorage on client mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const savedShield = localStorage.getItem("txlens_shield_over_tabs");
      if (savedShield !== null) setShieldOverTabs(savedShield === "true");

      const savedIntercept = localStorage.getItem("txlens_auto_intercept");
      if (savedIntercept !== null) setAutoIntercept(savedIntercept === "true");

      const savedThreshold = localStorage.getItem("txlens_alert_threshold");
      if (savedThreshold) setAlertThreshold(savedThreshold);

      const savedChain = localStorage.getItem("txlens_selected_chain");
      if (savedChain) setSelectedChain(savedChain);

      const savedApi = localStorage.getItem("txlens_api_url");
      if (savedApi) setApiUrl(savedApi);
    }
  }, []);

  const handleSaveSettings = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("txlens_shield_over_tabs", String(shieldOverTabs));
      localStorage.setItem("txlens_auto_intercept", String(autoIntercept));
      localStorage.setItem("txlens_alert_threshold", alertThreshold);
      localStorage.setItem("txlens_selected_chain", selectedChain);
      localStorage.setItem("txlens_api_url", apiUrl);
    }
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 2500);
  };

  const handleTestConnection = async () => {
    setIsTestingApi(true);
    setApiStatus("idle");
    try {
      const cleanUrl = apiUrl.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
      const res = await fetch(`${cleanUrl}/health`);
      if (res.ok) {
        setApiStatus("connected");
      } else {
        setApiStatus("failed");
      }
    } catch {
      setApiStatus("failed");
    } finally {
      setIsTestingApi(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink flex items-center gap-2">
          <span>🛡️</span> Settings & System Preferences
        </h1>
        <p className="mt-1 text-sm text-ink-muted">
          Configure cross-tab security shield, Web3 transaction interception, and backend AI threat models.
        </p>
      </div>

      {/* Cross-Tab Shield Configuration */}
      <Card>
        <CardHeader
          title="Cross-Tab & dApp Pop-Up Shield"
          subtitle="Control how TxLens protects you across external browser tabs (Uniswap, OpenSea, Etherscan, etc.)"
        />
        <div className="space-y-4 pt-2">
          {/* Toggle 1: Allow over tabs */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-muted/50 border border-border">
            <div className="space-y-0.5 max-w-xl">
              <label className="text-sm font-semibold text-ink flex items-center gap-2 cursor-pointer">
                <span>🌐</span> Allow Pop-Up Shield over other tabs & external dApps
              </label>
              <p className="text-xs text-ink-muted">
                When active, TxLens automatically inspects active web forms across any tab to detect transaction parameters before you submit them.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={shieldOverTabs}
                onChange={(e) => setShieldOverTabs(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand"></div>
            </label>
          </div>

          {/* Toggle 2: Auto Intercept */}
          <div className="flex items-center justify-between p-3 rounded-lg bg-surface-muted/50 border border-border">
            <div className="space-y-0.5 max-w-xl">
              <label className="text-sm font-semibold text-ink flex items-center gap-2 cursor-pointer">
                <span>⚡</span> Auto-Intercept Web3 Transactions before Signing
              </label>
              <p className="text-xs text-ink-muted">
                Hooks into Web3 wallet providers (<code className="text-xs bg-slate-800 px-1 py-0.5 rounded">window.ethereum</code>) to display the safety rating pop-up prior to opening your wallet confirmation prompt.
              </p>
            </div>
            <label className="relative inline-flex items-center cursor-pointer ml-4">
              <input
                type="checkbox"
                checked={autoIntercept}
                onChange={(e) => setAutoIntercept(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-brand"></div>
            </label>
          </div>

          {/* Alert Threshold */}
          <div className="p-3 rounded-lg bg-surface-muted/50 border border-border flex items-center justify-between">
            <div className="space-y-0.5">
              <div className="text-sm font-semibold text-ink">Warning Trigger Sensitivity</div>
              <div className="text-xs text-ink-muted">Choose when to pop up transaction safety alerts.</div>
            </div>
            <select
              value={alertThreshold}
              onChange={(e) => setAlertThreshold(e.target.value)}
              className="bg-surface border border-border rounded-md px-3 py-1.5 text-xs text-ink font-medium focus:outline-none focus:ring-1 focus:ring-brand cursor-pointer"
            >
              <option value="all">All Transactions (SAFE, MID, & RISK)</option>
              <option value="mid_and_risk">Suspicious & High Risk Only (MID & RISK)</option>
              <option value="risk_only">Critical Threats Only (RISK only)</option>
            </select>
          </div>
        </div>
      </Card>

      {/* Backend API & AI Engine */}
      <Card>
        <CardHeader
          title="Backend & AI Threat Analysis Engine"
          subtitle="Connection to the EVM simulation pipeline and free cloud AI models"
        />
        <div className="space-y-4 pt-2">
          <div>
            <label className="block text-xs font-semibold text-ink-muted uppercase tracking-wider mb-1.5">
              API Base Endpoint URL
            </label>
            <div className="flex gap-2">
              <input
                type="text"
                value={apiUrl}
                onChange={(e) => setApiUrl(e.target.value)}
                className="flex-1 bg-surface-muted border border-border rounded-lg px-3 py-2 text-sm font-mono text-ink focus:outline-none focus:ring-1 focus:ring-brand"
                placeholder="http://localhost:8000/api/v1"
              />
              <button
                onClick={handleTestConnection}
                disabled={isTestingApi}
                className="px-4 py-2 bg-surface border border-border hover:bg-surface-muted rounded-lg text-xs font-semibold text-ink flex items-center gap-1.5 transition-colors disabled:opacity-50"
              >
                {isTestingApi ? "Testing..." : "Test Connection"}
              </button>
            </div>
            {apiStatus === "connected" && (
              <p className="mt-2 text-xs text-emerald-400 flex items-center gap-1">
                ✓ Connected successfully to TxLens FastAPI service (v1).
              </p>
            )}
            {apiStatus === "failed" && (
              <p className="mt-2 text-xs text-rose-400 flex items-center gap-1">
                ✕ Unable to reach backend. Ensure `uvicorn services.api.main:app` is running on port 8000.
              </p>
            )}
          </div>

          <div className="p-3.5 rounded-lg bg-surface-muted/60 border border-border">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold text-ink flex items-center gap-1.5">
                <span>🤖</span> Active AI Model Engine
              </span>
              <Badge variant="success">100% Free Cloud LLM</Badge>
            </div>
            <p className="text-xs text-ink-muted leading-relaxed">
              Powered by multi-provider AI fallback: <strong className="text-ink">Google Gemini 1.5 Flash</strong>, <strong className="text-ink">Groq Llama-3.3 70B</strong>, <strong className="text-ink">OpenRouter Free</strong>, and local <strong className="text-ink">Ollama</strong>. No paid Anthropic/OpenAI keys required.
            </p>
          </div>
        </div>
      </Card>

      {/* Network Configuration */}
      <Card>
        <CardHeader title="EVM Network Selection" subtitle="Target blockchain for bytecode simulation and heuristic checks" />
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2">
          {[
            { id: "base-sepolia", name: "Base Sepolia Testnet", chainId: 84532, badge: "Default" },
            { id: "ethereum", name: "Ethereum Mainnet", chainId: 1, badge: "Mainnet" },
            { id: "base", name: "Base Mainnet", chainId: 8453, badge: "L2" },
            { id: "arbitrum", name: "Arbitrum One", chainId: 42161, badge: "L2" },
          ].map((net) => (
            <div
              key={net.id}
              onClick={() => setSelectedChain(net.id)}
              className={`p-3.5 rounded-lg border cursor-pointer transition-all flex items-center justify-between ${
                selectedChain === net.id
                  ? "border-brand bg-brand/10 text-white shadow-sm shadow-brand/20"
                  : "border-border bg-surface-muted hover:border-slate-600"
              }`}
            >
              <div>
                <div className="text-sm font-semibold text-ink">{net.name}</div>
                <div className="text-xs text-ink-muted">Chain ID: {net.chainId}</div>
              </div>
              <Badge variant={selectedChain === net.id ? "info" : "outline"}>{net.badge}</Badge>
            </div>
          ))}
        </div>
      </Card>

      {/* Browser Extension Installation Guide */}
      <Card>
        <CardHeader
          title="Load Browser Extension (All Tabs & dApps)"
          subtitle="Deploy TxLens to Chrome, Brave, Edge, or Opera in 3 simple steps"
        />
        <div className="space-y-3 pt-2 text-xs text-ink-muted leading-relaxed">
          <div className="flex items-start gap-2.5">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand/20 text-brand font-bold flex items-center justify-center text-[11px]">
              1
            </span>
            <span>
              Open your browser&apos;s extension manager at <code className="bg-slate-800 text-ink px-1.5 py-0.5 rounded">chrome://extensions</code> (or <code className="bg-slate-800 text-ink px-1.5 py-0.5 rounded">brave://extensions</code>) and toggle <strong className="text-ink">Developer Mode</strong> ON.
            </span>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand/20 text-brand font-bold flex items-center justify-center text-[11px]">
              2
            </span>
            <span>
              Click <strong className="text-ink">&quot;Load unpacked&quot;</strong> and select the directory: <code className="bg-slate-800 text-ink px-1.5 py-0.5 rounded font-mono">apps/extension</code> from this project folder.
            </span>
          </div>
          <div className="flex items-start gap-2.5">
            <span className="flex-shrink-0 w-5 h-5 rounded-full bg-brand/20 text-brand font-bold flex items-center justify-center text-[11px]">
              3
            </span>
            <span>
              Pin the <strong>TxLens Security Shield</strong> icon in your toolbar. Open any dApp (e.g. Uniswap or OpenSea) and the Pop-Up Shield will protect your transactions across all tabs!
            </span>
          </div>
        </div>
      </Card>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        <div>
          {saveSuccess && (
            <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
              ✓ Preferences saved successfully!
            </span>
          )}
        </div>
        <button
          onClick={handleSaveSettings}
          className="px-6 py-2.5 bg-brand hover:bg-brand-light text-white text-sm font-semibold rounded-lg shadow transition-colors"
        >
          Save All Settings
        </button>
      </div>
    </div>
  );
}


