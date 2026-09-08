"use client";

import { useEffect, useState } from "react";
import { Card, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { createPolicy, deletePolicy, listPolicies, TxLensApiError } from "@/lib/api";
import type { Policy, RuleType } from "@txlens/shared-types";

const RULE_TYPES: { value: RuleType; label: string; paramKey: string | null; paramLabel?: string }[] = [
  { value: "maximum_transaction_value", label: "Maximum transaction value", paramKey: "max_value", paramLabel: "Max value (native units)" },
  { value: "maximum_daily_spend", label: "Maximum daily spend", paramKey: "max_daily_spend", paramLabel: "Max daily spend (native units)" },
  { value: "require_review_above", label: "Require review above threshold", paramKey: "threshold", paramLabel: "Threshold (native units)" },
  { value: "block_unlimited_approvals", label: "Block unlimited approvals", paramKey: null },
  { value: "block_unknown_contracts", label: "Block unknown contracts", paramKey: null },
  { value: "require_review_for_new_contracts", label: "Require review for new contracts", paramKey: "max_age_days", paramLabel: "Max age (days)" },
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
      .catch((err) => setError(err instanceof TxLensApiError ? err.message : "Could not load policies"));
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
        <h1 className="text-xl font-semibold tracking-tight text-ink">Policies</h1>
        <p className="mt-1 text-sm text-ink-muted">
          Deterministic rules evaluated against every analyzed transaction.
        </p>
      </div>

      {error && (
        <Card className="border-danger/40">
          <p className="text-sm text-danger">{error}</p>
        </Card>
      )}

      <Card>
        <CardHeader title="Create policy" />
        <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 md:grid-cols-3">
          <label className="block text-sm">
            <span className="mb-1 block text-ink-muted">Name</span>
            <input
              required
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block text-ink-muted">Rule type</span>
            <select
              className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink"
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
          {selectedRule.paramKey && (
            <label className="block text-sm">
              <span className="mb-1 block text-ink-muted">{selectedRule.paramLabel}</span>
              <input
                required
                type="number"
                className="w-full rounded-md border border-border bg-surface px-3 py-2 text-ink"
                value={paramValue}
                onChange={(e) => setParamValue(e.target.value)}
              />
            </label>
          )}
          <div className="md:col-span-3">
            <Button type="submit" variant="primary" disabled={submitting}>
              {submitting ? "Creating…" : "Create policy"}
            </Button>
          </div>
        </form>
      </Card>

      <Card>
        <CardHeader title="Active policies" />
        {!policies && <p className="text-sm text-ink-muted">Loading…</p>}
        {policies && policies.length === 0 && (
          <p className="text-sm text-ink-muted">No policies configured yet.</p>
        )}
        {policies && policies.length > 0 && (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-ink-muted">
                <th className="pb-2 font-medium">Name</th>
                <th className="pb-2 font-medium">Rule</th>
                <th className="pb-2 font-medium">Parameters</th>
                <th className="pb-2 font-medium">Status</th>
                <th className="pb-2" />
              </tr>
            </thead>
            <tbody>
              {policies.map((p) => (
                <tr key={p.id} className="border-b border-border last:border-0">
                  <td className="py-2 text-ink">{p.name}</td>
                  <td className="py-2 text-ink-muted">{p.rule_type}</td>
                  <td className="py-2 font-mono text-ink-muted">{JSON.stringify(p.parameters)}</td>
                  <td className="py-2 text-ink-muted">{p.is_active ? "active" : "inactive"}</td>
                  <td className="py-2 text-right">
                    <Button variant="danger" onClick={() => handleDelete(p.id)}>
                      Delete
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </Card>
    </div>
  );
}
