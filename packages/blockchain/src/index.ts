/**
 * Frontend-side blockchain helpers (wallet connect, chain metadata).
 *
 * Phase 1 placeholder. The actual BlockchainProvider abstraction (section 9
 * of the product spec — get_balance, get_transaction, call, estimate_gas,
 * etc.) lives server-side in apps/api and is added in Phase 2; this package
 * will hold thin frontend-only helpers (e.g. wallet connection UX), not RPC
 * logic itself.
 */
export const SUPPORTED_CHAINS = ["base-sepolia"] as const;
