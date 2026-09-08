"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/Button";
import { connectWallet, getConnectedAddress, NoWalletFoundError, onAccountsChanged } from "@/lib/wallet";

function shortAddress(address: string): string {
  return `${address.slice(0, 6)}…${address.slice(-4)}`;
}

export function WalletConnectButton() {
  const [address, setAddress] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [connecting, setConnecting] = useState(false);

  useEffect(() => {
    getConnectedAddress().then(setAddress).catch(() => {});
    return onAccountsChanged((accounts) => setAddress(accounts[0] ?? null));
  }, []);

  const handleConnect = async () => {
    setError(null);
    setConnecting(true);
    try {
      const connected = await connectWallet();
      setAddress(connected);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Connection failed.");
    } finally {
      setConnecting(false);
    }
  };

  const handleDisconnect = () => {
    setAddress(null);
    setError(null);
  };

  if (address) {
    return (
      <div className="flex items-center gap-2">
        <span
          className="inline-flex items-center rounded-md border border-border bg-surface-muted px-3 py-1.5 text-sm font-medium font-mono text-ink"
          title={address}
        >
          {shortAddress(address)}
        </span>
        <Button variant="secondary" size="sm" onClick={handleDisconnect}>
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {error && <span className="max-w-[200px] truncate text-xs text-danger" title={error}>{error}</span>}
      <Button variant="primary" onClick={handleConnect} disabled={connecting}>
        {connecting ? "Connecting…" : "Connect Wallet"}
      </Button>
    </div>
  );
}
