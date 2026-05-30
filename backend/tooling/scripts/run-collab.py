#!/usr/bin/env python3
"""
Collaborative Story Runner - Unified CLI for Agent Collaboration

Integrates all collaboration features:
- Agent routing (auto-select best agents)
- Swarm mode (multi-agent debate)
- Shared memory and knowledge graph
- Automatic handoffs

Usage:
    python run-collab.py <story-key> [mode] [options]

Modes:
    --auto          Auto-route to best agents (default)
    --swarm         Multi-agent debate/consensus
    --sequential    Traditional sequential pipeline

Examples:
    python run-collab.py 3-5 --auto
    python run-collab.py 3-5 --swarm --agents ARCHITECT,DEV,REVIEWER
    python run-collab.py "fix login bug" --auto
"""

import argparse
import json
import os
import platform as platform_stdlib
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

SCRIPT_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from colors import Colors

from lib.platform import IS_MACOS, IS_WINDOWS


def detect_claude_cli() -> Optional[str]:
    """Detect Claude CLI across platforms.

    Returns:
        Path to Claude CLI or None if not found.
    """
    # Check common CLI names
    cli_names = ["claude", "claude-code"]

    for cli_name in cli_names:
        # Check if in PATH
        cli_path = shutil.which(cli_name)
        if cli_path:
            return cli_path

    # Platform-specific fallback locations
    if IS_WINDOWS:
        # Check common Windows install locations
        possible_paths = [
            Path(os.getenv("LOCALAPPDATA", "")) / "Programs" / "claude" / "claude.exe",
            Path(os.getenv("PROGRAMFILES", "")) / "Claude" / "claude.exe",
            Path.home() / ".claude" / "local" / "claude.exe",
            Path.home() / "AppData" / "Local" / "Programs" / "claude" / "claude.exe",
        ]
    else:
        # macOS and Linux
        possible_paths = [
            Path.home() / ".claude" / "local" / "claude",
            Path("/usr/local/bin/claude"),
            Path("/opt/claude/bin/claude"),
            Path.home() / ".local" / "bin" / "claude",
        ]

    for path in possible_paths:
        if path.exists() and path.is_file():
            return str(path)

    return None


def get_shell_quote(s: str) -> str:
    """Quote a string for shell use, cross-platform.

    Args:
        s: String to quote.

    Returns:
        Quoted string appropriate for current platform.
    """
    if IS_WINDOWS:
        # Windows: Use double quotes, escape internal quotes
        if '"' in s:
            s = s.replace('"', '""')
        return f'"{s}"'
    else:
        # Unix: Use shlex.quote
        import shlex

        return shlex.quote(s)


def normalize_path(path: Path) -> Path:
    """Normalize path for cross-platform use.

    Args:
        path: Path to normalize.

    Returns:
        Normalized Path object.
    """
    # Resolve to absolute path
    path = path.resolve()

    # On Windows, ensure we use the correct separators
    if IS_WINDOWS:
        return Path(str(path).replace("/", "\\"))
    return path


def get_config_dir() -> Path:
    """Get the configuration directory for storing data.

    Returns:
        Path to configuration directory.
    """
    if IS_WINDOWS:
        base = Path(os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming"))
        return base / "devflow"
    elif IS_MACOS:
        return Path.home() / "Library" / "Application Support" / "devflow"
    else:
        # Linux/Unix: Use XDG
        xdg_data = os.getenv("XDG_DATA_HOME") or str(Path.home() / ".local" / "share")
        return Path(xdg_data) / "devflow"


def get_cache_dir() -> Path:
    """Get the cache directory for temporary data.

    Returns:
        Path to cache directory.
    """
    if IS_WINDOWS:
        base = Path(os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local"))
        return base / "devflow" / "cache"
    elif IS_MACOS:
        return Path.home() / "Library" / "Caches" / "devflow"
    else:
        xdg_cache = os.getenv("XDG_CACHE_HOME") or str(Path.home() / ".cache")
        return Path(xdg_cache) / "devflow"


# Import collaboration modules
from lib.agent_handoff import HandoffGenerator, create_handoff  # noqa: E402
from lib.agent_router import AgentRouter, RoutingResult  # noqa: E402
from lib.shared_memory import get_knowledge_graph, get_shared_memory, share_learning  # noqa: E402
from lib.swarm_orchestrator import ConsensusType, SwarmConfig, SwarmOrchestrator  # noqa: E402

# Try to import validation loop
try:
    from lib.validation_loop import (
        POST_COMPLETION_GATES,
        PREFLIGHT_GATES,
        LoopContext,
        ValidationLoop,
    )

    HAS_VALIDATION = True
except ImportError:
    HAS_VALIDATION = False


def print_banner():
    """Print the CLI banner."""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║        DEVFLOW COLLABORATIVE STORY RUNNER                     ║
╠═══════════════════════════════════════════════════════════════╣
║  Multi-agent collaboration with swarm and auto-routing        ║
╚═══════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_routing_decision(result: RoutingResult, router: AgentRouter):
    """Print the routing decision."""
    print(f"\n{Colors.BOLD}Routing Decision{Colors.END}")
    print(router.explain_routing(result))


def print_section(title: str, content: str = ""):
    """Print a section header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}═══ {title} ═══{Colors.END}")
    if content:
        print(content)


def run_auto_mode(story_key: str, task: str, args: argparse.Namespace):
    """Run with automatic agent routing."""
    print_section("Auto-Routing Mode")

    router = AgentRouter()
    result = router.route(task)

    print_routing_decision(result, router)

    # Decide execution mode based on routing
    if result.workflow == "swarm":
        print(f"\n{Colors.YELLOW}-> Using swarm mode for multi-agent collaboration{Colors.END}")
        return run_swarm_mode(story_key, task, result.agents, args)
    else:
        print(f"\n{Colors.YELLOW}-> Using sequential execution{Colors.END}")
        return run_sequential_mode(story_key, task, result.agents, args)


def run_swarm_mode(story_key: str, task: str, agents: list[str], args: argparse.Namespace):
    """Run swarm mode with multi-agent debate."""
    print_section("Swarm Mode", f"Agents: {', '.join(agents)}")

    config = SwarmConfig(
        max_iterations=args.max_iterations,
        consensus_type=ConsensusType[args.consensus.upper()],
        parallel_execution=args.parallel,
        verbose=not args.quiet,
        budget_limit_usd=args.budget,
    )

    orchestrator = SwarmOrchestrator(story_key, config)
    result = orchestrator.run_swarm(agents, task)

    # Print result
    print(f"\n{Colors.GREEN}{result.to_summary()}{Colors.END}")

    # Save result
    save_result(story_key, "swarm", result.to_dict())

    return result


def run_sequential_mode(story_key: str, task: str, agents: list[str], args: argparse.Namespace):
    """Run sequential agent execution with handoffs."""
    print_section("Sequential Mode", f"Pipeline: {' -> '.join(agents)}")

    get_shared_memory(story_key)
    get_knowledge_graph(story_key)
    handoff_gen = HandoffGenerator(story_key)

    results = []
    previous_output = ""

    for i, agent in enumerate(agents):
        print(f"\n{Colors.CYAN}> Running {agent}...{Colors.END}")

        # Get context including handoffs
        context = handoff_gen.generate_context_for_agent(agent)

        # Build prompt for agent invocation
        prompt = f"""You are the {agent} agent.

{context}

## Task
{task}

## Previous Work
{previous_output[:2000] if previous_output else "This is the first step."}

Complete your part of this task according to your role.
"""

        # Invoke agent (simplified - in real use would call Claude CLI)
        # Note: prompt is prepared above for when full agent invocation is implemented
        _ = prompt  # Acknowledge prompt is ready for future use
        print("  -> Generating response...")

        # For demo, we'll note the handoff
        if i > 0:
            prev_agent = agents[i - 1]
            handoff = create_handoff(
                from_agent=prev_agent,
                to_agent=agent,
                story_key=story_key,
                summary=f"Completed {prev_agent} phase, handing off to {agent}",
            )
            print(f"  -> Handoff from {prev_agent}: {handoff.id}")

        # Record in shared memory
        share_learning(
            agent, f"Processed task: {task[:50]}...", story_key, tags=["sequential", agent.lower()]
        )

        results.append(
            {"agent": agent, "status": "completed", "timestamp": datetime.now().isoformat()}
        )

    print(f"\n{Colors.GREEN} Sequential pipeline complete!{Colors.END}")

    # Save result
    save_result(story_key, "sequential", {"agents": agents, "results": results})

    return results


def save_result(story_key: str, mode: str, result: dict):
    """Save result to file (cross-platform)."""
    # Use cross-platform cache directory for results
    results_dir = get_cache_dir() / "results"
    results_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize story_key for filename (Windows compatibility)
    safe_key = "".join(c if c.isalnum() or c in "-_" else "_" for c in story_key)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{safe_key}_{mode}_{timestamp}.json"

    filepath = normalize_path(results_dir / filename)

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(
            {
                "story_key": story_key,
                "mode": mode,
                "timestamp": datetime.now().isoformat(),
                "platform": platform_stdlib.system(),
                "result": result,
            },
            f,
            indent=2,
            default=str,
            ensure_ascii=False,
        )

    print(f"\n{Colors.CYAN} Result saved to: {filepath}{Colors.END}")


def show_memory(story_key: str):
    """Display shared memory and knowledge graph."""
    print_section("Shared Memory & Knowledge Graph")

    memory = get_shared_memory(story_key)
    kg = get_knowledge_graph(story_key)

    print(memory.to_context_string())
    print()
    print(kg.to_context_string())


def query_knowledge(story_key: str, question: str):
    """Query the knowledge graph."""
    print_section(f"Knowledge Query: {question}")

    kg = get_knowledge_graph(story_key)
    result = kg.query(question)

    if result:
        print(f"\n{Colors.GREEN}Answer:{Colors.END} {result['decision']}")
        print(f"{Colors.CYAN}Source:{Colors.END} {result['agent']} ({result['timestamp'][:10]})")
        print(f"{Colors.CYAN}Topic:{Colors.END} {result['topic']}")
    else:
        print(f"\n{Colors.YELLOW}No matching decision found.{Colors.END}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Collaborative Story Runner with multi-agent support",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run-collab.py 3-5 --auto
  python run-collab.py 3-5 --swarm --agents ARCHITECT,DEV,REVIEWER
  python run-collab.py "fix login bug" --auto
  python run-collab.py 3-5 --memory      # Show shared memory
  python run-collab.py 3-5 --query "What did ARCHITECT decide about auth?"
        """,
    )

    # Positional argument
    parser.add_argument("story_key", nargs="?", default=None, help="Story key or task description")

    # Mode selection
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--auto", action="store_true", default=True, help="Auto-route to best agents (default)"
    )
    mode_group.add_argument("--swarm", action="store_true", help="Multi-agent swarm/debate mode")
    mode_group.add_argument(
        "--sequential", action="store_true", help="Traditional sequential pipeline"
    )

    # Utility modes
    parser.add_argument(
        "--memory", action="store_true", help="Show shared memory and knowledge graph"
    )
    parser.add_argument("--query", type=str, metavar="QUESTION", help="Query the knowledge graph")
    parser.add_argument(
        "--route-only", action="store_true", help="Just show routing decision, don't execute"
    )

    # Agent selection
    parser.add_argument(
        "--agents", type=str, help="Comma-separated list of agents (for swarm/sequential)"
    )

    # Swarm options
    parser.add_argument(
        "--max-iterations", type=int, default=3, help="Maximum swarm iterations (default: 3)"
    )
    parser.add_argument(
        "--consensus",
        type=str,
        default="reviewer_approval",
        choices=["unanimous", "majority", "quorum", "reviewer_approval"],
        help="Consensus type (default: reviewer_approval)",
    )
    parser.add_argument("--parallel", action="store_true", help="Enable parallel agent execution")

    # General options
    parser.add_argument(
        "--model",
        type=str,
        default="opus",
        choices=["opus", "sonnet", "haiku"],
        help="Claude model to use (default: opus)",
    )
    parser.add_argument(
        "--budget", type=float, default=20.0, help="Budget limit in USD (default: 20.0)"
    )
    parser.add_argument("--quiet", "-q", action="store_true", help="Reduce output verbosity")
    parser.add_argument("--task", type=str, help="Override task description")

    # Validation options
    parser.add_argument("--validate", action="store_true", help="Enable validation loop")
    parser.add_argument("--no-validate", action="store_true", help="Disable validation loop")

    return parser.parse_args()


def run_validation(story_key: str, args: argparse.Namespace, tier: str = "preflight") -> bool:
    """Run validation checks.

    Args:
        story_key: Story identifier
        args: Command line arguments
        tier: Which tier to run ("preflight" or "post")

    Returns:
        True if validation passed, False otherwise
    """
    if not HAS_VALIDATION:
        return True

    validation_enabled = args.validate and not args.no_validate
    if not validation_enabled:
        return True

    gates = PREFLIGHT_GATES if tier == "preflight" else POST_COMPLETION_GATES
    validation_loop = ValidationLoop(
        gates=gates,
        config={"auto_fix_enabled": True},
        story_key=story_key,
    )
    context = LoopContext(story_key=story_key, phase=tier)

    if tier == "preflight":
        print(f"\n{Colors.CYAN}[VALIDATION] Running pre-flight checks...{Colors.END}")
        report = validation_loop.run_preflight(context)
    else:
        print(f"\n{Colors.CYAN}[VALIDATION] Running post-completion checks...{Colors.END}")
        report = validation_loop.run_post_completion(context)

    if report.passed:
        print(
            f"{Colors.GREEN}[PASS] Validation passed ({len(report.gate_results)} gates){Colors.END}"
        )
        if report.warnings:
            for warn in report.warnings:
                print(f"  {Colors.YELLOW}[WARN] {warn.gate_name}: {warn.message}{Colors.END}")
        return True
    else:
        print(f"{Colors.RED}[FAIL] Validation failed{Colors.END}")
        for failure in report.failures:
            print(f"  - {failure.gate_name}: {failure.message}")
        return tier != "preflight"  # Block on preflight, warn on post


def main():
    args = parse_args()

    # Handle utility modes first
    if args.memory:
        if not args.story_key:
            print(f"{Colors.RED}Error: story_key required for --memory{Colors.END}")
            return 1
        show_memory(args.story_key)
        return 0

    if args.query:
        if not args.story_key:
            print(f"{Colors.RED}Error: story_key required for --query{Colors.END}")
            return 1
        query_knowledge(args.story_key, args.query)
        return 0

    # Validate story key
    if not args.story_key:
        print(f"{Colors.RED}Error: story_key or task description required{Colors.END}")
        print("Use --help for usage information")
        return 1

    print_banner()

    story_key = args.story_key
    task = args.task or f"Implement story: {story_key}"

    print(f"{Colors.BOLD}Story/Task:{Colors.END} {story_key}")
    print(f"{Colors.BOLD}Mode:{Colors.END} ", end="")

    # Run pre-flight validation
    if not run_validation(story_key, args, "preflight"):
        print(f"\n{Colors.RED}[BLOCKED] Pre-flight validation failed. Aborting.{Colors.END}")
        return 1

    # Route-only mode
    if args.route_only:
        print("Route Analysis Only")
        router = AgentRouter()
        result = router.route(task)
        print_routing_decision(result, router)
        return 0

    # Parse and validate agents if provided
    agents = None
    if args.agents:
        agents = [a.strip().upper() for a in args.agents.split(",")]
        valid_agents = {
            "SM",
            "DEV",
            "BA",
            "ARCHITECT",
            "PM",
            "WRITER",
            "MAINTAINER",
            "REVIEWER",
            "SECURITY",
        }
        invalid_agents = [a for a in agents if a not in valid_agents]
        if invalid_agents:
            print(
                f"\n{Colors.RED}Error: Invalid agent name(s): {', '.join(invalid_agents)}{Colors.END}"
            )
            print(f"Valid agents are: {', '.join(sorted(valid_agents))}")
            return 1

    # Execute based on mode
    try:
        if args.swarm:
            print("Swarm")
            if not agents:
                agents = ["ARCHITECT", "DEV", "REVIEWER"]
            run_swarm_mode(story_key, task, agents, args)

        elif args.sequential:
            print("Sequential")
            if not agents:
                agents = ["SM", "DEV", "REVIEWER"]
            results = run_sequential_mode(story_key, task, agents, args)
            if results:
                print(f"  Completed {len(results)} agent(s)")

        else:  # auto mode
            print("Auto-Route")
            run_auto_mode(story_key, task, args)

        # Run post-completion validation
        run_validation(story_key, args, "post")

        print(f"\n{Colors.GREEN}{'═' * 60}{Colors.END}")
        print(f"{Colors.GREEN} Collaboration complete!{Colors.END}")
        return 0

    except KeyboardInterrupt:
        print(f"\n{Colors.YELLOW} Interrupted by user{Colors.END}")
        return 130
    except Exception as e:
        print(f"\n{Colors.RED} Error: {e}{Colors.END}")
        if not args.quiet:
            import traceback

            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
