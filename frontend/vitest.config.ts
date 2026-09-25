import { defineConfig } from "vitest/config";
import path from "node:path";

export default defineConfig({
  esbuild: { jsx: "automatic" },
  resolve: { alias: { "@": path.resolve(__dirname) } },
  test: { env: { NEXT_PUBLIC_VIGIL_ENV: "dev" }, environment: "jsdom", setupFiles: ["./tests/setup.ts"], include: ["tests/**/*.test.{ts,tsx}"] },
});
