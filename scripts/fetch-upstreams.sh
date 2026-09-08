#!/usr/bin/env bash
set -euo pipefail
DEST="${1:-upstreams}"
mkdir -p "$DEST"
cd "$DEST"
repos=(
  "https://github.com/Universal-Commerce-Protocol/samples.git"
  "https://github.com/modelcontextprotocol/typescript-sdk.git"
  "https://github.com/AnswerDotAI/llms-txt.git"
  "https://github.com/xpaysh/awesome-agentic-commerce.git"
  "https://github.com/anthropics/commerce-agents.git"
  "https://github.com/stripe-samples/machine-payments.git"
)
for repo in "${repos[@]}"; do
  name="$(basename "$repo" .git)"
  if [[ -d "$name/.git" ]]; then git -C "$name" pull --ff-only; else git clone --depth 1 "$repo" "$name"; fi
done
