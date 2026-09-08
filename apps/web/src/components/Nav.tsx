import Link from "next/link";
import { WalletConnectButton } from "@/components/WalletConnectButton";

const LINKS = [
  { href: "/", label: "Dashboard" },
  { href: "/analyze", label: "Transaction Analysis" },
  { href: "/policies", label: "Policies" },
  { href: "/reports", label: "Reports" },
  { href: "/settings", label: "Settings" },
];

export function Nav() {
  return (
    <header className="border-b border-border bg-surface">
      <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
        <div className="flex items-center gap-8">
          <Link href="/" className="text-base font-semibold tracking-tight text-ink">
            TxLens
          </Link>
          <nav className="flex gap-6">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="text-sm text-ink-muted transition-colors hover:text-ink"
              >
                {link.label}
              </Link>
            ))}
          </nav>
        </div>
        <WalletConnectButton />
      </div>
    </header>
  );
}
