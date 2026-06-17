#!/bin/bash
# UserPromptSubmit Hook — 每次用户发消息前，扫描脑力仓库的未完成任务
# 脑力仓库: ../minishop-brain/.ai/tasks/
# 写入 Claude Code memory 目录: .claude/memory/pending-tasks.md

BRAIN_TASKS="../minishop-brain/.ai/tasks"
MEMORY_DIR=".claude/memory"
PENDING_FILE="$MEMORY_DIR/pending-tasks.md"

# 确保 memory 目录存在
mkdir -p "$MEMORY_DIR"

cat > "$PENDING_FILE" << 'EOF'
---
name: pending-tasks
description: Active incomplete task items from minishop-brain
metadata:
  type: project
---

EOF

has_pending=false
for task_file in "$BRAIN_TASKS"/SHOP-*.md; do
  [ -f "$task_file" ] || continue
  story=$(basename "$task_file" .md)
  items=$(grep '^- \[ \]' "$task_file" 2>/dev/null)
  if [ -n "$items" ]; then
    has_pending=true
    echo "**$story:**" >> "$PENDING_FILE"
    while IFS= read -r line; do
      echo "  $line" >> "$PENDING_FILE"
    done <<< "$items"
    echo "" >> "$PENDING_FILE"
  fi
done

if [ "$has_pending" = false ]; then
  echo "无未完成任务。" >> "$PENDING_FILE"
fi

total=$(grep -c '^- \[' "$PENDING_FILE" 2>/dev/null || echo 0)
echo "[Hook] minishop-brain: $total 个待办项 → $PENDING_FILE" > /dev/stderr
