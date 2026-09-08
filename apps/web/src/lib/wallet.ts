/**
 * Thin wrapper around the browser's injected EIP-1193 wallet provider
 * (e.g. MetaMask) — deliberately dependency-free (no wagmi/viem/ethers)
 * so this works without any package install. TxLens never receives a
 * private key: every call here either reads public state or asks the
 * wallet to prompt the user, per product spec section 20.
 *
 * NOT exercised against a real wallet extension in the environment that
 * generated this repo (no browser here at all) — syntax-reviewed only.
 */

export interface EIP1193Provider {
  request: (args: { method: string; params?: unknown[] }) => Promise<unknown>;
  on?: (event: string, handler: (...args: unknown[]) => void) => void;
  removeListener?: (event: string, handler: (...args: unknown[]) => void) => void;
}

declare global {
  interface Window {
    ethereum?: EIP1193Provider;
  }
}

export class NoWalletFoundError extends Error {
  constructor() {
    super("No EVM wallet extension detected in this browser.");
    this.name = "NoWalletFoundError";
  }
}

function getProvider(): EIP1193Provider {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new NoWalletFoundError();
  }
  return window.ethereum;
}

/** Prompts the wallet's connect UI; returns the first connected address. */
export async function connectWallet(): Promise<string> {
  const provider = getProvider();
  const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
  if (!accounts || accounts.length === 0) {
    throw new Error("Wallet returned no accounts.");
  }
  return accounts[0];
}

/** Returns the currently connected address without prompting, or null. */
export async function getConnectedAddress(): Promise<string | null> {
  if (typeof window === "undefined" || !window.ethereum) return null;
  const accounts = (await window.ethereum.request({ method: "eth_accounts" })) as string[];
  return accounts?.[0] ?? null;
}

/**
 * Asks the wallet to sign and submit a transaction — the wallet remains
 * the sole signing authority (product spec section 20). Returns the
 * resulting transaction hash.
 */
export async function sendTransaction(tx: {
  from: string;
  to?: string;
  value?: string;
  data?: string;
}): Promise<string> {
  const provider = getProvider();
  const params: Record<string, string> = { from: tx.from };
  if (tx.to) params.to = tx.to;
  if (tx.value && tx.value !== "0") params.value = `0x${BigInt(tx.value).toString(16)}`;
  if (tx.data) params.data = tx.data;

  const txHash = (await provider.request({
    method: "eth_sendTransaction",
    params: [params],
  })) as string;
  return txHash;
}

export function onAccountsChanged(handler: (accounts: string[]) => void): () => void {
  if (typeof window === "undefined" || !window.ethereum?.on) {
    return () => {};
  }
  const listener = (...args: unknown[]) => handler(args[0] as string[]);
  window.ethereum.on("accountsChanged", listener);
  return () => window.ethereum?.removeListener?.("accountsChanged", listener);
}
