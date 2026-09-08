/**
 * Typed fetch client for the TxLens backend API.
 *
 * NOT executed against a live backend in the environment that generated
 * this repo (no `npm install`, no network) — see README limitations.
 * Every function here is a thin, direct mapping onto a real endpoint
 * built in earlier phases; nothing here calls an endpoint that doesn't
 * exist.
 */
import type {
  ContractResponse,
  Policy,
  PolicyCreateInput,
  TokenResponse,
  TransactionAnalyzeResponse,
  TransactionInput,
  WalletResponse,
} from "@txlens/shared-types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export class TxLensApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "TxLensApiError";
  }
}

let memoryToken: string | null = null;

export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    return localStorage.getItem("txlens_bearer_token") ?? memoryToken;
  }
  return memoryToken;
}

export function setAuthToken(token: string | null): void {
  memoryToken = token;
  if (typeof window !== "undefined") {
    if (token) {
      localStorage.setItem("txlens_bearer_token", token);
    } else {
      localStorage.removeItem("txlens_bearer_token");
    }
  }
}

export function clearAuthToken(): void {
  setAuthToken(null);
}

let authInitPromise: Promise<string> | null = null;

export async function ensureAuthToken(): Promise<string> {
  const existing = getAuthToken();
  if (existing) return existing;
  if (authInitPromise) return authInitPromise;

  authInitPromise = (async () => {
    try {
      const guestId = Math.random().toString(36).substring(2, 10);
      const email = `guest-${guestId}@txlens.local`;
      const password = `TxLensPass-${guestId}!123`;
      await register({ email, password });
      const res = await login({ email, password });
      setAuthToken(res.access_token);
      return res.access_token;
    } catch {
      return "";
    } finally {
      authInitPromise = null;
    }
  })();

  return authInitPromise;
}

async function request<T>(path: string, init?: RequestInit, isRetry = false): Promise<T> {
  let token = getAuthToken();
  if (!token && !path.startsWith("/auth/")) {
    token = await ensureAuthToken();
  }
  const authHeaders: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {};
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...(init?.headers ?? {}),
    },
  });

  if (response.status === 401 && !isRetry && !path.startsWith("/auth/")) {
    clearAuthToken();
    const freshToken = await ensureAuthToken();
    if (freshToken) {
      return request<T>(path, init, true);
    }
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = body?.detail ?? detail;
    } catch {
      // response body wasn't JSON — fall back to statusText
    }
    throw new TxLensApiError(response.status, detail);
  }

  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export function login(credentials: { email: string; password: string }): Promise<{ access_token: string; expires_in: number }> {
  return request("/auth/login", { method: "POST", body: JSON.stringify(credentials) });
}

export function register(credentials: { email: string; password: string }): Promise<{ id: string; email: string; is_active: boolean }> {
  return request("/auth/register", { method: "POST", body: JSON.stringify(credentials) });
}

export function analyzeTransaction(tx: TransactionInput): Promise<TransactionAnalyzeResponse> {
  return request("/transactions/analyze", { method: "POST", body: JSON.stringify(tx) });
}

export function simulateTransaction(tx: TransactionInput): Promise<TransactionAnalyzeResponse["simulation"]> {
  return request("/transactions/simulate", { method: "POST", body: JSON.stringify(tx) });
}

export function getWallet(address: string): Promise<WalletResponse> {
  return request(`/wallets/${address}`);
}

export function getContract(address: string): Promise<ContractResponse> {
  return request(`/contracts/${address}`);
}

export function getToken(address: string): Promise<TokenResponse> {
  return request(`/tokens/${address}`);
}

export function listPolicies(): Promise<Policy[]> {
  return request("/policies");
}

export function createPolicy(policy: PolicyCreateInput): Promise<Policy> {
  return request("/policies", { method: "POST", body: JSON.stringify(policy) });
}

export function deletePolicy(id: string): Promise<void> {
  return request(`/policies/${id}`, { method: "DELETE" });
}

export function updatePolicy(id: string, policy: Partial<PolicyCreateInput>): Promise<Policy> {
  return request(`/policies/${id}`, { method: "PUT", body: JSON.stringify(policy) });
}
