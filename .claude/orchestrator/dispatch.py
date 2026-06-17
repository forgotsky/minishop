"""
Orchestrator dispatch — auto-assign agent teams + result passing + judge.
Herme's Phase 3 pattern: LLM reads task → outputs assignments → workflow runs → judge checks.
"""
import os
import json

BRAIN_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "..", "minishop-brain")

# Agent capability manifest
AGENT_MANIFEST = {
    "planner":           {"role": "拆解任务、分配 Agent、编排工作流", "tools": "Read,Write,Glob"},
    "business-analyst":  {"role": "写 URS 需求文档", "tools": "Read,Glob"},
    "product-manager":   {"role": "拆 Story、定优先级", "tools": "Read,Glob"},
    "architect":         {"role": "设计技术方案", "tools": "Read,Grep,Glob"},
    "backend-dev":       {"role": "FastAPI/Python 后端代码", "tools": "Read,Write,Edit,Bash"},
    "miniprogram-dev":   {"role": "微信小程序 WXML/WXSS/JS", "tools": "Read,Write,Edit"},
    "tester":            {"role": "pytest/httpx 测试", "tools": "Read,Write,Edit,Bash"},
    "reviewer":          {"role": "代码审查、安全检查", "tools": "Read,Grep,Glob"},
    "devops-engineer":   {"role": "CI/CD, K8s, Docker", "tools": "Read,Write,Edit,Bash"},
    "tech-writer":       {"role": "写 README/Docs", "tools": "Read,Write"},
    "scrum-master":      {"role": "跟踪 Story 进度", "tools": "Read,Glob,Bash"},
}


def manifest_for_prompt() -> str:
    """Generate agent capability list for LLM prompt."""
    lines = ["可用 Agent 类型:"]
    for name, info in AGENT_MANIFEST.items():
        lines.append(f"  - {name}: {info['role']} (工具: {info['tools']})")
    return "\n".join(lines)


def output_path(story_key: str) -> str:
    """Path for upstream output.md that downstream reads."""
    d = os.path.join(BRAIN_DIR, ".ai", "outputs")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{story_key}.output.md")


def write_output(story_key: str, summary: str, details: dict = None):
    """Write upstream result for downstream consumption."""
    path = output_path(story_key)
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {story_key} 产出\n\n")
        f.write(f"## 摘要\n{summary}\n\n")
        if details:
            f.write("## 详情\n")
            for k, v in details.items():
                f.write(f"- **{k}**: {v}\n")
    return path


def read_output(story_key: str) -> str:
    """Read upstream output for downstream context injection."""
    path = output_path(story_key)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return f"[{story_key} 尚无产出]"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", action="store_true", help="Print agent manifest for LLM prompt")
    parser.add_argument("--write", nargs=2, metavar=("STORY", "SUMMARY"), help="Write output for downstream")
    parser.add_argument("--read", metavar="STORY", help="Read upstream output")
    args = parser.parse_args()

    if args.manifest:
        print(manifest_for_prompt())

    if args.write:
        write_output(args.write[0], args.write[1])
        print(f"{args.write[0]} output written")

    if args.read:
        print(read_output(args.read))
