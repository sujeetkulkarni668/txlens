"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { getWallet, listPolicies, TxLensApiError } from "@/lib/api";
import { getConnectedAddress, onAccountsChanged } from "@/lib/wallet";
import type { Policy, WalletResponse } from "@txlens/shared-types";

function weiToEthDisplay(weiStr: string): string {
  try {
    const clean = weiStr.trim();
    if (!clean || clean === "0") return "0.0 ETH";
    const b = BigInt(clean);
    const whole = b / BigInt(10 ** 18);
    const frac = (b % BigInt(10 ** 18)).toString().padStart(18, "0").slice(0, 4);
    return `${whole}.${frac} ETH`;
  } catch {
    return `${weiStr} wei`;
  }
}

export default function DashboardPage() {
  const [address, setAddress] = useState<string | null>(null);
  const [wallet, setWallet] = useState<WalletResponse | null>(null);
  const [walletError, setWalletError] = useState<string | null>(null);
  const [policies, setPolicies] = useState<Policy[] | null>(null);
  const [policiesError, setPoliciesError] = useState<string | null>(null);

  const [lookupAddress, setLookupAddress] = useState("");

  useEffect(() => {
    getConnectedAddress().then(setAddress).catch(() => {});
    return onAccountsChanged((accounts) => setAddress(accounts[0] ?? null));
  }, []);

  useEffect(() => {
    const target = address || (lookupAddress.trim().startsWith("0x") && lookupAddress.trim().length === 42 ? lookupAddress.trim() : null);
    if (!target) {
      setWallet(null);
      setWalletError(null);
      return;
    }
    setWalletError(null);
    getWallet(target)
      .then(setWallet)
      .catch((err) => setWalletError(err instanceof TxLensApiError ? err.message : "Could not load wallet"));
  }, [address, lookupAddress]);

  useEffect(() => {
    listPolicies()
      .then(setPolicies)
      .catch((err) => setPoliciesError(err instanceof TxLensApiError ? err.message : "Could not load policies"));
  }, []);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Your command center for transaction simulations, automated safety audits, and spending guardrails.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader title="Wallet Overview" subtitle={address ? "Connected wallet details" : "Connect your wallet or search an address"} />
          {!address && (
            <div className="space-y-3">
              <p className="text-sm text-ink-muted">Connect your browser wallet or enter any public address to inspect:</p>
              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="0x…"
                  className="flex-1 rounded-md border border-border bg-surface px-3 py-1.5 font-mono text-sm text-ink"
                  value={lookupAddress}
                  onChange={(e) => setLookupAddress(e.target.value)}
                />
                <Link href={lookupAddress.startsWith("0x") ? `/wallet/${lookupAddress}` : "#"}>
                  <Button variant="secondary" size="sm" disabled={!lookupAddress.startsWith("0x")}>
                    Inspect
                  </Button>
                </Link>
              </div>
            </div>
          )}
          {(address || lookupAddress) && !wallet && !walletError && (
            <p className="text-sm text-ink-muted">Loading wallet details…</p>
          )}
          {walletError && <p className="mt-2 text-sm text-danger">{walletError}</p>}
          {wallet && (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between">
                <dt className="text-ink-muted">Address</dt>
                <dd className="font-mono text-ink">
                  <Link href={`/wallet/${wallet.address}`} className="underline hover:text-ink/80">
                    {wallet.address.slice(0, 8)}…{wallet.address.slice(-6)}
                  </Link>
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Network</dt>
                <dd className="text-ink">{wallet.chain}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Balance</dt>
                <dd className="font-semibold text-ink">
                  {weiToEthDisplay(wallet.balance_wei)}
                </dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Completed Transactions</dt>
                <dd className="text-ink">{wallet.transaction_count}</dd>
              </div>
            </dl>
          )}
        </Card>

        <Card>
          <CardHeader title="Safety Policies" subtitle="Deterministic security guardrails protecting your wallet" />
          {policiesError && <p className="text-sm text-danger">{policiesError}</p>}
          {!policies && !policiesError && <p className="text-sm text-ink-muted">Loading policies…</p>}
          {policies && policies.length === 0 && (
            <p className="text-sm text-ink-muted">No custom policies configured yet. Standard rules active.</p>
          )}
          {policies && policies.length > 0 && (
            <ul className="space-y-2 text-sm text-ink">
              {policies.map((p) => (
                <li key={p.id} className="flex items-center justify-between rounded border border-border/50 bg-surface-muted/30 px-3 py-1.5">
                  <span className="font-medium">{p.name}</span>
                  <span className="text-xs text-ink-muted">{p.rule_type.replace(/_/g, " ")}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Link href="/policies">
              <Button variant="secondary">Manage Guardrails</Button>
            </Link>
          </div>
        </Card>
      </div>

      <div className="flex items-center gap-4">
        <Link href="/analyze">
          <Button variant="primary" size="lg">Inspect &amp; Verify a Transaction</Button>
        </Link>
        <Link href="/policies">
          <Button variant="secondary" size="lg">Configure Safety Guardrails</Button>
        </Link>
      </div>
    </div>
  );
}
