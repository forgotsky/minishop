#!/bin/bash
# PreCompact Hook — 对话压缩前保存未完成任务
# 读 .ai/tasks/ 下所有文件，找到 - [ ] 没勾的步骤，写入 compact-context.md
# Claude Code 在恢复时会自动加载这个文件

CONTEXT_FILE=".claude/compact-context.md"

echo "## 未完成任务（从 .ai/tasks/ 恢复）" > "$CONTEXT_FILE"
echo "" >> "$CONTEXT_FILE"

for task_file in .ai/tasks/*.md; do
  [ -f "$task_file" ] || continue
  pending=$(grep '^- \[ \]' "$task_file")
  if [ -n "$pending" ]; then
    echo "**$(basename "$task_file" .md):**" >> "$CONTEXT_FILE"
    echo "$pending" >> "$CONTEXT_FILE"
    echo "" >> "$CONTEXT_FILE"
  fi
done

echo "已保存 $(grep -c '^- \[' "$CONTEXT_FILE" 2>/dev/null || echo 0) 个待办项到 $CONTEXT_FILE"
