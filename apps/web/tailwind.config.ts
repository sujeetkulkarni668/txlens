import type { Config } from "tailwindcss";

// Restrained, developer-infrastructure-style palette (see README design
// principles) — neutral surfaces, no neon/gradient tokens.
const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        surface: "#ffffff",
        "surface-muted": "#f6f7f8",
        border: "#e2e4e8",
        ink: "#111318",
        "ink-muted": "#5b6270",
        danger: "#b3261e",
        warning: "#946200",
        success: "#1e6b4f",
      },
    },
  },
  plugins: [],
};
export default config;
