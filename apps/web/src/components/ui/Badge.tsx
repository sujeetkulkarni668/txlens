import type { PolicyDecision, RiskLevel } from "@txlens/shared-types";

const RISK_STYLES: Record<RiskLevel, string> = {
  LOW: "bg-success/10 text-success border-success/30",
  MEDIUM: "bg-warning/10 text-warning border-warning/30",
  HIGH: "bg-danger/10 text-danger border-danger/30",
  CRITICAL: "bg-danger/20 text-danger border-danger/50",
};

export function RiskBadge({ level }: { level: RiskLevel }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${RISK_STYLES[level]}`}
    >
      {level}
    </span>
  );
}

const DECISION_STYLES: Record<PolicyDecision, string> = {
  ALLOW: "bg-success/10 text-success border-success/30",
  REVIEW: "bg-warning/10 text-warning border-warning/30",
  BLOCK: "bg-danger/10 text-danger border-danger/30",
};

export function DecisionBadge({ decision }: { decision: PolicyDecision }) {
  return (
    <span
      className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${DECISION_STYLES[decision]}`}
    >
      {decision}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  const isComplete = status === "complete";
  const isSkipped = status.startsWith("skipped");
  const style = isComplete
    ? "bg-success/10 text-success border-success/30"
    : isSkipped
      ? "bg-surface-muted text-ink-muted border-border"
      : "bg-warning/10 text-warning border-warning/30";
  return (
    <span className={`inline-flex items-center rounded border px-2 py-0.5 text-xs font-medium ${style}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
