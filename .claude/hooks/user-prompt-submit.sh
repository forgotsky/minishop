#!/bin/bash
# UserPromptSubmit Hook — 每次用户发消息前，注入未完成任务
# 扫 .ai/tasks/ 下所有文件，找 - [ ] 项目
# 写到 .ai/tasks/PENDING.md，Claude Code 以 memory 形式加载

PENDING_FILE=".ai/tasks/PENDING.md"

cat > "$PENDING_FILE" << 'EOF'
---
name: pending-tasks
description: Active incomplete task items across all stories
metadata:
  type: project
---

EOF

has_pending=false
for task_file in .ai/tasks/SHOP-*.md; do
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

# 统计
total=$(grep -c '^- \[' "$PENDING_FILE" 2>/dev/null || echo 0)
echo "[Hook] 已扫描任务文件，$total 个待办项写入 $PENDING_FILE" > /dev/stderr
