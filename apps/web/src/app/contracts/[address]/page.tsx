"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { getContract, getToken, TxLensApiError } from "@/lib/api";
import type { ContractResponse, TokenResponse } from "@txlens/shared-types";

export default function ContractPage({ params }: { params: { address: string } }) {
  const [contract, setContract] = useState<ContractResponse | null>(null);
  const [token, setToken] = useState<TokenResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getContract(params.address)
      .then(setContract)
      .catch((err) => setError(err instanceof TxLensApiError ? err.message : "Could not load contract"));
    getToken(params.address).then(setToken).catch(() => {
      // Not every contract is a token — a failed token read isn't an error worth surfacing.
    });
  }, [params.address]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Contract</h1>
        <p className="mt-1 break-all font-mono text-sm text-ink-muted">{params.address}</p>
      </div>

      {error && (
        <Card className="border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      {!contract && !error && <p className="text-sm text-ink-muted">Loading…</p>}

      {contract && (
        <Card>
          <CardHeader title="Verification status" />
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-ink-muted">Is contract</dt>
            <dd className="text-ink">{contract.is_contract ? "yes" : "no (externally-owned account)"}</dd>
            <dt className="text-ink-muted">Bytecode size</dt>
            <dd className="text-ink">{contract.bytecode_size_bytes} bytes</dd>
            <dt className="text-ink-muted">Source verified</dt>
            <dd className="text-ink">
              {contract.source_verified === null
                ? "unknown — not checked"
                : contract.source_verified
                  ? "yes"
                  : "no"}
            </dd>
          </dl>
          {contract.notes.length > 0 && (
            <ul className="mt-3 list-inside list-disc text-sm text-ink-muted">
              {contract.notes.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
        </Card>
      )}

      {token && token.symbol && (
        <Card>
          <CardHeader title="Token" />
          <dl className="grid grid-cols-2 gap-3 text-sm">
            <dt className="text-ink-muted">Symbol</dt>
            <dd className="text-ink">{token.symbol}</dd>
            <dt className="text-ink-muted">Name</dt>
            <dd className="text-ink">{token.name ?? "—"}</dd>
            <dt className="text-ink-muted">Decimals</dt>
            <dd className="text-ink">{token.decimals ?? "—"}</dd>
            <dt className="text-ink-muted">Total supply</dt>
            <dd className="text-ink">{token.total_supply ?? "—"}</dd>
          </dl>
        </Card>
      )}
    </div>
  );
}
