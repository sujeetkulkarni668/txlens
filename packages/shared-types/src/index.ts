/**
 * Shared TypeScript types mirroring backend Pydantic schemas
 * (apps/api/app/schemas/*.py). Kept in sync by hand — there is no
 * codegen step yet; if you change a backend schema, update this file
 * too.
 */

export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";

export type PolicyDecision = "ALLOW" | "REVIEW" | "BLOCK";

export type TransactionType =
  | "native_transfer"
  | "erc20_transfer"
  | "erc20_approval"
  | "contract_interaction"
  | "unknown";

export type DecodeStatus = "decoded" | "partially_decoded" | "undecoded";

export interface TransactionInput {
  chain?: string;
  from: string;
  to?: string | null;
  value?: string;
  data?: string | null;
}

export interface ParsedTransaction {
  tx_type: TransactionType;
  decode_status: DecodeStatus;
  decoded_function?: string | null;
  contract_address?: string | null;
  parameters?: Record<string, string> | null;
  token_amount?: string | null;
  spender?: string | null;
  recipient?: string | null;
  sender?: string | null;
  is_unlimited_approval: boolean;
  notes: string[];
}

export interface SimulationResult {
  success: boolean | null;
  gas_estimate: string | null;
  decoded_actions: Record<string, unknown>[];
  asset_changes: Record<string, unknown>[];
  approvals: Record<string, unknown>[];
  events: Record<string, unknown>[];
  warnings: string[];
  trace_supported: boolean | null;
}

export interface RiskSignal {
  name: string;
  impact: number;
}

export interface RiskAssessment {
  risk_score: number;
  risk_level: RiskLevel;
  signals: RiskSignal[];
  model_is_demo_data: boolean;
  model_version: string;
  model_confidence: number;
  notes: string[];
}

export interface RuleOutcome {
  rule_name: string;
  rule_type: string;
  decision: PolicyDecision | null;
  reason: string;
}

export interface PolicyEvaluation {
  decision: PolicyDecision;
  matched_rules: RuleOutcome[];
  unevaluated_rules: RuleOutcome[];
}

export interface AIAssessment {
  summary: string;
  risk_assessment: string;
  findings: string[];
  potential_impact: string[];
  recommendation: PolicyDecision;
  confidence: number;
  is_fallback: boolean;
  notes: string[];
}

export interface TransactionAnalyzeResponse {
  parsed: ParsedTransaction;
  simulation: SimulationResult | null;
  risk: RiskAssessment | null;
  policy: PolicyEvaluation | null;
  ai_assessment: AIAssessment | null;
  pipeline_status: Record<string, string>;
}

export interface WalletResponse {
  address: string;
  chain: string;
  balance_wei: string;
  transaction_count: number;
  note: string;
}

export interface ContractResponse {
  address: string;
  is_contract: boolean;
  bytecode_size_bytes: number;
  source_verified: boolean | null;
  abi: Record<string, unknown> | null;
  notes: string[];
}

export interface TokenResponse {
  address: string;
  is_contract: boolean;
  symbol: string | null;
  name: string | null;
  decimals: number | null;
  total_supply: string | null;
  notes: string[];
}

export type RuleType =
  | "maximum_transaction_value"
  | "maximum_daily_spend"
  | "require_review_above"
  | "block_unlimited_approvals"
  | "block_unknown_contracts"
  | "require_review_for_new_contracts";

export interface Policy {
  id: string;
  name: string;
  rule_type: RuleType;
  parameters: Record<string, number>;
  is_active: boolean;
}

export interface PolicyCreateInput {
  name: string;
  rule_type: RuleType;
  parameters: Record<string, number>;
  is_active?: boolean;
}

export const SUPPORTED_CHAINS = ["base-sepolia"] as const;
