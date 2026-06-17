#!/bin/bash
# PreCompact Hook — 对话压缩前保存未完成任务
# 从脑力仓库读任务，写入 memory 文件

BRAIN_TASKS="../minishop-brain/.ai/tasks"
CONTEXT_FILE=".claude/compact-context.md"

echo "## 未完成任务（从 minishop-brain）" > "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"

for task_file in "$BRAIN_TASKS"/SHOP-*.md; do
  [ -f "$task_file" ] || continue
  pending=$(grep '^- \[ \]' "$task_file")
  if [ -n "$pending" ]; then
    echo "**$(basename "$task_file" .md):**" >> "$CONTEXT_FILE"
    echo "$pending" >> "$CONTEXT_FILE"
    echo "" >> "$CONTEXT_FILE"
  fi
done

echo "[Hook] 已保存待办项到 $CONTEXT_FILE" > /dev/stderr
