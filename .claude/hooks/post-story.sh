#!/bin/bash
# Post-Story Hook — Story 完成后自动提取教训 + 记录工作流模式
# 在 Stop 事件或故事完成后触发

STORY_KEY="${1:-unknown}"
AGENT_SEQUENCE="${2:-none}"

ORCHESTRATOR="../minishop-brain/../web-shop-app/.claude/orchestrator"
if [ -f ".claude/orchestrator/learn.py" ]; then
    ORCHESTRATOR=".claude/orchestrator"
fi

# Record workflow pattern
if [ "$AGENT_SEQUENCE" != "none" ]; then
    python "$ORCHESTRATOR/learn.py" --record "$STORY_KEY" $AGENT_SEQUENCE 2>/dev/null
fi

# Generate learning context for next planning
python "$ORCHESTRATOR/learn.py" --context 2>/dev/null > .claude/memory/recent-learnings.md

echo "[Hook] Post-story: recorded $STORY_KEY workflow, updated learnings" > /dev/stderr
