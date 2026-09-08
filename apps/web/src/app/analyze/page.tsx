"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { DecisionBadge, RiskBadge, StatusBadge } from "@/components/ui/Badge";
import { analyzeTransaction, TxLensApiError } from "@/lib/api";
import {
  connectWallet,
  getConnectedAddress,
  onAccountsChanged,
  onChainChanged,
  sendTransaction,
} from "@/lib/wallet";
import type { TransactionAnalyzeResponse } from "@txlens/shared-types";

interface AnalyzedTxPayload {
  chain: string;
  from: string;
  to: string | null;
  value: string;
  data: string | null;
}

const EMPTY_FORM = { chain: "base-sepolia", from: "", to: "", value: "0", data: "" };

export default function AnalyzePage() {
  const [form, setForm] = useState(EMPTY_FORM);
  const [connectedAddress, setConnectedAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TransactionAnalyzeResponse | null>(null);
  const [analyzedTx, setAnalyzedTx] = useState<AnalyzedTxPayload | null>(null);
  const [signStatus, setSignStatus] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);

  useEffect(() => {
    getConnectedAddress().then((addr) => {
      setConnectedAddress(addr);
      if (addr) {
        setForm((prev) => (prev.from ? prev : { ...prev, from: addr }));
      }
    }).catch(() => {});

    const unsubAccounts = onAccountsChanged((accounts) => {
      const newAddr = accounts[0] ?? null;
      setConnectedAddress(newAddr);
      if (newAddr) {
        setForm((prev) => ({ ...prev, from: newAddr }));
      }
      setResult(null);
      setAnalyzedTx(null);
      setIsStale(false);
      setSignStatus(newAddr ? "Account changed. Please re-analyze." : null);
    });
    const unsubChain = onChainChanged(() => {
      setResult(null);
      setAnalyzedTx(null);
      setIsStale(false);
      setSignStatus("Network changed. Please re-analyze.");
    });
    return () => {
      unsubAccounts();
      unsubChain();
    };
  }, []);

  const handleFormChange = (updated: typeof EMPTY_FORM) => {
    setForm(updated);
    if (analyzedTx) {
      const changed =
        updated.chain !== analyzedTx.chain ||
        (updated.from.trim().toLowerCase()) !== analyzedTx.from.toLowerCase() ||
        (updated.to || null) !== analyzedTx.to ||
        (updated.value || "0") !== analyzedTx.value ||
        (updated.data || null) !== analyzedTx.data;
      setIsStale(changed);
    }
  };

  const handleUseConnected = async () => {
    try {
      const addr = (await getConnectedAddress()) ?? (await connectWallet());
      setConnectedAddress(addr);
      setForm((prev) => ({ ...prev, from: addr }));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to connect wallet.");
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError(null);
    setResult(null);
    setAnalyzedTx(null);
    setIsStale(false);
    setSignStatus(null);
    setLoading(true);
    try {
      let from = form.from.trim();
      if (!from) {
        from = (await getConnectedAddress()) ?? (await connectWallet());
        setForm((prev) => ({ ...prev, from }));
      }
      if (!from) {
        throw new Error("Please specify a 'From' address or connect your wallet.");
      }
      const txPayload: AnalyzedTxPayload = {
        chain: form.chain,
        from,
        to: form.to ? form.to.trim() : null,
        value: form.value || "0",
        data: form.data ? form.data.trim() : null,
      };
      const analysis = await analyzeTransaction(txPayload);
      setResult(analysis);
      setAnalyzedTx(txPayload);
      setIsStale(false);
    } catch (err: unknown) {
      setError(
        err instanceof TxLensApiError
          ? err.message
          : err instanceof Error
            ? err.message
            : "Analysis failed. Please check backend status."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleContinue = async () => {
    if (!analyzedTx) {
      setSignStatus("Error: No valid analyzed transaction.");
      return;
    }
    if (isStale) {
      setSignStatus("Error: Form inputs have changed since analysis. Please re-analyze before signing.");
      return;
    }
    setSignStatus(null);
    try {
      const currentFrom = (await getConnectedAddress()) ?? (await connectWallet());
      if (currentFrom.toLowerCase() !== analyzedTx.from.toLowerCase()) {
        setSignStatus(`Connected wallet (${currentFrom.slice(0, 6)}…${currentFrom.slice(-4)}) does not match analyzed 'From' address (${analyzedTx.from.slice(0, 6)}…${analyzedTx.from.slice(-4)}). Please switch account or re-analyze.`);
        return;
      }
      // Exact analyzed transaction is sent to wallet, preventing TOCTOU substitution
      const hash = await sendTransaction({
        from: analyzedTx.from,
        to: analyzedTx.to || undefined,
        value: analyzedTx.value,
        data: analyzedTx.data || undefined,
      });
      setSignStatus(`Transaction submitted to network! Hash: ${hash}`);
    } catch (err: unknown) {
      setSignStatus(err instanceof Error ? `Signing failed: ${err.message}` : "Signing failed.");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Transaction Analysis</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Review what a transaction will do before your wallet signs it.
        </p>
      </div>

      <Card>
        <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <label className="block text-sm">
            <span className="mb-1 block text-ink-muted">Chain</span>
            <input
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink"
              value={form.chain}
              onChange={(e) => handleFormChange({ ...form, chain: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            <div className="mb-1 flex items-center justify-between">
              <span className="text-ink-muted">From (Sender Address)</span>
              {connectedAddress ? (
                <button
                  type="button"
                  onClick={() => setForm({ ...form, from: connectedAddress })}
                  className="text-xs text-ink underline hover:text-ink/80"
                >
                  Use connected ({connectedAddress.slice(0, 6)}…{connectedAddress.slice(-4)})
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleUseConnected}
                  className="text-xs text-ink underline hover:text-ink/80"
                >
                  Connect wallet
                </button>
              )}
            </div>
            <input
              required
              className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-ink"
              placeholder="0x…"
              value={form.from}
              onChange={(e) => handleFormChange({ ...form, from: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-ink-muted">To (Recipient / Contract)</span>
            <input
              className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-ink"
              placeholder="0x… (leave empty for contract deployment)"
              value={form.to}
              onChange={(e) => handleFormChange({ ...form, to: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-ink-muted">Value (wei)</span>
            <input
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink"
              value={form.value}
              onChange={(e) => handleFormChange({ ...form, value: e.target.value })}
            />
          </label>
          <label className="block text-sm md:col-span-2">
            <span className="mb-1 block text-ink-muted">Data (hex, optional calldata)</span>
            <input
              className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-ink"
              placeholder="0x…"
              value={form.data}
              onChange={(e) => handleFormChange({ ...form, data: e.target.value })}
            />
          </label>
          <div className="md:col-span-2">
            <Button type="submit" variant="primary" disabled={loading}>
              {loading ? "Analyzing…" : "Analyze"}
            </Button>
          </div>
        </form>
      </Card>

      {error && (
        <Card className="border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      {result && (
        <div className="space-y-6">
          {isStale && (
            <Card className="border-warning/60 bg-warning/10">
              <p className="text-sm font-medium text-warning">
                Warning: Form inputs have been modified since this analysis was generated.
                Please re-analyze the transaction before signing.
              </p>
            </Card>
          )}
          <Card>
            <CardHeader title="Risk" />
            {result.risk ? (
              <div className="flex items-baseline gap-4">
                <RiskBadge level={result.risk.risk_level} />
                <span className="text-2xl font-semibold text-ink">{result.risk.risk_score} / 100</span>
                {result.risk.model_is_demo_data && (
                  <span className="text-xs text-ink-muted">(demo model, synthetic training data)</span>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">Not available.</p>
            )}
            {result.risk && result.risk.signals.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm">
                {result.risk.signals.map((s) => (
                  <li key={s.name} className="flex justify-between text-ink">
                    <span>{s.name.replace(/_/g, " ")}</span>
                    <span className={s.impact >= 0 ? "text-danger" : "text-success"}>
                      {s.impact >= 0 ? "+" : ""}
                      {s.impact}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Parsed transaction" />
            <dl className="grid grid-cols-2 gap-2 text-sm">
              <dt className="text-ink-muted">Type</dt>
              <dd className="text-ink">{result.parsed.tx_type}</dd>
              <dt className="text-ink-muted">Decode status</dt>
              <dd className="text-ink">{result.parsed.decode_status}</dd>
              {result.parsed.decoded_function && (
                <>
                  <dt className="text-ink-muted">Function</dt>
                  <dd className="font-mono text-ink">{result.parsed.decoded_function}</dd>
                </>
              )}
            </dl>
            {result.parsed.notes.length > 0 && (
              <ul className="mt-3 list-inside list-disc text-sm text-ink-muted">
                {result.parsed.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            )}
          </Card>

          <Card>
            <CardHeader title="Simulation" />
            {result.simulation ? (
              <div className="space-y-2 text-sm">
                <p className="text-ink">
                  Outcome:{" "}
                  <span className="font-medium">
                    {result.simulation.success === null
                      ? "unknown"
                      : result.simulation.success
                        ? "would succeed"
                        : "would revert"}
                  </span>
                </p>
                {result.simulation.gas_estimate && (
                  <p className="text-ink-muted">Estimated gas: {result.simulation.gas_estimate}</p>
                )}
                <p className="text-ink-muted">
                  Internal-call trace: {result.simulation.trace_supported ? "supported" : "not supported by this RPC endpoint"}
                </p>
                {result.simulation.warnings.length > 0 && (
                  <ul className="list-inside list-disc text-warning">
                    {result.simulation.warnings.map((w) => (
                      <li key={w}>{w}</li>
                    ))}
                  </ul>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">Not available.</p>
            )}
          </Card>

          <Card>
            <CardHeader title="Policy" />
            {result.policy ? (
              <div className="space-y-2 text-sm">
                <DecisionBadge decision={result.policy.decision} />
                {result.policy.matched_rules.map((r) => (
                  <p key={r.rule_name} className="text-ink-muted">
                    {r.rule_name}: {r.reason}
                  </p>
                ))}
                {result.policy.unevaluated_rules.length > 0 && (
                  <p className="text-ink-muted">
                    {result.policy.unevaluated_rules.length} rule(s) could not be evaluated
                    (insufficient data).
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">No policies configured.</p>
            )}
          </Card>

          <Card>
            <CardHeader title="AI assessment" />
            {result.ai_assessment ? (
              <div className="space-y-2 text-sm">
                <DecisionBadge decision={result.ai_assessment.recommendation} />
                <p className="text-ink">{result.ai_assessment.summary}</p>
                <p className="text-ink-muted">{result.ai_assessment.risk_assessment}</p>
                {result.ai_assessment.is_fallback && (
                  <p className="text-warning">
                    This is a fallback result — the AI model&apos;s output could not be validated.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">
                {result.pipeline_status.ai_analyst === "skipped_no_api_key"
                  ? "Skipped — no AI provider is configured."
                  : "Not available."}
              </p>
            )}
          </Card>

          <Card>
            <CardHeader title="Pipeline status" />
            <div className="flex flex-wrap gap-2">
              {Object.entries(result.pipeline_status).map(([stage, status]) => (
                <div key={stage} className="flex items-center gap-2">
                  <span className="text-sm text-ink-muted">{stage}:</span>
                  <StatusBadge status={status} />
                </div>
              ))}
            </div>
          </Card>

          {analyzedTx && (
            <Card className="border-border bg-surface-muted/50 p-3">
              <p className="text-xs text-ink-muted">
                <span className="font-semibold text-ink">Signing payload verification:</span> To:{" "}
                <span className="font-mono text-ink">{analyzedTx.to ?? "(Contract creation)"}</span> | Value:{" "}
                <span className="font-mono text-ink">{analyzedTx.value} wei</span> | Chain:{" "}
                <span className="font-mono text-ink">{analyzedTx.chain}</span>
              </p>
            </Card>
          )}

          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={() => { setResult(null); setAnalyzedTx(null); setIsStale(false); }}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleContinue} disabled={isStale}>
              Continue — sign in wallet
            </Button>
            {signStatus && <span className="text-sm text-ink-muted">{signStatus}</span>}
          </div>
        </div>
      )}
    </div>
  );
}
