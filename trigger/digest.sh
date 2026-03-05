#!/usr/bin/env bash
# Device Link — Daily Digest Generator
# Rolls up all task ledger entries for a given day into a single summary note.
#
# Usage:
#   ./digest.sh              # today's digest
#   ./digest.sh 2026-03-04   # specific date

set -euo pipefail

VAULT_DIR="$HOME/Documents/second-brain"
LEDGER_DIR="$VAULT_DIR/_ledger/tasks"
DAILY_DIR="$VAULT_DIR/_ledger/daily"
TARGET_DATE="${1:-$(date +%Y-%m-%d)}"
TARGET_PREFIX="${TARGET_DATE//-/}"

if [[ ! -d "$VAULT_DIR" ]]; then
    echo "Error: Second brain vault not found at $VAULT_DIR" >&2
    exit 1
fi

mkdir -p "$DAILY_DIR"

# Find all task entries for the target date
MATCHING_FILES=()
for f in "$LEDGER_DIR"/${TARGET_PREFIX}*.md 2>/dev/null; do
    [[ -f "$f" ]] && MATCHING_FILES+=("$f")
done

if [[ ${#MATCHING_FILES[@]} -eq 0 ]]; then
    echo "No tasks logged for $TARGET_DATE"
    exit 0
fi

# Count by brain and status
LEFT_COUNT=0
RIGHT_COUNT=0
COMPLETED=0
FAILED=0
TASKS_LIST=""

for f in "${MATCHING_FILES[@]}"; do
    brain=$(grep "^brain:" "$f" | head -1 | sed 's/brain: *//')
    task=$(grep "^task:" "$f" | head -1 | sed 's/task: *"//;s/"$//')
    status=$(grep "^status:" "$f" | head -1 | sed 's/status: *//')
    mode=$(grep "^mode:" "$f" | head -1 | sed 's/mode: *//')

    [[ "$brain" == "left" ]] && ((LEFT_COUNT++)) || ((RIGHT_COUNT++))
    [[ "$status" == "completed" ]] && ((COMPLETED++)) || ((FAILED++))

    local_time=$(basename "$f" .md | cut -d- -f1 | sed 's/\(....\)\(..\)\(..\)\(..\)\(..\)\(..\)/\4:\5/')
    TASKS_LIST+="| ${local_time} | ${brain} | ${mode} | ${task} | ${status} |\n"
done

DIGEST_FILE="$DAILY_DIR/${TARGET_DATE}.md"

cat > "$DIGEST_FILE" <<EOF
---
title: "Daily Digest — ${TARGET_DATE}"
date: ${TARGET_DATE}
tags: [task-log, digest]
tasks_total: ${#MATCHING_FILES[@]}
tasks_completed: ${COMPLETED}
tasks_failed: ${FAILED}
---

# Daily Digest — ${TARGET_DATE}

## Summary
- **Total tasks**: ${#MATCHING_FILES[@]}
- **Completed**: ${COMPLETED}
- **Failed**: ${FAILED}
- **Left brain**: ${LEFT_COUNT} tasks
- **Right brain**: ${RIGHT_COUNT} tasks

## Tasks

| Time | Brain | Mode | Task | Status |
|------|-------|------|------|--------|
$(echo -e "$TASKS_LIST")

EOF

echo "Digest written: $DIGEST_FILE"
echo "  ${#MATCHING_FILES[@]} tasks (${COMPLETED} completed, ${FAILED} failed)"
