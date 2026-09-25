import type { Config } from "tailwindcss";

const token = (name: string) => `hsl(var(--${name}) / <alpha-value>)`;
const tones = ["pos", "cau", "neg", "neu", "pri"].reduce<Record<string, Record<string, string>>>((acc, tone) => {
  acc[tone] = { DEFAULT: token(tone), bg: token(`${tone}-bg`), bd: token(`${tone}-bd`) };
  return acc;
}, {});

export default {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./modules/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        background: token("background"), card: token("card"), foreground: token("foreground"),
        muted: { DEFAULT: token("muted"), foreground: token("muted-foreground") },
        border: token("border"), input: token("input"), ring: token("ring"), accent: token("accent"),
        primary: { DEFAULT: token("primary"), foreground: token("primary-foreground") },
        dev: { DEFAULT: token("dev"), bg: token("dev-bg") },
        test: { DEFAULT: token("test"), bg: token("test-bg") },
        ...tones,
      },
      fontFamily: { mono: ["IBM Plex Mono", "ui-monospace", "monospace"] },
      boxShadow: { card: "var(--shadow)" },
    },
  },
  plugins: [],
} satisfies Config;
