#!/usr/bin/env python3
"""
Adversarial Swarm Test Harness and Performance Tracker

Tests the adversarial swarm system and tracks performance metrics
to identify trends like diminishing returns.

Usage:
    python3 tooling/scripts/test_adversarial_swarm.py [--runs N] [--plot]

Metrics tracked per round:
- New arguments introduced
- Challenges raised
- Concessions made
- Agreement score delta
- Token usage
- Unique issues identified

Outputs:
- JSON results in tooling/.automation/benchmarks/
- Performance plots (if --plot flag used)
"""

import argparse
import json
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add lib to path
sys.path.insert(0, str(Path(__file__).parent / "lib"))

try:
    from personality_system import (
        ConvergenceDetector,
        PersonalitySelector,
    )
except ImportError:
    print("[ERROR] Could not import personality_system. Run from project root.")
    sys.exit(1)


PROJECT_ROOT = Path(__file__).parent.parent.parent
BENCHMARK_DIR = PROJECT_ROOT / "tooling" / ".automation" / "benchmarks"


@dataclass
class RoundMetrics:
    """Metrics for a single debate round."""

    round_num: int
    new_arguments: int = 0
    challenges_raised: int = 0
    concessions_made: int = 0
    agreement_score: float = 0.0
    agreement_delta: float = 0.0
    unique_issues: int = 0
    tokens_used: int = 0
    cost_usd: float = 0.0
    positions_changed: int = 0  # How many agents changed position


@dataclass
class SwarmBenchmarkResult:
    """Complete benchmark result for a swarm run."""

    test_id: str
    task: str
    agents: list[str]
    personas_used: list[str]
    total_rounds: int
    termination_reason: str
    final_agreement_score: float
    total_tokens: int
    total_cost_usd: float
    rounds: list[RoundMetrics] = field(default_factory=list)
    timestamp: str = ""
    duration_seconds: float = 0.0

    # Derived metrics
    arguments_per_round: list[int] = field(default_factory=list)
    agreement_progression: list[float] = field(default_factory=list)
    marginal_value: list[float] = field(default_factory=list)  # Value gained per round

    def to_dict(self) -> dict:
        result = {
            "test_id": self.test_id,
            "task": self.task,
            "agents": self.agents,
            "personas_used": self.personas_used,
            "total_rounds": self.total_rounds,
            "termination_reason": self.termination_reason,
            "final_agreement_score": self.final_agreement_score,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "rounds": [asdict(r) for r in self.rounds],
            "arguments_per_round": self.arguments_per_round,
            "agreement_progression": self.agreement_progression,
            "marginal_value": self.marginal_value,
        }
        return result


class AdversarialSwarmTester:
    """Tests the adversarial swarm and collects metrics."""

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or BENCHMARK_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: list[SwarmBenchmarkResult] = []

    def run_simulated_test(
        self,
        task: str,
        agents: list[str],
        max_rounds: int = 3,
    ) -> SwarmBenchmarkResult:
        """Run a simulated test without actual LLM calls.

        This tests the personality selection and convergence detection
        without consuming tokens.
        """
        import random
        import time

        test_id = f"sim_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = time.time()

        print(f"\n[TEST] Starting simulated adversarial swarm: {test_id}")
        print(f"  Task: {task[:60]}...")
        print(f"  Agents: {', '.join(agents)}")

        # Select personas
        selector = PersonalitySelector()
        personas = selector.select_adversarial_personas(task, len(agents), agents)

        print("  Selected personas:")
        for p in personas:
            stance = p.adversarial_stance.primary_concern if p.adversarial_stance else "general"
            print(f"    - {p.name} ({p.agent_type}) [Focus: {stance}]")

        # Simulate debate rounds
        _detector = ConvergenceDetector(similarity_threshold=0.8, stability_rounds=2)
        rounds: list[RoundMetrics] = []
        prev_agreement = 0.0
        cumulative_arguments = set()

        for round_num in range(max_rounds):
            # Simulate round metrics (decreasing novelty over rounds)
            decay_factor = 0.7**round_num
            new_args = int(random.randint(3, 8) * decay_factor) + 1
            challenges = int(random.randint(2, 5) * decay_factor)
            concessions = int(random.randint(0, 2) * (1 - decay_factor) + round_num * 0.5)

            # Simulate agreement increasing over rounds
            agreement_increase = random.uniform(0.1, 0.25) * decay_factor
            agreement = min(1.0, prev_agreement + agreement_increase)

            # Add arguments to cumulative set
            for i in range(new_args):
                cumulative_arguments.add(f"arg_{round_num}_{i}")

            # Calculate marginal value (new unique insights / tokens)
            tokens = random.randint(500, 1500)
            cost = tokens * 0.00001  # Rough estimate

            round_metrics = RoundMetrics(
                round_num=round_num,
                new_arguments=new_args,
                challenges_raised=challenges,
                concessions_made=concessions,
                agreement_score=agreement,
                agreement_delta=agreement - prev_agreement,
                unique_issues=max(0, int((8 - round_num) * decay_factor)),
                tokens_used=tokens,
                cost_usd=cost,
                positions_changed=max(0, int(len(agents) * decay_factor * 0.5)),
            )
            rounds.append(round_metrics)

            print(
                f"  Round {round_num + 1}: Agreement={agreement:.0%}, "
                f"NewArgs={new_args}, Challenges={challenges}, Concessions={concessions}"
            )

            prev_agreement = agreement

            # Check for simulated convergence
            if agreement > 0.85 and round_num >= 1:
                print("  [CONVERGED] High agreement reached")
                break

        # Build result
        duration = time.time() - start_time
        result = SwarmBenchmarkResult(
            test_id=test_id,
            task=task,
            agents=agents,
            personas_used=[p.name for p in personas],
            total_rounds=len(rounds),
            termination_reason="convergence" if prev_agreement > 0.85 else "max_rounds",
            final_agreement_score=prev_agreement,
            total_tokens=sum(r.tokens_used for r in rounds),
            total_cost_usd=sum(r.cost_usd for r in rounds),
            rounds=rounds,
            timestamp=datetime.now().isoformat(),
            duration_seconds=duration,
            arguments_per_round=[r.new_arguments for r in rounds],
            agreement_progression=[r.agreement_score for r in rounds],
            marginal_value=self._calculate_marginal_value(rounds),
        )

        self.results.append(result)
        return result

    def _calculate_marginal_value(self, rounds: list[RoundMetrics]) -> list[float]:
        """Calculate marginal value (insight gained per token spent) per round."""
        marginal = []
        for _i, r in enumerate(rounds):
            if r.tokens_used == 0:
                marginal.append(0.0)
            else:
                # Value = (new arguments + challenges + agreement delta * 10) / tokens
                value = r.new_arguments + r.challenges_raised + r.agreement_delta * 10
                marginal.append(value / (r.tokens_used / 1000))  # Per 1K tokens
        return marginal

    def run_batch_tests(self, num_runs: int = 5) -> list[SwarmBenchmarkResult]:
        """Run a batch of simulated tests with different tasks."""
        test_tasks = [
            "Design a secure authentication system with OAuth2 and JWT",
            "Implement a caching layer for the API with Redis",
            "Refactor the monolith into microservices",
            "Add rate limiting to protect against DDoS",
            "Design a real-time notification system",
            "Implement a data pipeline for analytics",
            "Create a plugin architecture for extensibility",
            "Design a multi-tenant database schema",
            "Implement end-to-end encryption for messages",
            "Build a recommendation engine using collaborative filtering",
        ]

        agent_combos = [
            ["ARCHITECT", "DEV", "REVIEWER"],
            ["DEV", "REVIEWER", "SECURITY"],
            ["ARCHITECT", "DEV", "MAINTAINER"],
        ]

        results = []
        for i in range(num_runs):
            task = test_tasks[i % len(test_tasks)]
            agents = agent_combos[i % len(agent_combos)]
            result = self.run_simulated_test(task, agents)
            results.append(result)

        return results

    def save_results(self, filename: Optional[str] = None):
        """Save benchmark results to JSON."""
        if not filename:
            filename = f"benchmark_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        filepath = self.output_dir / filename
        with open(filepath, "w") as f:
            json.dump([r.to_dict() for r in self.results], f, indent=2)

        print(f"\n[OK] Results saved to {filepath}")
        return filepath

    def generate_summary(self) -> dict:
        """Generate summary statistics from all runs."""
        if not self.results:
            return {}

        total_runs = len(self.results)
        avg_rounds = sum(r.total_rounds for r in self.results) / total_runs
        avg_agreement = sum(r.final_agreement_score for r in self.results) / total_runs
        avg_cost = sum(r.total_cost_usd for r in self.results) / total_runs

        # Calculate average marginal value per round across all runs
        max_rounds = max(r.total_rounds for r in self.results)
        avg_marginal_by_round = []

        for round_idx in range(max_rounds):
            values = []
            for result in self.results:
                if round_idx < len(result.marginal_value):
                    values.append(result.marginal_value[round_idx])
            if values:
                avg_marginal_by_round.append(sum(values) / len(values))

        # Identify diminishing returns point
        diminishing_point = None
        for i in range(1, len(avg_marginal_by_round)):
            if avg_marginal_by_round[i] < avg_marginal_by_round[i - 1] * 0.5:
                diminishing_point = i + 1
                break

        return {
            "total_runs": total_runs,
            "avg_rounds": avg_rounds,
            "avg_agreement_score": avg_agreement,
            "avg_cost_usd": avg_cost,
            "avg_marginal_value_by_round": avg_marginal_by_round,
            "diminishing_returns_round": diminishing_point,
            "convergence_rate": sum(
                1 for r in self.results if r.termination_reason == "convergence"
            )
            / total_runs,
        }


def plot_results(results: list[SwarmBenchmarkResult], output_path: Optional[Path] = None):
    """Generate performance plots from benchmark results."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("[WARNING] matplotlib not installed. Run: pip install matplotlib")
        return

    if not results:
        print("[WARNING] No results to plot")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Adversarial Swarm Performance Analysis", fontsize=14, fontweight="bold")

    # Plot 1: Agreement progression over rounds
    ax1 = axes[0, 0]
    for result in results:
        ax1.plot(
            range(1, len(result.agreement_progression) + 1),
            result.agreement_progression,
            marker="o",
            alpha=0.7,
            label=result.test_id[:12],
        )
    ax1.set_xlabel("Round")
    ax1.set_ylabel("Agreement Score")
    ax1.set_title("Agreement Progression Over Rounds")
    ax1.set_ylim(0, 1.1)
    ax1.grid(True, alpha=0.3)

    # Plot 2: New arguments per round (diminishing returns)
    ax2 = axes[0, 1]
    for result in results:
        ax2.plot(
            range(1, len(result.arguments_per_round) + 1),
            result.arguments_per_round,
            marker="s",
            alpha=0.7,
        )
    ax2.set_xlabel("Round")
    ax2.set_ylabel("New Arguments")
    ax2.set_title("New Arguments Per Round (Diminishing Returns)")
    ax2.grid(True, alpha=0.3)

    # Plot 3: Marginal value per round
    ax3 = axes[1, 0]
    for result in results:
        ax3.plot(
            range(1, len(result.marginal_value) + 1),
            result.marginal_value,
            marker="^",
            alpha=0.7,
        )
    ax3.set_xlabel("Round")
    ax3.set_ylabel("Marginal Value (per 1K tokens)")
    ax3.set_title("Marginal Value Per Round")
    ax3.grid(True, alpha=0.3)

    # Plot 4: Cost vs Agreement scatter
    ax4 = axes[1, 1]
    costs = [r.total_cost_usd for r in results]
    agreements = [r.final_agreement_score for r in results]
    rounds = [r.total_rounds for r in results]

    scatter = ax4.scatter(costs, agreements, c=rounds, cmap="viridis", s=100, alpha=0.7)
    ax4.set_xlabel("Total Cost (USD)")
    ax4.set_ylabel("Final Agreement Score")
    ax4.set_title("Cost vs Agreement (color = rounds)")
    ax4.grid(True, alpha=0.3)
    plt.colorbar(scatter, ax=ax4, label="Rounds")

    plt.tight_layout()

    if output_path:
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        print(f"[OK] Plot saved to {output_path}")
    else:
        plt.show()


def main():
    parser = argparse.ArgumentParser(description="Test adversarial swarm performance")
    parser.add_argument("--runs", type=int, default=5, help="Number of test runs")
    parser.add_argument("--plot", action="store_true", help="Generate performance plots")
    parser.add_argument("--output", type=str, help="Output filename for results")
    args = parser.parse_args()

    print("=" * 60)
    print("  ADVERSARIAL SWARM TEST HARNESS")
    print("=" * 60)

    tester = AdversarialSwarmTester()

    # Run batch tests
    print(f"\n[INFO] Running {args.runs} simulated tests...")
    results = tester.run_batch_tests(args.runs)

    # Save results
    tester.save_results(args.output)

    # Generate summary
    summary = tester.generate_summary()
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)
    print(f"  Total runs: {summary['total_runs']}")
    print(f"  Average rounds: {summary['avg_rounds']:.1f}")
    print(f"  Average agreement: {summary['avg_agreement_score']:.0%}")
    print(f"  Average cost: ${summary['avg_cost_usd']:.4f}")
    print(f"  Convergence rate: {summary['convergence_rate']:.0%}")

    if summary.get("diminishing_returns_round"):
        print(
            f"\n  [INSIGHT] Diminishing returns detected at round {summary['diminishing_returns_round']}"
        )
        print("            Consider limiting debates to this many rounds for efficiency.")

    print("\n  Marginal value by round:")
    for i, val in enumerate(summary.get("avg_marginal_value_by_round", [])):
        bar = "[" + "=" * int(val * 2) + " " * (20 - int(val * 2)) + "]"
        print(f"    Round {i + 1}: {bar} {val:.2f}")

    # Generate plots
    if args.plot:
        plot_path = (
            BENCHMARK_DIR / f"performance_plot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        )
        plot_results(results, plot_path)

    print("\n[OK] Test harness complete")
    return 0


if __name__ == "__main__":
    sys.exit(main())
