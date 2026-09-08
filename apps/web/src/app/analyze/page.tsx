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
import { TxLensSafetyPopup } from "@/components/TxLensSafetyPopup";

import type { TransactionAnalyzeResponse } from "@txlens/shared-types";


interface AnalyzedTxPayload {
  chain: string;
  from: string;
  to: string | null;
  value: string;
  data: string | null;
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

function weiToEth(weiStr: string): string {
  try {
    const clean = weiStr.trim();
    if (!clean || clean === "0") return "0";
    const b = BigInt(clean);
    const whole = b / BigInt(10 ** 18);
    const frac = (b % BigInt(10 ** 18)).toString().padStart(18, "0").replace(/0+$/, "");
    return frac.length > 0 ? `${whole}.${frac}` : whole.toString();
  } catch {
    return "0";
  }
}

export default function AnalyzePage() {
  const [txCategory, setTxCategory] = useState<"payment" | "contract">("payment");
  const [chain, setChain] = useState("base-sepolia");
  const [fromAddress, setFromAddress] = useState("");
  const [toAddress, setToAddress] = useState("");
  const [amountEth, setAmountEth] = useState("0");
  const [actionData, setActionData] = useState("");

  const [connectedAddress, setConnectedAddress] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TransactionAnalyzeResponse | null>(null);
  const [analyzedTx, setAnalyzedTx] = useState<AnalyzedTxPayload | null>(null);
  const [signStatus, setSignStatus] = useState<string | null>(null);
  const [isStale, setIsStale] = useState(false);
  const [showPopupModal, setShowPopupModal] = useState(false);


  useEffect(() => {
    getConnectedAddress().then((addr) => {
      setConnectedAddress(addr);
      if (addr) {
        setFromAddress((prev) => (prev ? prev : addr));
      }
    }).catch(() => {});

    const unsubAccounts = onAccountsChanged((accounts) => {
      const newAddr = accounts[0] ?? null;
      setConnectedAddress(newAddr);
      if (newAddr) {
        setFromAddress(newAddr);
      }
      setResult(null);
      setAnalyzedTx(null);
      setIsStale(false);
      setSignStatus(newAddr ? "Wallet account changed. Please re-analyze before signing." : null);
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

  const markStaleIfChanged = () => {
    if (analyzedTx) {
      const currentWei = ethToWei(amountEth);
      const changed =
        chain !== analyzedTx.chain ||
        fromAddress.trim().toLowerCase() !== analyzedTx.from.toLowerCase() ||
        (toAddress.trim() || null) !== analyzedTx.to ||
        currentWei !== analyzedTx.value ||
        (txCategory === "contract" ? (actionData.trim() || null) : null) !== analyzedTx.data;
      setIsStale(changed);
    }
  };

  const handleUseConnected = async () => {
    try {
      const addr = (await getConnectedAddress()) ?? (await connectWallet());
      setConnectedAddress(addr);
      setFromAddress(addr);
      markStaleIfChanged();
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
      let from = fromAddress.trim();
      if (!from) {
        from = (await getConnectedAddress()) ?? (await connectWallet());
        setFromAddress(from);
      }
      if (!from) {
        throw new Error("Please specify your wallet address or click 'Use connected wallet'.");
      }

      const calculatedWei = ethToWei(amountEth);
      const dataPayload = txCategory === "contract" && actionData.trim() ? actionData.trim() : null;

      const txPayload: AnalyzedTxPayload = {
        chain,
        from,
        to: toAddress.trim() ? toAddress.trim() : null,
        value: calculatedWei,
        data: dataPayload,
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
            : "Analysis failed. Please check network connection."
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
      setSignStatus("Warning: Form details changed after analysis. Please re-analyze before signing.");
      return;
    }
    setSignStatus(null);
    try {
      const currentFrom = (await getConnectedAddress()) ?? (await connectWallet());
      if (currentFrom.toLowerCase() !== analyzedTx.from.toLowerCase()) {
        setSignStatus(
          `Connected wallet (${currentFrom.slice(0, 6)}…${currentFrom.slice(-4)}) does not match analyzed sender (${analyzedTx.from.slice(0, 6)}…${analyzedTx.from.slice(-4)}). Switch account or re-analyze.`
        );
        return;
      }
      const hash = await sendTransaction({
        from: analyzedTx.from,
        to: analyzedTx.to || undefined,
        value: analyzedTx.value,
        data: analyzedTx.data || undefined,
      });
      setSignStatus(`Success! Transaction approved & broadcast. Hash: ${hash}`);
    } catch (err: unknown) {
      setSignStatus(err instanceof Error ? `Signing failed: ${err.message}` : "Signing failed.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-ink">Transaction Safety Shield</h1>
          <p className="mt-1 text-sm text-ink-muted">
            Simulate, inspect, and verify what any transfer or smart contract action will do before you sign it in your wallet.
          </p>
        </div>
        <Button
          variant="secondary"
          size="md"
          type="button"
          onClick={() => setShowPopupModal(true)}
          className="border-primary/40 bg-primary/5 hover:bg-primary/10 text-primary font-semibold shadow-sm"
        >
          🛡️ Pop-Up Shield Preview
        </Button>

      </div>

      {/* Interactive Pop-up Simulator Modal */}
      {showPopupModal && (
        <TxLensSafetyPopup
          chain={chain}
          from={fromAddress}
          to={toAddress}
          valueEth={amountEth}
          data={txCategory === "contract" ? actionData : null}
          dappName="TxLens Web Simulator"
          isOpen={showPopupModal}
          onClose={() => setShowPopupModal(false)}
        />
      )}


      {/* Main Analysis Form */}
      <Card>

        {/* Transaction Type Tabs */}
        <div className="mb-6">
          <label className="mb-2 block text-xs font-semibold uppercase tracking-wider text-ink-muted">
            1. Select Transaction Type
          </label>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <button
              type="button"
              onClick={() => {
                setTxCategory("payment");
                setActionData("");
                markStaleIfChanged();
              }}
              className={`flex flex-col items-start rounded-lg border p-4 text-left transition-all ${
                txCategory === "payment"
                  ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary"
                  : "border-border bg-surface hover:border-border-strong hover:bg-surface-muted/40"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  💸
                </span>
                <span className="font-semibold text-ink">Direct Payment / Transfer</span>
              </div>
              <p className="mt-1 text-xs text-ink-muted">
                Send ETH or native crypto directly to a friend, family member, or exchange wallet.
              </p>
            </button>

            <button
              type="button"
              onClick={() => {
                setTxCategory("contract");
                markStaleIfChanged();
              }}
              className={`flex flex-col items-start rounded-lg border p-4 text-left transition-all ${
                txCategory === "contract"
                  ? "border-primary bg-primary/5 shadow-sm ring-1 ring-primary"
                  : "border-border bg-surface hover:border-border-strong hover:bg-surface-muted/40"
              }`}
            >
              <div className="flex items-center gap-2">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/10 text-xs font-bold text-primary">
                  ⚡
                </span>
                <span className="font-semibold text-ink">Smart Contract / App Action</span>
              </div>
              <p className="mt-1 text-xs text-ink-muted">
                DEX swap, NFT mint, staking, token approvals, or interacting with decentralized apps.
              </p>
            </button>
          </div>
        </div>

        {/* Input Form Fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block text-xs font-semibold uppercase tracking-wider text-ink-muted">
            2. Enter Transaction Details
          </label>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {/* Network Selector */}
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">Blockchain Network</span>
              <select
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                value={chain}
                onChange={(e) => {
                  setChain(e.target.value);
                  markStaleIfChanged();
                }}
              >
                <option value="base-sepolia">Base Sepolia (Testnet)</option>
                <option value="base">Base Mainnet</option>
                <option value="ethereum">Ethereum Mainnet</option>
                <option value="sepolia">Sepolia Testnet</option>
                <option value="arbitrum">Arbitrum One</option>
                <option value="optimism">OP Mainnet</option>
                <option value="polygon">Polygon</option>
              </select>
            </label>

            {/* Sender / Your Wallet */}
            <label className="block text-sm">
              <div className="mb-1 flex items-center justify-between">
                <span className="font-medium text-ink">Sender (Your Wallet Address)</span>
                {connectedAddress ? (
                  <button
                    type="button"
                    onClick={() => {
                      setFromAddress(connectedAddress);
                      markStaleIfChanged();
                    }}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Use connected ({connectedAddress.slice(0, 6)}…{connectedAddress.slice(-4)})
                  </button>
                ) : (
                  <button
                    type="button"
                    onClick={handleUseConnected}
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Connect wallet
                  </button>
                )}
              </div>
              <input
                required
                className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-ink shadow-sm placeholder:text-ink-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="0x..."
                value={fromAddress}
                onChange={(e) => {
                  setFromAddress(e.target.value);
                  markStaleIfChanged();
                }}
              />
            </label>

            {/* Recipient or Contract Address */}
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">
                {txCategory === "payment" ? "Receiver (Destination Wallet Address)" : "Smart Contract / App Address"}
              </span>
              <input
                className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-sm text-ink shadow-sm placeholder:text-ink-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder={txCategory === "payment" ? "0x... (Recipient's 42-character address)" : "0x... (dApp contract address, or leave empty for contract deployment)"}
                value={toAddress}
                onChange={(e) => {
                  setToAddress(e.target.value);
                  markStaleIfChanged();
                }}
              />
              <span className="mt-1 block text-xs text-ink-muted">
                {txCategory === "payment"
                  ? "Where your funds will be delivered."
                  : "The verified smart contract you want to interact with."}
              </span>
            </label>

            {/* Amount in ETH */}
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">
                {txCategory === "payment" ? "Transfer Amount (in ETH)" : "Attached Value / Deposit (in ETH, optional)"}
              </span>
              <input
                type="text"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm text-ink shadow-sm placeholder:text-ink-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="0.0"
                value={amountEth}
                onChange={(e) => {
                  setAmountEth(e.target.value);
                  markStaleIfChanged();
                }}
              />
              <span className="mt-1 block text-xs text-ink-muted">
                {amountEth && !isNaN(Number(amountEth)) && Number(amountEth) > 0
                  ? `≈ ${Number(amountEth).toLocaleString()} ETH (${ethToWei(amountEth)} wei)`
                  : "Enter 0 if this transaction carries no ETH."}
              </span>
            </label>

            {/* Smart Contract Action Data Payload (Only shown in contract mode) */}
            {txCategory === "contract" && (
              <label className="block text-sm md:col-span-2">
                <span className="mb-1 block font-medium text-ink">Action Data / Payload</span>
                <textarea
                  rows={2}
                  className="w-full rounded-md border border-border bg-surface px-3 py-2 font-mono text-xs text-ink shadow-sm placeholder:text-ink-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                  placeholder="0x... (Optional: paste the action instructions supplied by your dApp)"
                  value={actionData}
                  onChange={(e) => {
                    setActionData(e.target.value);
                    markStaleIfChanged();
                  }}
                />
                <span className="mt-1 block text-xs text-ink-muted">
                  The compiled instructions telling the contract what function to trigger (swap, stake, mint, etc.).
                </span>
              </label>
            )}
          </div>

          <div className="pt-2">
            <Button type="submit" variant="primary" size="lg" disabled={loading}>
              {loading ? "Simulating & Analyzing…" : "Inspect & Verify Transaction"}
            </Button>
          </div>
        </form>
      </Card>

      {/* Error Card */}
      {error && (
        <Card className="border-danger/40 bg-danger/5">
          <div className="flex items-center gap-2 text-danger">
            <span className="text-base font-bold">⚠️</span>
            <p className="text-sm font-medium">{error}</p>
          </div>
        </Card>
      )}

      {/* Analysis Results */}
      {result && (
        <div className="space-y-6">
          {/* Stale Warning */}
          {isStale && (
            <Card className="border-warning/60 bg-warning/10">
              <p className="text-sm font-medium text-warning">
                ⚠️ Notice: You edited the form after running this analysis. Please re-run &quot;Inspect &amp; Verify Transaction&quot; before signing.
              </p>
            </Card>
          )}

          {/* AI Security Review */}
          <Card>
            <CardHeader
              title="AI Security Analyst Review"
              subtitle="Automated intelligent scan analyzing contract risk, drainer patterns, and safety"
            />
            {result.ai_assessment ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-3">
                  <DecisionBadge decision={result.ai_assessment.recommendation} />
                  <span className="font-medium text-ink">{result.ai_assessment.summary}</span>
                </div>
                <div className="rounded-md bg-surface-muted/50 p-3 text-ink-muted">
                  <p>{result.ai_assessment.risk_assessment}</p>
                </div>
                {result.ai_assessment.is_fallback && (
                  <p className="text-xs text-warning">
                    Standard heuristic safety checks applied.
                  </p>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">
                {result.pipeline_status.ai_analyst === "skipped_no_api_key"
                  ? "Standard rule engine active (AI analyst optional)."
                  : "Safety scan complete."}
              </p>
            )}
          </Card>

          {/* Safety Simulation Outcome */}
          <Card>
            <CardHeader
              title="Transaction Safety Simulation"
              subtitle="Simulated in a private sandbox without spending or risking real funds"
            />
            {result.simulation ? (
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2">
                  <span className="text-ink-muted">Execution Outcome:</span>
                  <span
                    className={`font-semibold ${
                      result.simulation.success
                        ? "text-success"
                        : result.simulation.success === false
                        ? "text-danger"
                        : "text-ink"
                    }`}
                  >
                    {result.simulation.success === null
                      ? "Unknown"
                      : result.simulation.success
                      ? "✓ Succeeded (Transaction will execute safely on-chain)"
                      : "✕ Would Fail / Revert (Transaction will fail or be rejected)"}
                  </span>
                </div>
                {result.simulation.gas_estimate && (
                  <p className="text-ink-muted">
                    Estimated Network Gas Units: <span className="font-mono text-ink">{result.simulation.gas_estimate}</span>
                  </p>
                )}
                {result.simulation.warnings.length > 0 && (
                  <div className="rounded-md border border-warning/30 bg-warning/5 p-3">
                    <span className="block font-medium text-warning">Safety Warnings:</span>
                    <ul className="mt-1 list-inside list-disc text-xs text-warning">
                      {result.simulation.warnings.map((w) => (
                        <li key={w}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">Simulation not available for this network.</p>
            )}
          </Card>

          {/* Overall Risk Score & Factors */}
          <Card>
            <CardHeader
              title="Risk Assessment & Safety Meter"
              subtitle="Machine-learning evaluated risk score (0 = Completely Safe, 100 = Critical Danger)"
            />
            {result.risk ? (
              <div>
                <div className="flex items-baseline gap-4">
                  <RiskBadge level={result.risk.risk_level} />
                  <span className="text-3xl font-bold text-ink">{result.risk.risk_score} / 100</span>
                </div>
                {result.risk.signals.length > 0 && (
                  <div className="mt-4 space-y-2">
                    <span className="text-xs font-semibold uppercase tracking-wider text-ink-muted">
                      Evaluated Factors:
                    </span>
                    <ul className="divide-y divide-border rounded-md border border-border bg-surface-muted/30 text-sm">
                      {result.risk.signals.map((s) => (
                        <li key={s.name} className="flex items-center justify-between px-3 py-2 text-ink">
                          <span>{s.name.replace(/_/g, " ")}</span>
                          <span className={s.impact >= 0 ? "font-semibold text-danger" : "font-semibold text-success"}>
                            {s.impact >= 0 ? `+${s.impact} risk` : `${s.impact} safe`}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">Risk scoring not available.</p>
            )}
          </Card>

          {/* Security Guardrails (Policy Engine) */}
          <Card>
            <CardHeader
              title="Security Guardrails & Spending Limits"
              subtitle="User-defined policy checks and protection rules"
            />
            {result.policy ? (
              <div className="space-y-3 text-sm">
                <DecisionBadge decision={result.policy.decision} />
                {result.policy.matched_rules.length > 0 ? (
                  <ul className="space-y-1">
                    {result.policy.matched_rules.map((r) => (
                      <li key={r.rule_name} className="text-ink-muted">
                        <strong className="text-ink">{r.rule_name.replace(/_/g, " ")}:</strong> {r.reason}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="text-ink-muted">All active safety guardrails passed successfully.</p>
                )}
              </div>
            ) : (
              <p className="text-sm text-ink-muted">No custom policies configured.</p>
            )}
          </Card>

          {/* Transaction Breakdown */}
          <Card>
            <CardHeader title="Transaction Breakdown" subtitle="Detailed action summary" />
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-xs text-ink-muted">Action Type</dt>
                <dd className="font-semibold text-ink">{result.parsed.tx_type}</dd>
              </div>
              <div>
                <dt className="text-xs text-ink-muted">Decode Status</dt>
                <dd className="text-ink">{result.parsed.decode_status}</dd>
              </div>
              {result.parsed.decoded_function && (
                <div className="col-span-2">
                  <dt className="text-xs text-ink-muted">Target Function</dt>
                  <dd className="font-mono text-sm text-ink">{result.parsed.decoded_function}</dd>
                </div>
              )}
            </dl>
            {result.parsed.notes.length > 0 && (
              <ul className="mt-3 list-inside list-disc text-xs text-ink-muted">
                {result.parsed.notes.map((n) => (
                  <li key={n}>{n}</li>
                ))}
              </ul>
            )}
          </Card>

          {/* Verification Banner */}
          {analyzedTx && (
            <Card className="border-border bg-surface-muted/50 p-4">
              <div className="flex flex-col gap-1 text-xs text-ink-muted">
                <span className="font-semibold text-ink">Verified Payload to Sign:</span>
                <div className="flex flex-wrap gap-x-4 gap-y-1 font-mono text-ink">
                  <span>To: {analyzedTx.to ?? "New Contract Creation"}</span>
                  <span>Value: {weiToEth(analyzedTx.value)} ETH ({analyzedTx.value} wei)</span>
                  <span>Network: {analyzedTx.chain}</span>
                </div>
              </div>
            </Card>
          )}

          {/* Action Buttons */}
          <div className="flex flex-wrap items-center gap-4">
            <Button
              variant="secondary"
              onClick={() => {
                setResult(null);
                setAnalyzedTx(null);
                setIsStale(false);
              }}
            >
              Reset
            </Button>
            <Button variant="primary" size="lg" onClick={handleContinue} disabled={isStale}>
              Approve &amp; Sign in Wallet
            </Button>
            {signStatus && (
              <span className="text-sm font-medium text-ink">
                {signStatus}
              </span>
            )}
          </div>
        </div>
      )}

      {/* Visual Usage Workflow Guide */}
      <Card className="border-border-strong/60 bg-gradient-to-br from-surface to-surface-muted/40 p-6">
        <div className="mb-6">
          <h2 className="text-lg font-bold tracking-tight text-ink">How TxLens Protects You</h2>
          <p className="text-sm text-ink-muted">
            A simple 4-step workflow that gives you complete clarity before you touch your funds.
          </p>
        </div>

        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          {/* Step 1 */}
          <div className="flex flex-col rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
              1
            </div>
            <h3 className="font-semibold text-ink">Choose &amp; Fill</h3>
            <p className="mt-1 text-xs text-ink-muted">
              Select whether you are sending a direct payment or interacting with a smart contract. Fill in the receiver and amount.
            </p>
          </div>

          {/* Step 2 */}
          <div className="flex flex-col rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
              2
            </div>
            <h3 className="font-semibold text-ink">Sandbox Dry-Run</h3>
            <p className="mt-1 text-xs text-ink-muted">
              TxLens simulates the transaction in an isolated sandbox to detect reverts, errors, and exact asset movements before anything happens.
            </p>
          </div>

          {/* Step 3 */}
          <div className="flex flex-col rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
              3
            </div>
            <h3 className="font-semibold text-ink">AI &amp; Safety Checks</h3>
            <p className="mt-1 text-xs text-ink-muted">
              Machine learning models, spending limit guardrails, and AI security analysts verify the contract reputation and flag scams or drainers.
            </p>
          </div>

          {/* Step 4 */}
          <div className="flex flex-col rounded-lg border border-border bg-surface p-4 shadow-sm">
            <div className="mb-3 flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 font-bold text-primary">
              4
            </div>
            <h3 className="font-semibold text-ink">Safe Execution</h3>
            <p className="mt-1 text-xs text-ink-muted">
              Once you review the clear outcome and green lights, approve the verified transaction with confidence in MetaMask or Rabby.
            </p>
          </div>
        </div>
      </Card>
    </div>
  );
}

