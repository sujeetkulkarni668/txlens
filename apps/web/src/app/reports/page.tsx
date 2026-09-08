import { Card, CardHeader } from "@/components/ui/Card";
import Link from "next/link";

export default function ReportsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold tracking-tight text-ink">Reports</h1>
        <p className="mt-1 text-sm text-ink-muted">Readable investigation reports.</p>
      </div>

      <Card>
        <CardHeader title="Not yet persisted" />
        <p className="text-sm text-ink-muted">
          There is no <code className="rounded bg-surface-muted px-1">POST /api/v1/reports</code> endpoint
          in this build, so analysis results aren&apos;t saved as retrievable reports yet — each{" "}
          <Link href="/analyze" className="underline">
            Transaction Analysis
          </Link>{" "}
          is a one-off request. The MCP server&apos;s <code className="rounded bg-surface-muted px-1">create_security_report</code>{" "}
          tool reflects this honestly too: it returns the analysis inline and marks{" "}
          <code className="rounded bg-surface-muted px-1">persisted: false</code>.
        </p>
      </Card>
    </div>
  );
}
