import { Card, CardHeader } from "@/components/ui/Card";

export default function SettingsPage() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Settings</h1>
        <p className="mt-1 text-sm text-ink-muted">Network and API configuration.</p>
      </div>

      <Card>
        <CardHeader title="Backend API" subtitle="Read-only — set via NEXT_PUBLIC_API_URL at build/deploy time" />
        <dl className="grid grid-cols-2 gap-3 text-sm">
          <dt className="text-ink-muted">API base URL</dt>
          <dd className="font-mono text-ink">{apiUrl}</dd>
        </dl>
      </Card>

      <Card>
        <CardHeader title="Network" />
        <p className="text-sm text-ink-muted">
          The active EVM RPC endpoint is configured server-side via <code className="rounded bg-surface-muted px-1">EVM_RPC_URL</code> and{" "}
          <code className="rounded bg-surface-muted px-1">EVM_CHAIN</code> in the backend&apos;s environment — there
          is no in-app editor for this yet. Your wallet extension&apos;s selected network determines
          what it will actually sign against; make sure it matches.
        </p>
      </Card>
    </div>
  );
}
