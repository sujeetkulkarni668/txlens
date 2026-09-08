"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { getWallet, listPolicies, TxLensApiError } from "@/lib/api";
import { getConnectedAddress, onAccountsChanged } from "@/lib/wallet";
import type { Policy, WalletResponse } from "@txlens/shared-types";

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
        <h1 className="text-xl font-semibold tracking-tight text-ink">Dashboard</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Verify a transaction before you sign it, or review your configured policies.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <Card>
          <CardHeader title="Wallet" subtitle={address ? "Connected wallet details" : "Connect or inspect a public address"} />
          {!address && (
            <div className="space-y-3">
              <p className="text-sm text-ink-muted">Connect your browser wallet or enter any EVM address to inspect:</p>
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
                    View
                  </Button>
                </Link>
              </div>
            </div>
          )}
          {(address || lookupAddress) && !wallet && !walletError && (
            <p className="text-sm text-ink-muted">Loading on-chain data…</p>
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
                <dt className="text-ink-muted">Chain</dt>
                <dd className="text-ink">{wallet.chain}</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Balance</dt>
                <dd className="font-mono text-ink">{wallet.balance_wei} wei</dd>
              </div>
              <div className="flex justify-between">
                <dt className="text-ink-muted">Transaction count</dt>
                <dd className="text-ink">{wallet.transaction_count}</dd>
              </div>
            </dl>
          )}
        </Card>

        <Card>
          <CardHeader title="Policies" subtitle="Active security policies on your account" />
          {policiesError && <p className="text-sm text-danger">{policiesError}</p>}
          {!policies && !policiesError && <p className="text-sm text-ink-muted">Loading…</p>}
          {policies && policies.length === 0 && (
            <p className="text-sm text-ink-muted">No policies configured yet.</p>
          )}
          {policies && policies.length > 0 && (
            <ul className="space-y-1 text-sm text-ink">
              {policies.map((p) => (
                <li key={p.id} className="flex justify-between">
                  <span>{p.name}</span>
                  <span className="text-ink-muted">{p.rule_type}</span>
                </li>
              ))}
            </ul>
          )}
          <div className="mt-4">
            <Link href="/policies">
              <Button variant="secondary">Manage policies</Button>
            </Link>
          </div>
        </Card>

        <Card>
          <CardHeader title="Recent analyses" />
          <p className="text-sm text-ink-muted">
            Not available yet — there is no analysis-history endpoint in this build. Every
            analysis today is a one-off request; see{" "}
            <Link href="/analyze" className="underline">
              Transaction Analysis
            </Link>
            .
          </p>
        </Card>

        <Card>
          <CardHeader title="Recent alerts" />
          <p className="text-sm text-ink-muted">
            Not available yet — alerting requires persisted analysis history, which isn&apos;t
            implemented in this build.
          </p>
        </Card>
      </div>

      <div>
        <Link href="/analyze">
          <Button variant="primary">Analyze a transaction</Button>
        </Link>
      </div>
    </div>
  );
}
