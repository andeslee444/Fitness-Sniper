import { defineConfig } from "vitest/config";
import { resolve } from "path";

/**
 * vitest.client-graph.config.ts — ROADMAP #81.
 *
 * The main vitest.config.ts aliases `server-only` to a no-op stub so server
 * components can be rendered under jsdom. That alias also hides the one
 * failure a client-safe module must never have: transitively importing a
 * `import "server-only"` module, which Next rejects at `next build` — a
 * ~35-minute round trip through export → build → verify. This config runs
 * src/__tests__/client-graph/** with the REAL package
 * (node_modules/server-only/index.js throws on import), so a leak into the
 * "use client" graph fails here in about a second.
 *
 * Same root (this directory) and the same tsconfig as the main config, so
 * JSX comes from "jsx": "react-jsx" exactly as it does there.
 *
 * Wired into `npm test` (package.json) after the main run; the main config
 * excludes this directory because its control assertions are only true
 * without the alias.
 */
export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    include: ["src/__tests__/client-graph/**/*.test.{ts,tsx}"],
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
      // NO "server-only" alias — on purpose. See the header.
    },
  },
});
