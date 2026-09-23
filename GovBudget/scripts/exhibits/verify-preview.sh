#!/usr/bin/env bash
# Operator handoff for sessions that cannot bind local build/browser-test ports.
# Builds and verifies only. Does not deploy or change Vercel/R2 configuration.
set -euo pipefail

EXHIBIT_REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "${EXHIBIT_REPO_ROOT}/site"
mkdir -p test-results/exhibits
export NEXT_PUBLIC_SITE_URL=https://fiscalreceipts.com

echo "Building Fiscal Receipts with the three visual pilots..."
npm run build 2>&1 | tee test-results/exhibits/build.log

echo "Running the required site verification gates..."
npm run verify 2>&1 | tee test-results/exhibits/verify.log

echo "Checks passed. Starting the local preview at http://127.0.0.1:4173/explore/"
echo "Leave this Terminal window open for visual review. Press Control-C to stop."
exec node scripts/serve-static.mjs
