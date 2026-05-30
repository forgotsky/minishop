#!/usr/bin/env python3
"""
Agent Router - Dynamic Agent Selection

Automatically selects the best agent(s) for a task based on:
- Task complexity analysis
- Code context and file types
- Historical performance data
- Task type detection (bug, feature, refactor, etc.)

Features:
- Smart task classification
- Multi-agent routing for complex tasks
- Confidence scoring
- Override support for manual selection

Usage:
    from lib.agent_router import AgentRouter, TaskAnalysis

    router = AgentRouter()
    result = router.route("Fix authentication bug in login.py")
    print(f"Recommended agents: {result.agents}")
    print(f"Confidence: {result.confidence}")
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# Configuration constants (can be overridden via environment or config)
CONFIDENCE_BASE = 0.3  # Base confidence score
CONFIDENCE_PATTERN_WEIGHT = 0.1  # Weight per detected pattern
CONFIDENCE_FILE_CONTEXT_WEIGHT = 0.1  # Weight per file context match
COMPLEXITY_SIMPLE_THRESHOLD = 2  # Complexity <= this is "simple"
COST_OPT_COMPLEXITY_THRESHOLD = 3  # Max complexity for cost optimization
MAX_ALTERNATIVES = 3  # Maximum alternative agents to suggest


class TaskType(Enum):
    """Types of development tasks."""

    FEATURE = "feature"  # New functionality
    BUGFIX = "bugfix"  # Bug fix
    REFACTOR = "refactor"  # Code restructuring
    SECURITY = "security"  # Security-related
    PERFORMANCE = "performance"  # Performance optimization
    DOCUMENTATION = "documentation"  # Docs update
    TESTING = "testing"  # Test addition/fix
    MIGRATION = "migration"  # Data/code migration
    TECH_DEBT = "tech_debt"  # Technical debt
    INVESTIGATION = "investigation"  # Code exploration
    ARCHITECTURE = "architecture"  # Design decisions
    QUICK_FIX = "quick_fix"  # Small, targeted fix


class Complexity(Enum):
    """Task complexity levels."""

    TRIVIAL = 1  # Single file, simple change
    LOW = 2  # Few files, straightforward
    MEDIUM = 3  # Multiple files, some complexity
    HIGH = 4  # Many files, complex logic
    CRITICAL = 5  # System-wide, critical path


@dataclass
class Agent:
    """Agent configuration."""

    name: str
    model: str
    specialties: list[str]
    cost_tier: str  # low, medium, high
    max_complexity: int  # Max complexity this agent handles well

    def __hash__(self):
        return hash(self.name)


# Agent definitions with specialties
AGENTS = {
    "SM": Agent(
        name="SM",
        model="sonnet",
        specialties=["planning", "context", "coordination", "review"],
        cost_tier="low",
        max_complexity=5,
    ),
    "DEV": Agent(
        name="DEV",
        model="opus",
        specialties=["implementation", "coding", "feature", "bugfix"],
        cost_tier="high",
        max_complexity=5,
    ),
    "BA": Agent(
        name="BA",
        model="sonnet",
        specialties=["requirements", "analysis", "user-stories", "acceptance-criteria"],
        cost_tier="low",
        max_complexity=3,
    ),
    "ARCHITECT": Agent(
        name="ARCHITECT",
        model="sonnet",
        specialties=["design", "architecture", "patterns", "system-design", "scalability"],
        cost_tier="low",
        max_complexity=5,
    ),
    "PM": Agent(
        name="PM",
        model="sonnet",
        specialties=["planning", "prioritization", "stakeholders", "roadmap"],
        cost_tier="low",
        max_complexity=3,
    ),
    "WRITER": Agent(
        name="WRITER",
        model="sonnet",
        specialties=["documentation", "readme", "api-docs", "tutorials"],
        cost_tier="low",
        max_complexity=3,
    ),
    "MAINTAINER": Agent(
        name="MAINTAINER",
        model="sonnet",  # Uses Opus for complex tasks
        specialties=["bugfix", "refactor", "tech-debt", "legacy", "maintenance"],
        cost_tier="medium",
        max_complexity=4,
    ),
    "REVIEWER": Agent(
        name="REVIEWER",
        model="opus",
        specialties=["review", "quality", "security", "best-practices", "critique"],
        cost_tier="high",
        max_complexity=5,
    ),
    "SECURITY": Agent(
        name="SECURITY",
        model="opus",
        specialties=["security", "vulnerabilities", "auth", "encryption", "penetration"],
        cost_tier="high",
        max_complexity=5,
    ),
}


# Keyword patterns for task type detection
TASK_PATTERNS = {
    TaskType.BUGFIX: [
        r"\bbug\b",
        r"\bfix\b",
        r"\berror\b",
        r"\bcrash\b",
        r"\bbroken\b",
        r"\bfailing\b",
        r"\bissue\b",
        r"\bdefect\b",
        r"\bregression\b",
    ],
    TaskType.SECURITY: [
        r"\bsecurity\b",
        r"\bvulnerability\b",
        r"\bauth\b",
        r"\bpassword\b",
        r"\btoken\b",
        r"\bencrypt\b",
        r"\bxss\b",
        r"\bsql.?injection\b",
        r"\bcve\b",
        r"\boauth\b",
        r"\bjwt\b",
        r"\bcors\b",
    ],
    TaskType.PERFORMANCE: [
        r"\bperformance\b",
        r"\bslow\b",
        r"\boptimize\b",
        r"\blatency\b",
        r"\bcache\b",
        r"\bmemory\b",
        r"\bcpu\b",
        r"\bprofile\b",
        r"\bbottleneck\b",
    ],
    TaskType.REFACTOR: [
        r"\brefactor\b",
        r"\brestructure\b",
        r"\bcleanup\b",
        r"\bclean.?up\b",
        r"\breorganize\b",
        r"\bsimplify\b",
        r"\bmodularize\b",
    ],
    TaskType.DOCUMENTATION: [
        r"\bdoc\b",
        r"\bdocument\b",
        r"\breadme\b",
        r"\bcomment\b",
        r"\bexplain\b",
        r"\bapi.?doc\b",
        r"\btutorial\b",
    ],
    TaskType.TESTING: [
        r"\btest\b",
        r"\bspec\b",
        r"\bcoverage\b",
        r"\bassert\b",
        r"\bmock\b",
        r"\bunit.?test\b",
        r"\bintegration.?test\b",
    ],
    TaskType.MIGRATION: [
        r"\bmigrat\b",
        r"\bupgrad\b",
        r"\bconvert\b",
        r"\bport\b",
        r"\bversion\b",
        r"\bdeprecate\b",
    ],
    TaskType.TECH_DEBT: [
        r"\btech.?debt\b",
        r"\btodo\b",
        r"\bfixme\b",
        r"\bhack\b",
        r"\bworkaround\b",
        r"\btemporary\b",
        r"\blegacy\b",
    ],
    TaskType.ARCHITECTURE: [
        r"\barchitect\b",
        r"\bdesign\b",
        r"\bpattern\b",
        r"\bstructure\b",
        r"\bscalable\b",
        r"\bmicroservice\b",
        r"\bmonolith\b",
        r"\bapi.?design\b",
    ],
    TaskType.INVESTIGATION: [
        r"\binvestigate\b",
        r"\bexplore\b",
        r"\banalyze\b",
        r"\bunderstand\b",
        r"\bresearch\b",
        r"\bspike\b",
        r"\bpoc\b",
    ],
}

# Pre-compile regex patterns for performance
COMPILED_TASK_PATTERNS: dict[TaskType, list[re.Pattern]] = {
    task_type: [re.compile(pattern, re.IGNORECASE) for pattern in patterns]
    for task_type, patterns in TASK_PATTERNS.items()
}

# File extension to specialty mapping
FILE_SPECIALTIES = {
    # Security-sensitive files
    ".pem": ["security"],
    ".key": ["security"],
    ".env": ["security"],
    # Documentation
    ".md": ["documentation"],
    ".rst": ["documentation"],
    ".txt": ["documentation"],
    # Test files
    "test_": ["testing"],
    "_test.": ["testing"],
    ".spec.": ["testing"],
    # Config files - often architectural
    ".yaml": ["architecture", "devops"],
    ".yml": ["architecture", "devops"],
    ".toml": ["architecture"],
    ".json": ["configuration"],
    # Database
    ".sql": ["database", "migration"],
    "migration": ["migration", "database"],
}


@dataclass
class TaskAnalysis:
    """Result of analyzing a task."""

    task_type: TaskType
    complexity: Complexity
    detected_patterns: list[str]
    file_contexts: list[str]
    confidence: float  # 0.0 to 1.0

    def to_dict(self) -> dict:
        return {
            "task_type": self.task_type.value,
            "complexity": self.complexity.value,
            "detected_patterns": self.detected_patterns,
            "file_contexts": self.file_contexts,
            "confidence": self.confidence,
        }


@dataclass
class RoutingResult:
    """Result of agent routing."""

    agents: list[str]  # Ordered list of recommended agents
    workflow: str  # sequential, parallel, swarm
    task_analysis: TaskAnalysis
    reasoning: str
    alternative_agents: list[str] = field(default_factory=list)
    model_overrides: dict[str, str] = field(default_factory=dict)  # agent -> model

    def to_dict(self) -> dict:
        return {
            "agents": self.agents,
            "workflow": self.workflow,
            "task_analysis": self.task_analysis.to_dict(),
            "reasoning": self.reasoning,
            "alternative_agents": self.alternative_agents,
            "model_overrides": self.model_overrides,
        }


class AgentRouter:
    """Dynamic agent selection based on task analysis."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.agents = AGENTS.copy()

    def analyze_task(self, description: str, files: Optional[list[str]] = None) -> TaskAnalysis:
        """
        Analyze a task to determine type and complexity.

        Args:
            description: Natural language description of the task to analyze.
                        Keywords in the description are matched against patterns
                        to determine task type (bugfix, security, feature, etc.)
            files: Optional list of file paths related to the task. Used to:
                   - Detect security-sensitive files (.pem, .key, .env)
                   - Identify documentation tasks (.md, .rst files)
                   - Detect test-related work (test_ prefixed files)
                   - Infer architectural scope from config files
                   If None, analysis is based solely on the description.

        Returns:
            TaskAnalysis object containing detected task type, complexity level,
            matched patterns, file contexts, and confidence score (0.0-1.0).
        """
        description_lower = description.lower()

        # Detect task type from pre-compiled patterns (faster than re.findall each time)
        type_scores: dict[TaskType, int] = {}
        detected_patterns: list[str] = []

        for task_type, compiled_patterns in COMPILED_TASK_PATTERNS.items():
            score = 0
            for pattern in compiled_patterns:
                matches = pattern.findall(description_lower)
                if matches:
                    score += len(matches)
                    detected_patterns.extend(matches)
            if score > 0:
                type_scores[task_type] = score

        # Determine primary task type
        if type_scores:
            task_type = max(type_scores.keys(), key=lambda t: type_scores[t])
        else:
            task_type = TaskType.FEATURE  # Default

        # Analyze file contexts
        file_contexts: list[str] = []
        if files:
            for file_path in files:
                for pattern, specialties in FILE_SPECIALTIES.items():
                    if pattern in file_path.lower():
                        file_contexts.extend(specialties)

        # Estimate complexity
        complexity = self._estimate_complexity(description, files)

        # Calculate confidence using configurable weights
        confidence = min(
            1.0,
            CONFIDENCE_BASE
            + (CONFIDENCE_PATTERN_WEIGHT * len(detected_patterns))
            + (CONFIDENCE_FILE_CONTEXT_WEIGHT * len(file_contexts)),
        )

        return TaskAnalysis(
            task_type=task_type,
            complexity=complexity,
            detected_patterns=list(set(detected_patterns)),
            file_contexts=list(set(file_contexts)),
            confidence=confidence,
        )

    def _estimate_complexity(
        self, description: str, files: Optional[list[str]] = None
    ) -> Complexity:
        """Estimate task complexity."""
        score = 1

        # Description-based heuristics
        complexity_indicators = {
            "simple": -1,
            "trivial": -1,
            "minor": -1,
            "quick": -1,
            "complex": 2,
            "difficult": 2,
            "critical": 3,
            "major": 2,
            "redesign": 3,
            "rewrite": 3,
            "overhaul": 3,
            "multiple": 1,
            "several": 1,
            "many": 2,
            "across": 1,
            "throughout": 2,
            "system-wide": 3,
        }

        desc_lower = description.lower()
        for indicator, delta in complexity_indicators.items():
            if indicator in desc_lower:
                score += delta

        # File count based
        if files:
            file_count = len(files)
            if file_count > 10:
                score += 2
            elif file_count > 5:
                score += 1

        # Clamp to valid range
        score = max(1, min(5, score))

        return Complexity(score)

    def route(
        self,
        description: str,
        files: Optional[list[str]] = None,
        prefer_cost: bool = False,
        force_agents: Optional[list[str]] = None,
    ) -> RoutingResult:
        """Route a task to the appropriate agent(s)."""

        # Allow manual override
        if force_agents:
            analysis = self.analyze_task(description, files)
            return RoutingResult(
                agents=force_agents,
                workflow="sequential",
                task_analysis=analysis,
                reasoning="Manual agent selection override",
            )

        # Analyze the task
        analysis = self.analyze_task(description, files)

        # Select agents based on task type and complexity
        agents, workflow, reasoning = self._select_agents(analysis, prefer_cost)

        # Determine model overrides for complex tasks
        model_overrides = {}
        if analysis.complexity.value >= 4:
            # Use Opus for complex tasks even for typically Sonnet agents
            for agent in agents:
                if self.agents[agent].cost_tier == "low":
                    model_overrides[agent] = "opus"

        # Find alternative agents
        alternatives = self._find_alternatives(agents, analysis)

        return RoutingResult(
            agents=agents,
            workflow=workflow,
            task_analysis=analysis,
            reasoning=reasoning,
            alternative_agents=alternatives,
            model_overrides=model_overrides,
        )

    def _select_agents(
        self, analysis: TaskAnalysis, prefer_cost: bool
    ) -> tuple[list[str], str, str]:
        """Select agents based on task analysis."""

        task_type = analysis.task_type
        complexity = analysis.complexity

        # Define routing rules
        routing_rules = {
            TaskType.FEATURE: {
                "simple": (["DEV"], "sequential", "Direct implementation"),
                "complex": (
                    ["SM", "ARCHITECT", "DEV", "REVIEWER"],
                    "sequential",
                    "Full pipeline for complex feature",
                ),
            },
            TaskType.BUGFIX: {
                "simple": (["MAINTAINER"], "sequential", "Simple bug fix"),
                "complex": (
                    ["DEV", "REVIEWER"],
                    "sequential",
                    "Complex bug requires senior review",
                ),
            },
            TaskType.SECURITY: {
                "simple": (["SECURITY", "DEV"], "sequential", "Security fix with review"),
                "complex": (
                    ["SECURITY", "DEV", "REVIEWER"],
                    "swarm",
                    "Critical security requires multi-agent review",
                ),
            },
            TaskType.PERFORMANCE: {
                "simple": (["DEV"], "sequential", "Performance optimization"),
                "complex": (
                    ["ARCHITECT", "DEV", "REVIEWER"],
                    "sequential",
                    "Architectural review for performance",
                ),
            },
            TaskType.REFACTOR: {
                "simple": (["MAINTAINER"], "sequential", "Simple refactor"),
                "complex": (
                    ["ARCHITECT", "DEV", "REVIEWER"],
                    "sequential",
                    "Architectural oversight for major refactor",
                ),
            },
            TaskType.DOCUMENTATION: {
                "simple": (["WRITER"], "sequential", "Documentation update"),
                "complex": (["BA", "WRITER"], "sequential", "Requirements review before docs"),
            },
            TaskType.TESTING: {
                "simple": (["DEV"], "sequential", "Test implementation"),
                "complex": (["DEV", "REVIEWER"], "sequential", "Test review for coverage"),
            },
            TaskType.MIGRATION: {
                "simple": (["MAINTAINER"], "sequential", "Simple migration"),
                "complex": (
                    ["ARCHITECT", "DEV", "REVIEWER"],
                    "sequential",
                    "Full review for migration",
                ),
            },
            TaskType.TECH_DEBT: {
                "simple": (["MAINTAINER"], "sequential", "Tech debt cleanup"),
                "complex": (
                    ["ARCHITECT", "MAINTAINER", "REVIEWER"],
                    "sequential",
                    "Architectural review for major cleanup",
                ),
            },
            TaskType.ARCHITECTURE: {
                "simple": (["ARCHITECT"], "sequential", "Design decision"),
                "complex": (["ARCHITECT", "DEV", "REVIEWER"], "swarm", "Multi-agent design review"),
            },
            TaskType.INVESTIGATION: {
                "simple": (["SM"], "sequential", "Code exploration"),
                "complex": (
                    ["SM", "ARCHITECT"],
                    "sequential",
                    "Deep analysis with architecture context",
                ),
            },
            TaskType.QUICK_FIX: {
                "simple": (["MAINTAINER"], "sequential", "Quick targeted fix"),
                "complex": (["MAINTAINER"], "sequential", "Quick fix"),
            },
        }

        # Determine complexity level
        complexity_level = (
            "simple" if complexity.value <= COMPLEXITY_SIMPLE_THRESHOLD else "complex"
        )

        # Get routing
        rule = routing_rules.get(task_type, {}).get(complexity_level)
        if not rule:
            rule = (["DEV"], "sequential", "Default routing")

        agents, workflow, reasoning = rule

        # Cost optimization
        if prefer_cost and complexity.value <= COST_OPT_COMPLEXITY_THRESHOLD:
            # Replace Opus agents with Sonnet equivalents where possible
            cost_effective_agents = []
            for agent in agents:
                if agent == "REVIEWER" and complexity.value <= COMPLEXITY_SIMPLE_THRESHOLD:
                    cost_effective_agents.append("SM")  # SM can do simple reviews
                else:
                    cost_effective_agents.append(agent)
            agents = cost_effective_agents
            reasoning += " (cost-optimized)"

        return agents, workflow, reasoning

    def _find_alternatives(self, primary: list[str], analysis: TaskAnalysis) -> list[str]:
        """Find alternative agents that could handle the task."""
        alternatives = []

        for name, agent in self.agents.items():
            if name in primary:
                continue

            # Check if agent specialties match any file contexts or detected patterns
            matches = set(agent.specialties) & (
                set(analysis.file_contexts) | {p.lower() for p in analysis.detected_patterns}
            )

            if matches and agent.max_complexity >= analysis.complexity.value:
                alternatives.append(name)

        return alternatives[:MAX_ALTERNATIVES]

    def get_workflow_for_agents(self, agents: list[str]) -> str:
        """Determine the best workflow for a set of agents."""
        if len(agents) == 1:
            return "single"

        # If includes ARCHITECT, likely needs sequential
        if "ARCHITECT" in agents:
            return "sequential"

        # If 3+ agents with REVIEWER, consider swarm
        if len(agents) >= 3 and "REVIEWER" in agents:
            return "swarm"

        return "sequential"

    def explain_routing(self, result: RoutingResult) -> str:
        """Generate a human-readable explanation of the routing decision."""
        lines = [
            "**Task Analysis**",
            f"  - Type: {result.task_analysis.task_type.value}",
            f"  - Complexity: {result.task_analysis.complexity.name} ({result.task_analysis.complexity.value}/5)",
            f"  - Confidence: {result.task_analysis.confidence:.0%}",
            "",
            "**Recommended Agents**",
        ]

        for i, agent in enumerate(result.agents, 1):
            agent_info = self.agents.get(agent)
            model = result.model_overrides.get(agent, agent_info.model if agent_info else "sonnet")
            lines.append(f"  {i}. **{agent}** (model: {model})")

        lines.extend(
            [
                "",
                f" **Workflow**: {result.workflow}",
                f" **Reasoning**: {result.reasoning}",
            ]
        )

        if result.alternative_agents:
            lines.extend(["", f"**Alternatives**: {', '.join(result.alternative_agents)}"])

        if result.task_analysis.detected_patterns:
            lines.extend(
                [
                    "",
                    f" **Detected patterns**: {', '.join(result.task_analysis.detected_patterns[:5])}",
                ]
            )

        return "\n".join(lines)


# Convenience functions
def route_task(description: str, files: Optional[list[str]] = None) -> RoutingResult:
    """Quick routing of a task."""
    router = AgentRouter()
    return router.route(description, files)


def explain_route(description: str, files: Optional[list[str]] = None) -> str:
    """Get an explanation of how a task would be routed."""
    router = AgentRouter()
    result = router.route(description, files)
    return router.explain_routing(result)


if __name__ == "__main__":
    # Demo usage
    print("=== Agent Router Demo ===\n")

    router = AgentRouter()

    test_cases = [
        "Fix login authentication bug in auth.py",
        "Add user profile feature with photo upload",
        "Security vulnerability in password hashing",
        "Refactor payment service for better maintainability",
        "Update README with new API documentation",
        "Performance optimization for database queries",
        "Investigate memory leak in production",
        "Migrate from React 17 to React 18",
    ]

    for task in test_cases:
        print(f'Task: "{task}"')
        result = router.route(task)
        print(router.explain_routing(result))
        print("\n" + "=" * 60 + "\n")
