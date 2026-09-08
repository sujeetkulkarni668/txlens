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
  isMetaMask?: boolean;
  providers?: EIP1193Provider[];
}

declare global {
  interface Window {
    ethereum?: EIP1193Provider;
  }
}

export class NoWalletFoundError extends Error {
  constructor() {
    super("No EVM wallet extension detected. Please install MetaMask, Rabby, or Coinbase Wallet.");
    this.name = "NoWalletFoundError";
  }
}

export function getProvider(): EIP1193Provider {
  if (typeof window === "undefined" || !window.ethereum) {
    throw new NoWalletFoundError();
  }
  const eth = window.ethereum;
  if (Array.isArray(eth.providers) && eth.providers.length > 0) {
    const metaMask = eth.providers.find((p) => p.isMetaMask);
    return metaMask ?? eth.providers[0];
  }
  return eth;
}

/** Prompts the wallet's connect UI; returns the first connected address. */
export async function connectWallet(): Promise<string> {
  const provider = getProvider();
  try {
    const accounts = (await provider.request({ method: "eth_requestAccounts" })) as string[];
    if (!accounts || accounts.length === 0) {
      throw new Error("Wallet returned no accounts.");
    }
    return accounts[0];
  } catch (err: unknown) {
    const errorObj = err as { code?: number; message?: string };
    if (errorObj?.code === 4001) {
      throw new Error("Connection rejected by user in wallet.");
    }
    if (errorObj?.code === -32002) {
      throw new Error("Connection request already pending. Please open your wallet extension to approve.");
    }
    throw new Error(errorObj?.message ?? "Failed to connect wallet.");
  }
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

export async function getConnectedChainId(): Promise<number | null> {
  if (typeof window === "undefined" || !window.ethereum) return null;
  try {
    const chainIdHex = (await window.ethereum.request({ method: "eth_chainId" })) as string;
    return chainIdHex ? parseInt(chainIdHex, 16) : null;
  } catch {
    return null;
  }
}

export function onAccountsChanged(handler: (accounts: string[]) => void): () => void {
  if (typeof window === "undefined" || !window.ethereum?.on) {
    return () => {};
  }
  const listener = (...args: unknown[]) => handler(args[0] as string[]);
  window.ethereum.on("accountsChanged", listener);
  return () => window.ethereum?.removeListener?.("accountsChanged", listener);
}

export function onChainChanged(handler: (chainId: string) => void): () => void {
  if (typeof window === "undefined" || !window.ethereum?.on) {
    return () => {};
  }
  const listener = (...args: unknown[]) => handler(args[0] as string);
  window.ethereum.on("chainChanged", listener);
  return () => window.ethereum?.removeListener?.("chainChanged", listener);
}

export function onDisconnect(handler: () => void): () => void {
  if (typeof window === "undefined" || !window.ethereum?.on) {
    return () => {};
  }
  const listener = () => handler();
  window.ethereum.on("disconnect", listener);
  return () => window.ethereum?.removeListener?.("disconnect", listener);
}
