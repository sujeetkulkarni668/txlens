import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "danger";

const VARIANT_STYLES: Record<Variant, string> = {
  primary: "bg-ink text-white hover:bg-ink/90",
  secondary: "bg-surface border border-border text-ink hover:bg-surface-muted",
  danger: "bg-danger text-white hover:bg-danger/90",
};

export function Button({
  variant = "secondary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant }) {
  return (
    <button
      className={`rounded-md px-4 py-2 text-sm font-medium transition-colors disabled:cursor-not-allowed disabled:opacity-50 ${VARIANT_STYLES[variant]} ${className}`}
      {...props}
    />
  );
}
