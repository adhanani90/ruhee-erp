#!/usr/bin/env bash
# Creates the M1 GitHub issues from the card files in this folder.
# Requires the GitHub CLI (gh), logged in with access to the repository.
# Usage: ./create_m1_issues.sh <owner>/ruhee-erp
set -euo pipefail
REPO="${1:?usage: $0 <owner>/ruhee-erp}"
cd "$(dirname "$0")"

gh label create "M1" --repo "$REPO" --color "1f6feb" --description "Milestone 1: technical spike" --force
gh label create "owner:claude-code" --repo "$REPO" --color "8250df" --force
gh label create "owner:chatgpt" --repo "$REPO" --color "1a7f37" --force
gh label create "owner:sam" --repo "$REPO" --color "bf8700" --force

for f in M1-*.md; do
  title="$(head -n 1 "$f" | sed 's/^# //')"
  owners="$(grep -m1 '^<!-- labels:' "$f" | sed -E 's/<!-- labels: (.*) -->/\1/')"
  gh issue create --repo "$REPO" --title "$title" --body-file "$f" --label "M1,${owners}"
  echo "Created: $title"
done
