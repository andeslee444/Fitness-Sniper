import { defineConfig, configDefaults } from "vitest/config";
import { resolve } from "path";

export default defineConfig({
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/__tests__/setup.ts"],
    // ROADMAP #81: src/__tests__/client-graph/** runs under
    // vitest.client-graph.config.ts, where server-only is the REAL package.
    // Under the alias below its control assertions would be false, so it is
    // excluded here and `npm test` runs both configs.
    exclude: [...configDefaults.exclude, "src/__tests__/client-graph/**"],
    server: {
      deps: {
        // Mock server-only so it is a no-op in the test environment
        // (it throws in non-Next.js runtimes by design)
        inline: ["server-only"],
      },
    },
  },
  resolve: {
    alias: {
      "@": resolve(__dirname, "./src"),
      // server-only is a no-op in tests — it only guards against client bundling
      "server-only": resolve(__dirname, "./src/__tests__/__mocks__/server-only.ts"),
    },
  },
});
