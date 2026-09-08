"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { getWallet, TxLensApiError } from "@/lib/api";
import type { WalletResponse } from "@txlens/shared-types";

export default function WalletPage({ params }: { params: { address: string } }) {
  const [wallet, setWallet] = useState<WalletResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getWallet(params.address)
      .then(setWallet)
      .catch((err) => setError(err instanceof TxLensApiError ? err.message : "Could not load wallet"));
  }, [params.address]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Wallet</h1>
        <p className="mt-1 break-all font-mono text-sm text-ink-muted">{params.address}</p>
      </div>

      {error && (
        <Card className="border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      {!wallet && !error && <p className="text-sm text-ink-muted">Loading…</p>}

      {wallet && (
        <Card>
          <CardHeader title="Public on-chain information" subtitle={wallet.note} />
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-ink-muted">Chain</dt>
            <dd className="text-ink">{wallet.chain}</dd>
            <dt className="text-ink-muted">Balance</dt>
            <dd className="text-ink">{wallet.balance_wei} wei</dd>
            <dt className="text-ink-muted">Transaction count</dt>
            <dd className="text-ink">{wallet.transaction_count}</dd>
          </dl>
        </Card>
      )}

      <Card>
        <CardHeader title="Risk signals" />
        <p className="text-sm text-ink-muted">
          Standalone wallet risk scoring is intentionally not offered without a specific
          transaction for context — see{" "}
          <a href="/analyze" className="underline">
            Transaction Analysis
          </a>
          .
        </p>
      </Card>
    </div>
  );
}
