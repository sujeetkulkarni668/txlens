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
    } catch (err) {
      setError(err instanceof NoWalletFoundError ? "No wallet extension found." : "Connection failed.");
    } finally {
      setConnecting(false);
    }
  };

  if (address) {
    return (
      <span className="inline-flex items-center rounded-md border border-border bg-surface-muted px-3 py-1.5 text-sm font-medium text-ink">
        {shortAddress(address)}
      </span>
    );
  }

  return (
    <div className="flex items-center gap-2">
      {error && <span className="text-xs text-danger">{error}</span>}
      <Button variant="primary" onClick={handleConnect} disabled={connecting}>
        {connecting ? "Connecting…" : "Connect Wallet"}
      </Button>
    </div>
  );
}
