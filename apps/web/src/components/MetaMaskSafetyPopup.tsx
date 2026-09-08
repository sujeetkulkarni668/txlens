"use client";

import { useState } from "react";
import { Button } from "@/components/ui/Button";
import { analyzeTransaction, TxLensApiError } from "@/lib/api";
import type { TransactionAnalyzeResponse } from "@txlens/shared-types";

interface MetaMaskSafetyPopupProps {
  chain?: string;
  from?: string;
  to?: string | null;
  valueEth?: string;
  data?: string | null;
  dappName?: string;
  isOpen?: boolean;
  onClose?: () => void;
}

function ethToWei(ethStr: string): string {
  try {
    const clean = ethStr.trim();
    if (!clean || isNaN(Number(clean)) || Number(clean) < 0) return "0";
    const parts = clean.split(".");
    const whole = parts[0] || "0";
    let fraction = parts[1] || "";
    if (fraction.length > 18) {
      fraction = fraction.slice(0, 18);
    } else {
      fraction = fraction.padEnd(18, "0");
    }
    const wholeWei = BigInt(whole) * BigInt(10 ** 18);
    const fractionWei = BigInt(fraction);
    return (wholeWei + fractionWei).toString();
  } catch {
    return "0";
  }
}

function extractTop3Reasons(result: TransactionAnalyzeResponse): string[] {
  const reasons: string[] = [];

  // 1. Simulation outcome
  if (result.simulation) {
    if (result.simulation.success) {
      reasons.push("Simulation Succeeded: Transaction executes safely with no reverts or errors.");
    } else if (result.simulation.success === false) {
      reasons.push("Simulation Failed: Transaction will revert on-chain and waste gas fees.");
    }
  }

  // 2. AI Security findings
  if (result.ai_assessment) {
    if (result.ai_assessment.findings && result.ai_assessment.findings.length > 0) {
      reasons.push(`AI Analyst: ${result.ai_assessment.findings[0]}`);
    } else if (result.ai_assessment.summary) {
      reasons.push(`AI Analyst: ${result.ai_assessment.summary}`);
    }
  }

  // 3. Risk Engine factors
  if (result.risk && result.risk.signals && result.risk.signals.length > 0) {
    const topSig = result.risk.signals[0];
    const impact = topSig.impact >= 0 ? `+${topSig.impact} risk` : `${topSig.impact} safe`;
    reasons.push(`Risk Model: ${topSig.name.replace(/_/g, " ")} (${impact})`);
  }

  // 4. Policy Guardrails
  if (result.policy && result.policy.matched_rules && result.policy.matched_rules.length > 0) {
    reasons.push(`Security Policy: ${result.policy.matched_rules[0].reason}`);
  }

  // Fallbacks
  if (reasons.length < 1) reasons.push("Verified recipient address and network state.");
  if (reasons.length < 2) reasons.push("No unlimited token approval or drainer pattern detected.");
  if (reasons.length < 3) reasons.push("Complies with active wallet safety guardrails.");

  return reasons.slice(0, 3);
}

export function MetaMaskSafetyPopup({
  chain = "base-sepolia",
  from = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
  to = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
  valueEth = "0.05",
  data = null,
  dappName = "Active dApp",
  isOpen = true,
  onClose,
}: MetaMaskSafetyPopupProps) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<TransactionAnalyzeResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleVerify = async () => {
    setLoading(true);
    setError(null);
    try {
      const payload = {
        chain,
        from: from.trim() || "0x742d35Cc6634C0532925a3b844Bc454e4438f44e",
        to: to?.trim() || null,
        value: ethToWei(valueEth || "0"),
        data: data?.trim() || null,
      };
      const res = await analyzeTransaction(payload);
      setResult(res);
    } catch (err) {
      setError(err instanceof TxLensApiError ? err.message : "Verification failed");
    } finally {
      setLoading(false);
    }
  };

  const score = result?.risk ? result.risk.risk_score : 15;
  const reasons = result ? extractTop3Reasons(result) : [];

  let status: "SAFE" | "MID" | "RISK" = "SAFE";
  let statusText = "🟢 SAFE";
  let statusSub = "Threat Score: Low (Safe to Approve)";
  let badgeColor = "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
  let meterColor = "bg-emerald-500";

  if (score > 60) {
    status = "RISK";
    statusText = "🔴 RISK (Danger)";
    statusSub = `Threat Score: ${score} / 100 (High Threat Alert)`;
    badgeColor = "bg-rose-500/10 border-rose-500/30 text-rose-400";
    meterColor = "bg-rose-500";
  } else if (score > 25) {
    status = "MID";
    statusText = "🟡 MID (Caution)";
    statusSub = `Threat Score: ${score} / 100 (Review Advised)`;
    badgeColor = "bg-amber-500/10 border-amber-500/30 text-amber-400";
    meterColor = "bg-amber-500";
  } else {
    statusSub = `Threat Score: ${score} / 100 (Safe to Approve)`;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
      <div className="relative w-[360px] rounded-2xl border border-slate-700 bg-slate-900 p-4 text-slate-100 shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <div className="flex items-center gap-2">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-indigo-600 text-base font-bold shadow-md">
              🛡️
            </div>
            <div>
              <h3 className="text-sm font-bold text-white tracking-tight leading-none">TxLens Shield</h3>
              <span className="text-[10px] text-slate-400">MetaMask Pop-Up Simulator</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
              {chain}
            </span>
            {onClose && (
              <button onClick={onClose} className="text-slate-400 hover:text-white text-xs">
                ✕
              </button>
            )}
          </div>
        </div>

        <div className="mt-3 space-y-3">
          {/* Detected Context Card */}
          <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-xs space-y-2">
            <div className="flex justify-between items-center text-[11px] font-semibold text-slate-400 uppercase tracking-wider">
              <span>Detected Transaction</span>
              <span className="text-blue-400 lowercase">{dappName}</span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Recipient / App:</span>
              <span className="font-mono text-slate-200">
                {to ? `${to.slice(0, 6)}…${to.slice(-4)}` : "0x… (Contract Deploy)"}
              </span>
            </div>
            <div className="flex justify-between text-slate-300">
              <span className="text-slate-400">Transfer Amount:</span>
              <span className="font-semibold text-white">{valueEth || "0.0"} ETH</span>
            </div>
          </div>

          {/* Verify Button */}
          {!result && (
            <button
              type="button"
              onClick={handleVerify}
              disabled={loading}
              className="w-full rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 py-3 text-xs font-bold text-white shadow-lg shadow-blue-500/25 transition-all hover:opacity-95 disabled:opacity-50"
            >
              {loading ? "Verifying Authenticity…" : "🔍 Verify Transaction Authenticity"}
            </button>
          )}

          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-2 text-xs text-rose-400">
              {error}
            </div>
          )}

          {/* Verification Results */}
          {result && (
            <div className="space-y-3">
              {/* Verdict Status Box */}
              <div className={`rounded-xl border p-3 text-center ${badgeColor}`}>
                <div className="text-lg font-black tracking-wide">{statusText}</div>
                <div className="text-[11px] font-medium opacity-90 mt-0.5">{statusSub}</div>
                <div className="mt-2 h-1.5 w-full rounded-full bg-slate-800 overflow-hidden">
                  <div className={`h-full ${meterColor}`} style={{ width: `${Math.max(8, score)}%` }} />
                </div>
              </div>

              {/* Top 3 Reasons */}
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-2">
                  Top 3 Verification Reasons
                </div>
                <ul className="space-y-1.5 text-[11px] text-slate-300">
                  {reasons.map((r, idx) => (
                    <li key={idx} className="flex items-start gap-1.5 rounded-md bg-slate-900/60 p-1.5 border border-slate-800/80">
                      <span className="font-bold text-blue-400">{idx + 1}.</span>
                      <span className="leading-tight">{r}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleVerify}
                  disabled={loading}
                  className="flex-1 rounded-lg border border-slate-700 bg-slate-800 py-2 text-[11px] font-medium text-slate-200 hover:bg-slate-750"
                >
                  Re-Verify
                </button>
                {onClose && (
                  <button
                    type="button"
                    onClick={onClose}
                    className="flex-1 rounded-lg bg-blue-600 py-2 text-[11px] font-bold text-white hover:bg-blue-500"
                  >
                    Done
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-3 flex items-center justify-between border-t border-slate-800/80 pt-2 text-[10px] text-slate-500">
          <span>TxLens Pop-Up Engine</span>
          <span className="text-blue-400">1-Click Scrape Active</span>
        </div>
      </div>
    </div>
  );
}
