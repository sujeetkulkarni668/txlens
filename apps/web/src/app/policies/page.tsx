"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { createPolicy, deletePolicy, listPolicies, TxLensApiError } from "@/lib/api";
import type { Policy, RuleType } from "@txlens/shared-types";

const RULE_TYPES: { value: RuleType; label: string; description: string; paramKey: string | null; paramLabel?: string; paramPlaceholder?: string }[] = [
  {
    value: "maximum_transaction_value",
    label: "Maximum Transfer Limit per Transaction",
    description: "Blocks any single transaction that attempts to send more than this amount.",
    paramKey: "max_value",
    paramLabel: "Maximum allowed value (in wei / native units)",
    paramPlaceholder: "e.g. 1000000000000000000 for 1 ETH",
  },
  {
    value: "maximum_daily_spend",
    label: "Daily Spend Budget Cap",
    description: "Sets a ceiling on total funds that can leave your wallet within a 24-hour period.",
    paramKey: "max_daily_spend",
    paramLabel: "Maximum daily limit (in wei / native units)",
    paramPlaceholder: "e.g. 5000000000000000000 for 5 ETH",
  },
  {
    value: "require_review_above",
    label: "Trigger Warning Above Threshold",
    description: "Raises a high-caution review alert if a transaction exceeds this value.",
    paramKey: "threshold",
    paramLabel: "Alert threshold value (in wei / native units)",
    paramPlaceholder: "e.g. 500000000000000000 for 0.5 ETH",
  },
  {
    value: "block_unlimited_approvals",
    label: "Block Unlimited Token Approvals (Anti-Drainer)",
    description: "Prevents contracts from requesting infinite access to your ERC-20 tokens.",
    paramKey: null,
  },
  {
    value: "block_unknown_contracts",
    label: "Block Unknown & Unverified Contracts",
    description: "Rejects transactions interacting with unverified or zero-reputation contracts.",
    paramKey: null,
  },
  {
    value: "require_review_for_new_contracts",
    label: "Review Alert for Newly Deployed Contracts",
    description: "Flags transactions interacting with smart contracts created less than N days ago.",
    paramKey: "max_age_days",
    paramLabel: "Contract age threshold (in days)",
    paramPlaceholder: "e.g. 7",
  },
];

export default function PoliciesPage() {
  const [policies, setPolicies] = useState<Policy[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [ruleType, setRuleType] = useState<RuleType>("maximum_transaction_value");
  const [paramValue, setParamValue] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const refresh = () => {
    listPolicies()
      .then(setPolicies)
      .catch((err) => setError(err instanceof TxLensApiError ? err.message : "Could not load safety policies"));
  };

  useEffect(refresh, []);

  const selectedRule = RULE_TYPES.find((r) => r.value === ruleType)!;

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      const parameters = selectedRule.paramKey
        ? { [selectedRule.paramKey]: Number(paramValue) }
        : {};
      await createPolicy({ name, rule_type: ruleType, parameters, is_active: true });
      setName("");
      setParamValue("");
      refresh();
    } catch (err) {
      setError(err instanceof TxLensApiError ? err.message : "Could not create policy");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deletePolicy(id);
      refresh();
    } catch (err) {
      setError(err instanceof TxLensApiError ? err.message : "Could not delete policy");
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-ink">Safety Guardrails &amp; Policies</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Configure automated safety rules evaluated against every transaction before wallet confirmation.
        </p>
      </div>

      {error && (
        <Card className="border-danger/40 bg-danger/5">
          <p className="text-sm font-medium text-danger">{error}</p>
        </Card>
      )}

      <Card>
        <CardHeader
          title="Create New Safety Rule"
          subtitle="Add customizable limits and anti-phishing guardrails"
        />
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">Rule Name</span>
              <input
                required
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder="e.g. My 1 ETH Spending Cap"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">Rule Type</span>
              <select
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink shadow-sm focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value as RuleType)}
              >
                {RULE_TYPES.map((r) => (
                  <option key={r.value} value={r.value}>
                    {r.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          <div className="rounded-md border border-border/60 bg-surface-muted/30 p-3 text-xs text-ink-muted">
            <p className="font-medium text-ink">About this guardrail:</p>
            <p className="mt-0.5">{selectedRule.description}</p>
          </div>

          {selectedRule.paramKey && (
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-ink">{selectedRule.paramLabel}</span>
              <input
                required
                type="number"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink shadow-sm placeholder:text-ink-muted/50 focus:border-primary focus:outline-none focus:ring-1 focus:ring-primary"
                placeholder={selectedRule.paramPlaceholder}
                value={paramValue}
                onChange={(e) => setParamValue(e.target.value)}
              />
            </label>
          )}

          <div>
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Saving Guardrail…" : "Save Guardrail"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader
          title="Active Guardrails"
          subtitle="Rules currently protecting your transactions"
        />
        {!policies && <p className="text-sm text-ink-muted">Loading guardrails…</p>}
        {policies && policies.length === 0 && (
          <p className="text-sm text-ink-muted">No custom policies configured yet.</p>
        )}
        {policies && policies.length > 0 && (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-semibold uppercase tracking-wider text-ink-muted">
                  <th className="pb-3 font-medium">Name</th>
                  <th className="pb-3 font-medium">Protection Type</th>
                  <th className="pb-3 font-medium">Parameters</th>
                  <th className="pb-3 font-medium">Status</th>
                  <th className="pb-3 text-right" />
                </tr>
              </thead>
              <tbody className="divide-y divide-border/60">
                {policies.map((p) => (
                  <tr key={p.id}>
                    <td className="py-3 font-medium text-ink">{p.name}</td>
                    <td className="py-3 text-ink-muted">{p.rule_type.replace(/_/g, " ")}</td>
                    <td className="py-3 font-mono text-xs text-ink-muted">{JSON.stringify(p.parameters)}</td>
                    <td className="py-3">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
                        p.is_active ? "bg-success/10 text-success" : "bg-ink-muted/10 text-ink-muted"
                      }`}>
                        {p.is_active ? "Active" : "Disabled"}
                      </span>
                    </td>
                    <td className="py-3 text-right">
                      <Button variant="danger" size="sm" onClick={() => handleDelete(p.id)}>
                        Remove
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
}

