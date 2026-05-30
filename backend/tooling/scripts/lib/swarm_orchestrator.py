#!/usr/bin/env python3
"""
Swarm Orchestrator - Adversarial Multi-Agent Collaboration System

Orchestrates multiple agents in ADVERSARIAL debate mode where agents
take opposing stances and challenge each other's designs. This creates
robust solutions through competitive pressure.

Features:
- Adversarial personas: Agents are assigned opposing viewpoints
- Dynamic personality selection: Task analysis determines best persona mix
- Convergence detection: Hybrid token/round limits with stability checks
- Personality handoff: Debate summary passed to implementing agent
- Cross-challenge rounds: Agents directly challenge each other

The adversarial approach:
1. General agent (e.g., DEV) receives task
2. Spawns sub-agents with opposing personas (e.g., Security vs Velocity)
3. Agents debate in rounds, challenging each other's positions
4. Convergence is forced after budget/round limits
5. Synthesized result returned to implementing agent

Usage:
    from lib.swarm_orchestrator import SwarmOrchestrator, SwarmConfig

    orchestrator = SwarmOrchestrator(story_key="3-5")
    result = orchestrator.run_swarm(
        agents=["ARCHITECT", "DEV", "REVIEWER"],
        task="Design and implement user authentication",
        max_iterations=5
    )
    # result includes PersonalityHandoff with debate summary
"""

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Optional

# Import dependencies
try:
    from lib.agent_handoff import HandoffGenerator
    from lib.agent_router import AgentRouter
    from lib.personality_system import (
        ConvergenceDetector,
        DebatePosition,
        PersonalityHandoff,
        PersonalityProfile,
        PersonalitySelector,
        extract_arguments_from_response,
    )
    from lib.platform import IS_WINDOWS
    from lib.shared_memory import get_knowledge_graph, get_shared_memory
except ImportError:
    # Fallback for when running from lib directory
    import sys as _sys

    IS_WINDOWS = _sys.platform == "win32"
    from agent_handoff import HandoffGenerator
    from agent_router import AgentRouter
    from personality_system import (
        ConvergenceDetector,
        DebatePosition,
        PersonalityHandoff,
        PersonalityProfile,
        PersonalitySelector,
        extract_arguments_from_response,
    )
    from shared_memory import get_knowledge_graph, get_shared_memory

# Try to import validation loop
try:
    from validation_loop import (
        INTER_PHASE_GATES,
        LoopContext,
        ValidationLoop,
    )

    HAS_VALIDATION = True
except ImportError:
    try:
        from lib.validation_loop import (
            INTER_PHASE_GATES,
            LoopContext,
            ValidationLoop,
        )

        HAS_VALIDATION = True
    except ImportError:
        HAS_VALIDATION = False


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
CLAUDE_CLI = "claude.cmd" if IS_WINDOWS else "claude"

# Security: Maximum prompt length to prevent resource exhaustion
MAX_PROMPT_LENGTH = 500_000  # ~500KB


def _sanitize_prompt(prompt: str) -> str:
    """Sanitize prompt for safe subprocess execution.

    - Removes null bytes and control characters (except newlines/tabs)
    - Truncates to maximum length
    - Ensures valid UTF-8

    Args:
        prompt: Raw prompt string

    Returns:
        Sanitized prompt safe for subprocess
    """
    if not prompt:
        return ""

    # Remove null bytes and control characters (keep newlines, tabs, and printable chars)
    # Keep: \n (10), \t (9), \r (13), and all chars >= 32 (printable ASCII + UTF-8)
    sanitized = "".join(char for char in prompt if char in "\n\t\r" or ord(char) >= 32)

    # Truncate if too long
    if len(sanitized) > MAX_PROMPT_LENGTH:
        sanitized = sanitized[:MAX_PROMPT_LENGTH] + "\n[TRUNCATED]"

    return sanitized


class SwarmState(Enum):
    """State of the swarm orchestration."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    DEBATING = "debating"
    CONVERGING = "converging"
    CONSENSUS = "consensus"
    COMPLETED = "completed"
    FAILED = "failed"
    MAX_ITERATIONS = "max_iterations"


class ConsensusType(Enum):
    """Types of consensus mechanisms."""

    UNANIMOUS = "unanimous"  # All must agree
    MAJORITY = "majority"  # >50% agree
    QUORUM = "quorum"  # N of M agree
    REVIEWER_APPROVAL = "reviewer_approval"  # REVIEWER must approve


@dataclass
class AgentResponse:
    """Response from an agent in adversarial debate."""

    agent: str
    model: str
    content: str
    timestamp: str
    iteration: int
    tokens_used: int = 0
    cost_usd: float = 0.0
    issues_found: list[str] = field(default_factory=list)
    approvals: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    vote: Optional[str] = None  # approve, reject, abstain
    # Adversarial debate fields
    persona_name: Optional[str] = None
    challenges_raised: list[str] = field(default_factory=list)
    concessions_made: list[str] = field(default_factory=list)
    key_arguments: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "model": self.model,
            "content": self.content[:500] + "..." if len(self.content) > 500 else self.content,
            "timestamp": self.timestamp,
            "iteration": self.iteration,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
            "issues_found": self.issues_found,
            "approvals": self.approvals,
            "suggestions": self.suggestions,
            "vote": self.vote,
            "persona_name": self.persona_name,
            "challenges_raised": self.challenges_raised,
            "key_arguments": self.key_arguments[:5],
        }


@dataclass
class SwarmIteration:
    """One iteration of the swarm."""

    iteration_num: int
    responses: list[AgentResponse] = field(default_factory=list)
    consensus_reached: bool = False
    issues_remaining: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "iteration_num": self.iteration_num,
            "responses": [r.to_dict() for r in self.responses],
            "consensus_reached": self.consensus_reached,
            "issues_remaining": self.issues_remaining,
            "decisions_made": self.decisions_made,
        }


@dataclass
class SwarmResult:
    """Result of adversarial swarm orchestration."""

    story_key: str
    task: str
    state: SwarmState
    iterations: list[SwarmIteration]
    final_output: str
    agents_involved: list[str]
    total_tokens: int
    total_cost_usd: float
    start_time: str
    end_time: str
    consensus_type: ConsensusType
    # Adversarial debate results
    personality_handoff: Optional[PersonalityHandoff] = None
    termination_reason: str = "max_iterations"  # consensus, convergence, budget, max_iterations

    def to_dict(self) -> dict:
        return {
            "story_key": self.story_key,
            "task": self.task,
            "state": self.state.value,
            "iterations": [i.to_dict() for i in self.iterations],
            "final_output": self.final_output,
            "agents_involved": self.agents_involved,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "consensus_type": self.consensus_type.value,
            "termination_reason": self.termination_reason,
            "personality_handoff": (
                self.personality_handoff.to_dict() if self.personality_handoff else None
            ),
        }

    def to_summary(self) -> str:
        """Generate a human-readable summary of the adversarial debate."""
        lines = [
            f"## Adversarial Swarm Result: {self.story_key}",
            "",
            f"**Task**: {self.task}",
            f"**State**: {self.state.value}",
            f"**Debate Rounds**: {len(self.iterations)}",
            f"**Termination**: {self.termination_reason}",
            f"**Total Cost**: ${self.total_cost_usd:.4f}",
            "",
        ]

        # Show participating personas
        if self.personality_handoff:
            lines.append("### Adversarial Personas")
            for p in self.personality_handoff.selected_personas:
                stance = (
                    f" [Focus: {p.adversarial_stance.primary_concern}]"
                    if p.adversarial_stance
                    else ""
                )
                lines.append(f"- **{p.name}** ({p.agent_type}){stance}")
            lines.append("")

        if self.state == SwarmState.CONSENSUS:
            lines.append("[CONSENSUS] Agents reached agreement!")
        elif self.termination_reason == "convergence":
            lines.append("[CONVERGED] Positions stabilized - forcing consensus")
        elif self.termination_reason == "budget":
            lines.append("[BUDGET] Token budget reached - forcing consensus")
        elif self.state == SwarmState.MAX_ITERATIONS:
            lines.append("[MAX ROUNDS] Iteration limit reached")

        # Show consensus points and tensions
        if self.personality_handoff:
            if self.personality_handoff.consensus_points:
                lines.append("")
                lines.append("### Points of Agreement")
                for point in self.personality_handoff.consensus_points:
                    lines.append(f"- {point}")

            if self.personality_handoff.unresolved_tensions:
                lines.append("")
                lines.append("### Unresolved Tensions")
                for tension in self.personality_handoff.unresolved_tensions:
                    lines.append(f"- [WARNING] {tension}")

            lines.append("")
            lines.append("### Recommended Approach")
            lines.append(self.personality_handoff.recommended_approach)

        lines.append("")
        lines.append("### Final Output")
        lines.append(
            self.final_output[:1000] if len(self.final_output) > 1000 else self.final_output
        )

        return "\n".join(lines)


@dataclass
class SwarmConfig:
    """Configuration for adversarial swarm orchestration."""

    max_iterations: int = 3  # Limited to 3 rounds - diminishing returns after this
    consensus_type: ConsensusType = ConsensusType.MAJORITY
    quorum_size: int = 2  # For QUORUM type
    timeout_seconds: int = 300
    parallel_execution: bool = False
    auto_fix_enabled: bool = True  # DEV automatically addresses REVIEWER issues
    verbose: bool = True
    budget_limit_usd: float = 10.0  # Budget for debate
    validation_enabled: bool = True  # Enable inter-iteration validation
    # Adversarial-specific settings
    convergence_threshold: float = 0.8  # Position similarity to consider converged
    stability_rounds: int = 2  # Rounds of stability before convergence
    force_consensus_on_budget: bool = True  # Force agreement when budget exhausted
    cross_challenge_enabled: bool = True  # Agents directly challenge each other

    def to_dict(self) -> dict:
        return {
            "max_iterations": self.max_iterations,
            "consensus_type": self.consensus_type.value,
            "quorum_size": self.quorum_size,
            "timeout_seconds": self.timeout_seconds,
            "parallel_execution": self.parallel_execution,
            "auto_fix_enabled": self.auto_fix_enabled,
            "budget_limit_usd": self.budget_limit_usd,
            "validation_enabled": self.validation_enabled,
            "convergence_threshold": self.convergence_threshold,
            "stability_rounds": self.stability_rounds,
            "cross_challenge_enabled": self.cross_challenge_enabled,
        }


class SwarmOrchestrator:
    """Orchestrates adversarial multi-agent collaboration.

    Agents are assigned opposing personas and debate until consensus
    or convergence is reached. This creates robust solutions through
    competitive pressure and cross-examination.
    """

    def __init__(self, story_key: str, config: Optional[SwarmConfig] = None):
        self.story_key = story_key
        self.config = config or SwarmConfig()
        self.project_root = PROJECT_ROOT
        self.shared_memory = get_shared_memory(story_key)
        self.knowledge_graph = get_knowledge_graph(story_key)
        self.handoff_generator = HandoffGenerator(story_key)
        self.router = AgentRouter()

        self.state = SwarmState.INITIALIZING
        self.iterations: list[SwarmIteration] = []
        self.total_tokens = 0
        self.total_cost = 0.0
        self.termination_reason = "max_iterations"

        # Adversarial personality system
        self.personality_selector = PersonalitySelector()
        self.convergence_detector = ConvergenceDetector(
            similarity_threshold=self.config.convergence_threshold,
            stability_rounds=self.config.stability_rounds,
        )
        self.selected_personas: list[PersonalityProfile] = []
        self.agent_personas: dict[str, PersonalityProfile] = {}
        self.debate_positions: dict[str, DebatePosition] = {}

        # Agent model mapping (can be overridden by persona)
        self.agent_models = {
            "SM": "sonnet",
            "DEV": "opus",
            "REVIEWER": "opus",
            "ARCHITECT": "sonnet",
            "BA": "sonnet",
            "PM": "sonnet",
            "WRITER": "sonnet",
            "MAINTAINER": "sonnet",
            "SECURITY": "opus",
        }

        # Initialize validation loop if available and enabled
        self.validation_loop = None
        self.validation_context = None
        if HAS_VALIDATION and self.config.validation_enabled:
            self.validation_loop = ValidationLoop(
                gates=INTER_PHASE_GATES,
                config={"auto_fix_enabled": self.config.auto_fix_enabled},
                story_key=story_key,
            )
            self.validation_context = LoopContext(
                story_key=story_key,
                max_iterations=self.config.max_iterations,
            )

    def _log(self, message: str, level: str = "INFO"):
        """Log a message with timestamp."""
        if self.config.verbose:
            timestamp = datetime.now().strftime("%H:%M:%S")
            emoji = {
                "INFO": "[INFO]",
                "SUCCESS": "",
                "WARNING": "",
                "ERROR": "",
                "DEBUG": "",
            }.get(level, "•")
            print(f"[{timestamp}] {emoji} {message}")

    def _select_adversarial_personas(self, agents: list[str], task: str):
        """Select adversarial personas for the given agents and task."""
        self._log("Selecting adversarial personas for debate...")

        # Get personas from personality selector
        self.selected_personas = self.personality_selector.select_adversarial_personas(
            task=task,
            num_agents=len(agents),
            required_agents=agents,
        )

        # Map personas to agents
        for i, agent in enumerate(agents):
            if i < len(self.selected_personas):
                persona = self.selected_personas[i]
                self.agent_personas[agent] = persona
                # Override model if persona specifies
                if persona.model:
                    self.agent_models[agent] = persona.model
                self._log(
                    f"  {agent} -> {persona.name} "
                    f"[{persona.adversarial_stance.primary_concern if persona.adversarial_stance else 'general'}]"
                )

                # Initialize debate position tracking
                self.debate_positions[agent] = DebatePosition(
                    agent=agent,
                    persona_name=persona.name,
                )

    def _invoke_agent(self, agent: str, prompt: str, iteration: int = 0) -> AgentResponse:
        """Invoke a single agent with Claude CLI, including adversarial persona."""
        model = self.agent_models.get(agent, "sonnet")
        persona = self.agent_personas.get(agent)
        persona_name = persona.name if persona else None

        persona_label = f" as '{persona_name}'" if persona_name else ""
        self._log(f"Invoking {agent}{persona_label} (model: {model})...")

        # Build the full prompt with context and persona
        context = self.handoff_generator.generate_context_for_agent(agent)

        # Inject persona if available
        persona_injection = ""
        if persona:
            persona_injection = persona.to_prompt_injection() + "\n\n---\n\n"

        full_prompt = _sanitize_prompt(f"{persona_injection}{context}\n\n---\n\n{prompt}")

        try:
            result = subprocess.run(
                [CLAUDE_CLI, "--print", "--model", model, "-p", full_prompt],
                capture_output=True,
                text=True,
                timeout=self.config.timeout_seconds,
                cwd=str(self.project_root),
            )

            content = result.stdout + result.stderr

            # Parse response for issues, approvals, suggestions
            issues = self._extract_issues(content)
            approvals = self._extract_approvals(content)
            suggestions = self._extract_suggestions(content)
            vote = self._determine_vote(content, issues, approvals)

            # Extract adversarial elements
            key_arguments = extract_arguments_from_response(content)
            challenges = self._extract_challenges(content)
            concessions = self._extract_concessions(content)

            # Update debate position
            if agent in self.debate_positions:
                pos = self.debate_positions[agent]
                pos.key_arguments = key_arguments
                pos.challenges_raised = challenges
                pos.concessions_made.extend(concessions)

            # Estimate tokens (rough)
            tokens = len(full_prompt.split()) + len(content.split())
            cost = self._estimate_cost(tokens, model)

            self.total_tokens += tokens
            self.total_cost += cost

            return AgentResponse(
                agent=agent,
                model=model,
                content=content,
                timestamp=datetime.now().isoformat(),
                iteration=iteration,
                tokens_used=tokens,
                cost_usd=cost,
                issues_found=issues,
                approvals=approvals,
                suggestions=suggestions,
                vote=vote,
                persona_name=persona_name,
                challenges_raised=challenges,
                concessions_made=concessions,
                key_arguments=key_arguments,
            )

        except subprocess.TimeoutExpired:
            self._log(f"{agent} timed out", "WARNING")
            return AgentResponse(
                agent=agent,
                model=model,
                content="[TIMEOUT]",
                timestamp=datetime.now().isoformat(),
                iteration=iteration,
                vote="abstain",
                persona_name=persona_name,
            )
        except Exception as e:
            self._log(f"{agent} failed: {e}", "ERROR")
            return AgentResponse(
                agent=agent,
                model=model,
                content=f"[ERROR: {str(e)}]",
                timestamp=datetime.now().isoformat(),
                iteration=iteration,
                vote="abstain",
                persona_name=persona_name,
            )

    def _extract_challenges(self, content: str) -> list[str]:
        """Extract challenges/objections from adversarial response."""
        challenges = []
        patterns = [
            r"(?:I challenge|I disagree|I object|However|But|My concern is)[\s:]+(.+?)(?:\.|$)",
            r"(?:This ignores|This overlooks|What about)[\s:]+(.+?)(?:\.|$)",
            r"\[CHALLENGE\]\s*(.+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            challenges.extend(matches)

        return list({c.strip() for c in challenges if len(c) > 10})[:5]

    def _extract_concessions(self, content: str) -> list[str]:
        """Extract concessions from adversarial response."""
        concessions = []
        patterns = [
            r"(?:I concede|I agree that|Fair point|You're right that|I accept)[\s:]+(.+?)(?:\.|$)",
            r"(?:On reflection|Reconsidering)[\s:]+(.+?)(?:\.|$)",
            r"\[CONCEDE\]\s*(.+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            concessions.extend(matches)

        return list({c.strip() for c in concessions if len(c) > 10})[:5]

    def _extract_issues(self, content: str) -> list[str]:
        """Extract issues/problems from response."""
        issues = []
        patterns = [
            r"(?:issue|problem|bug|error|fix needed|must fix|should fix):\s*(.+)",
            r"\s*(.+)",
            r"\[ISSUE\]\s*(.+)",
            r"- (?:Issue|Problem|Bug):\s*(.+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            issues.extend(matches)

        return list(set(issues))[:10]  # Limit to 10

    def _extract_approvals(self, content: str) -> list[str]:
        """Extract approvals/LGTMs from response."""
        approvals = []
        patterns = [
            r"(?:lgtm|approved|looks good|well done|excellent)[\s:]*(.+)?",
            r"\s*(.+)",
            r"\[APPROVED\]\s*(.+)?",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            for match in matches:
                approvals.append(match if match else "Approved")

        return list(set(approvals))[:5]

    def _extract_suggestions(self, content: str) -> list[str]:
        """Extract suggestions from response."""
        suggestions = []
        patterns = [
            r"(?:suggest|consider|recommend|might want to|could):\s*(.+)",
            r"\s*(.+)",
            r"\[SUGGESTION\]\s*(.+)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, content, re.IGNORECASE | re.MULTILINE)
            suggestions.extend(matches)

        return list(set(suggestions))[:5]

    def _determine_vote(self, content: str, issues: list[str], approvals: list[str]) -> str:
        """Determine agent's vote based on response."""
        content_lower = content.lower()

        # Explicit votes
        if any(
            word in content_lower for word in ["approved", "lgtm", "ship it", "looks good to me"]
        ):
            return "approve"
        if any(
            word in content_lower for word in ["rejected", "do not merge", "needs work", "blocking"]
        ):
            return "reject"

        # Implicit from issues/approvals
        if len(issues) > len(approvals):
            return "reject"
        if len(approvals) > 0 and len(issues) == 0:
            return "approve"

        return "abstain"

    def _estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost in USD."""
        # Approximate pricing per 1M tokens
        pricing = {
            "opus": {"input": 15.0, "output": 75.0},
            "sonnet": {"input": 3.0, "output": 15.0},
            "haiku": {"input": 0.8, "output": 4.0},
        }

        rates = pricing.get(model, pricing["sonnet"])
        # Assume 50/50 input/output split
        cost = (tokens / 2 / 1_000_000 * rates["input"]) + (
            tokens / 2 / 1_000_000 * rates["output"]
        )
        return cost

    def _check_consensus(self, responses: list[AgentResponse]) -> bool:
        """Check if consensus is reached based on config."""
        votes = [r.vote for r in responses if r.vote]
        approvals = votes.count("approve")
        rejects = votes.count("reject")
        total = len(votes)

        if total == 0:
            return False

        if self.config.consensus_type == ConsensusType.UNANIMOUS:
            return approvals == total

        elif self.config.consensus_type == ConsensusType.MAJORITY:
            return approvals > total / 2

        elif self.config.consensus_type == ConsensusType.QUORUM:
            return approvals >= self.config.quorum_size

        elif self.config.consensus_type == ConsensusType.REVIEWER_APPROVAL:
            reviewer_responses = [r for r in responses if r.agent == "REVIEWER"]
            if not reviewer_responses:
                return approvals > rejects
            return reviewer_responses[0].vote == "approve"

        return False

    def _collect_issues(self, responses: list[AgentResponse]) -> list[str]:
        """Collect all unique issues from responses."""
        all_issues = []
        for r in responses:
            all_issues.extend(r.issues_found)
        return list(set(all_issues))

    def _run_iteration_validation(self, iteration: int, responses: list[AgentResponse]) -> bool:
        """Run validation between iterations.

        Args:
            iteration: Current iteration number
            responses: Agent responses from this iteration

        Returns:
            True if validation passed, False otherwise
        """
        if not self.validation_loop or not self.validation_context:
            return True

        self.validation_context.iteration = iteration
        self.validation_context.phase = f"iteration_{iteration}"

        # Update context with iteration data
        self.validation_context.accumulated_issues = self._collect_issues(responses)

        report = self.validation_loop.run_gates(self.validation_context, tier=2)

        if report.passed:
            self._log(f"[VALIDATION] Iteration {iteration + 1} passed validation")
            return True
        else:
            # Log warnings but don't block swarm - just record issues
            for failure in report.failures:
                self._log(f"[VALIDATION] {failure.gate_name}: {failure.message}", "WARN")
                # Add to accumulated issues for next iteration
                self.validation_context.accumulated_issues.append(
                    f"Validation: {failure.gate_name} - {failure.message}"
                )
            return True  # Don't block swarm, just inform

    def _build_iteration_prompt(
        self,
        agent: str,
        task: str,
        iteration: int,
        previous_responses: list[AgentResponse],
        issues_to_fix: list[str],
    ) -> str:
        """Build adversarial debate prompt for a specific iteration."""
        persona = self.agent_personas.get(agent)
        stance_info = ""
        if persona and persona.adversarial_stance:
            stance = persona.adversarial_stance
            stance_info = f"""
Your stance in this debate:
- Primary concern: {stance.primary_concern}
- Challenge arguments that prioritize: {', '.join(stance.opposes) if stance.opposes else 'shortcuts or poor quality'}
- Debate style: {stance.debate_style}
"""

        if iteration == 0:
            # First iteration - state position and challenge others
            return f"""## ADVERSARIAL DEBATE - Round 1

You are the {agent} agent participating in an adversarial design debate.
Your goal is to advocate for your perspective while challenging others.

### The Task
{task}

{stance_info}

### Instructions
1. State your position on how to approach this task
2. Identify potential issues, risks, or overlooked concerns
3. Be specific about what approach you advocate for and WHY
4. Anticipate counter-arguments and address them preemptively

### Response Format
Structure your response with:
- **My Position**: Your recommended approach
- **Key Arguments**: Why this is the right approach (be specific)
- **Concerns**: What could go wrong with other approaches
- **Challenges for Others**: Questions or objections for other agents to address

At the end, indicate: APPROVE (if you'd accept current direction) or ISSUES (if concerns remain)
"""

        # Subsequent iterations - adversarial cross-challenge
        other_positions = []
        for r in previous_responses:
            if r.agent == agent:
                continue

            persona_label = f" ({r.persona_name})" if r.persona_name else ""

            position_block = [f"### {r.agent}{persona_label}"]

            # Show their key arguments
            if r.key_arguments:
                position_block.append("**Their Arguments:**")
                for arg in r.key_arguments[:3]:
                    position_block.append(f"- {arg}")

            # Show challenges they raised
            if r.challenges_raised:
                position_block.append("**Challenges They Raised:**")
                for challenge in r.challenges_raised[:3]:
                    position_block.append(f"- {challenge}")

            # Show their issues
            if r.issues_found:
                position_block.append("**Issues They Identified:**")
                for issue in r.issues_found[:3]:
                    position_block.append(f"- {issue}")

            # Show their vote
            if r.vote:
                position_block.append(f"**Their Vote**: {r.vote.upper()}")

            position_block.append("")
            other_positions.append("\n".join(position_block))

        prompt = f"""## ADVERSARIAL DEBATE - Round {iteration + 1}

You are the {agent} agent. This is round {iteration + 1} of the debate.

### Original Task
{task}

{stance_info}

### Other Agents' Positions
{chr(10).join(other_positions) if other_positions else "No other positions yet."}

### Outstanding Issues
{chr(10).join(f"- {issue}" for issue in issues_to_fix) if issues_to_fix else "None identified."}

### Your Task This Round
1. **Respond to challenges**: Address objections raised against your position
2. **Challenge others**: Push back on weak arguments or overlooked concerns
3. **Find common ground**: Identify points of agreement where possible
4. **Refine your position**: Adjust based on valid critiques (concede if warranted)

### Response Format
- **Response to Challenges**: Address specific objections to your position
- **Counter-Arguments**: Challenge weak points in others' positions
- **Concessions**: Points you're willing to concede (use [CONCEDE] prefix)
- **Updated Position**: Your refined stance after this round
- **Remaining Concerns**: Issues that still need resolution

End with: APPROVE (ready to move forward) or ISSUES (significant concerns remain)
"""

        return prompt

    def run_swarm(
        self, agents: list[str], task: str, max_iterations: Optional[int] = None
    ) -> SwarmResult:
        """Run adversarial swarm orchestration with multiple agents.

        Agents are assigned opposing personas and debate until consensus,
        convergence, or budget exhaustion.
        """

        max_iter = max_iterations or self.config.max_iterations
        start_time = datetime.now().isoformat()

        self.state = SwarmState.RUNNING
        self._log(f"Starting ADVERSARIAL swarm with agents: {', '.join(agents)}")
        self._log(f"Task: {task[:100]}...")

        # Select adversarial personas for each agent
        self._select_adversarial_personas(agents, task)

        issues_to_fix: list[str] = []
        previous_responses: list[AgentResponse] = []

        for iteration in range(max_iter):
            self._log(f"=== Debate Round {iteration + 1}/{max_iter} ===")
            self.state = SwarmState.DEBATING

            # Check budget limit
            if self.total_cost >= self.config.budget_limit_usd:
                self._log("[BUDGET] Budget limit reached - forcing consensus", "WARNING")
                self.termination_reason = "budget"
                break

            # Check convergence (hybrid: positions stabilized)
            if iteration > 0 and self.convergence_detector.has_converged():
                self._log("[CONVERGED] Positions have stabilized - ending debate", "SUCCESS")
                self.termination_reason = "convergence"
                self.state = SwarmState.CONVERGING
                break

            iter_responses: list[AgentResponse] = []

            if self.config.parallel_execution and iteration == 0:
                # Parallel execution for first iteration
                with ThreadPoolExecutor(max_workers=len(agents)) as executor:
                    futures = {}
                    for agent in agents:
                        prompt = self._build_iteration_prompt(
                            agent, task, iteration, previous_responses, issues_to_fix
                        )
                        futures[executor.submit(self._invoke_agent, agent, prompt, iteration)] = (
                            agent
                        )

                    for future in as_completed(futures):
                        response = future.result()
                        iter_responses.append(response)
            else:
                # Sequential execution
                for agent in agents:
                    prompt = self._build_iteration_prompt(
                        agent, task, iteration, previous_responses, issues_to_fix
                    )
                    response = self._invoke_agent(agent, prompt, iteration)
                    iter_responses.append(response)

                    # Record in shared memory
                    self.shared_memory.add(
                        agent=agent,
                        content=f"Iteration {iteration + 1}: {response.vote or 'no vote'}",
                        tags=["swarm", "iteration"],
                    )

            # Collect issues
            issues_to_fix = self._collect_issues(iter_responses)

            # Record positions for convergence detection
            round_positions = {}
            for r in iter_responses:
                if r.agent in self.debate_positions:
                    round_positions[r.agent] = self.debate_positions[r.agent]
            self.convergence_detector.record_round(round_positions)

            # Run validation between iterations
            self._run_iteration_validation(iteration, iter_responses)

            # Check consensus
            consensus = self._check_consensus(iter_responses)

            swarm_iter = SwarmIteration(
                iteration_num=iteration,
                responses=iter_responses,
                consensus_reached=consensus,
                issues_remaining=issues_to_fix,
                decisions_made=[f"{r.agent}: {r.vote}" for r in iter_responses],
            )
            self.iterations.append(swarm_iter)

            previous_responses = iter_responses

            # Log debate status
            agreement_score = self.convergence_detector.calculate_agreement_score()
            self._log(f"Issues remaining: {len(issues_to_fix)}")
            self._log(f"Agreement score: {agreement_score:.0%}")
            self._log(f"Consensus: {'[YES]' if consensus else '[NO]'}")

            if consensus:
                self.state = SwarmState.CONSENSUS
                self.termination_reason = "consensus"
                self._log("[CONSENSUS] Agents reached agreement!", "SUCCESS")
                break

        # Determine final state
        if self.state not in (SwarmState.CONSENSUS, SwarmState.CONVERGING):
            self.state = SwarmState.MAX_ITERATIONS
            self.termination_reason = "max_iterations"

        # Generate final output and personality handoff
        final_output = self._generate_final_output(previous_responses)
        personality_handoff = self._generate_personality_handoff(
            task, previous_responses, final_output
        )

        # Create result
        result = SwarmResult(
            story_key=self.story_key,
            task=task,
            state=self.state,
            iterations=self.iterations,
            final_output=final_output,
            agents_involved=agents,
            total_tokens=self.total_tokens,
            total_cost_usd=self.total_cost,
            start_time=start_time,
            end_time=datetime.now().isoformat(),
            consensus_type=self.config.consensus_type,
            personality_handoff=personality_handoff,
            termination_reason=self.termination_reason,
        )

        # Save to knowledge graph
        self.knowledge_graph.add_decision(
            agent="SWARM",
            topic="adversarial-debate-result",
            decision=f"Completed: {self.termination_reason} after {len(self.iterations)} rounds",
            context={
                "iterations": len(self.iterations),
                "cost": self.total_cost,
                "termination": self.termination_reason,
                "personas": [p.name for p in self.selected_personas],
            },
        )

        return result

    def _generate_personality_handoff(
        self,
        task: str,
        responses: list[AgentResponse],
        final_output: str,
    ) -> PersonalityHandoff:
        """Generate a personality handoff summarizing the adversarial debate."""

        # Extract consensus points and tensions
        response_dicts = [{"content": r.content} for r in responses]
        consensus_points, tensions = self.convergence_detector.extract_consensus_points(
            response_dicts
        )

        # Generate debate summary
        debate_summary = self.convergence_detector.summarize_debate(
            [i.to_dict() for i in self.iterations]
        )

        # Synthesize recommended approach from final responses
        recommended = self._synthesize_recommendation(responses)

        return PersonalityHandoff(
            spawned_by="SWARM_ORCHESTRATOR",
            selected_personas=self.selected_personas,
            debate_summary=debate_summary,
            consensus_points=consensus_points,
            unresolved_tensions=tensions,
            recommended_approach=recommended,
            confidence=self.convergence_detector.calculate_agreement_score(),
            total_rounds=len(self.iterations),
            termination_reason=self.termination_reason,
            positions=list(self.debate_positions.values()),
        )

    def _synthesize_recommendation(self, responses: list[AgentResponse]) -> str:
        """Synthesize a recommended approach from debate responses."""
        # Collect all key arguments from approving agents
        approving_args = []
        for r in responses:
            if r.vote == "approve" and r.key_arguments:
                approving_args.extend(r.key_arguments[:2])

        if approving_args:
            return "Based on debate consensus: " + "; ".join(approving_args[:3])

        # Fallback to general synthesis
        all_args = []
        for r in responses:
            if r.key_arguments:
                all_args.extend(r.key_arguments[:1])

        if all_args:
            return "Synthesized from debate: " + "; ".join(all_args[:3])

        return "No clear recommendation emerged - human review recommended."

    def _generate_final_output(self, responses: list[AgentResponse]) -> str:
        """Generate consolidated final output."""
        # Use the DEV response as primary, or last response
        dev_response = next((r for r in responses if r.agent == "DEV"), None)
        primary = dev_response or responses[-1] if responses else None

        if not primary:
            return "No output generated."

        return primary.content

    def run_iteration_loop(
        self,
        primary_agent: str,
        reviewer_agent: str,
        task: str,
        max_iterations: Optional[int] = None,
    ) -> SwarmResult:
        """Run a simple iteration loop between two agents (e.g., DEV -> REVIEWER -> DEV)."""
        return self.run_swarm(
            agents=[primary_agent, reviewer_agent], task=task, max_iterations=max_iterations
        )


# Convenience functions
def run_swarm(
    story_key: str, agents: list[str], task: str, max_iterations: int = 3, **config_kwargs
) -> SwarmResult:
    """Quick function to run a swarm."""
    config = SwarmConfig(**config_kwargs)
    orchestrator = SwarmOrchestrator(story_key, config)
    return orchestrator.run_swarm(agents, task, max_iterations)


def run_dev_review_loop(story_key: str, task: str, max_iterations: int = 3) -> SwarmResult:
    """Run a DEV -> REVIEWER iteration loop."""
    config = SwarmConfig(
        max_iterations=max_iterations, consensus_type=ConsensusType.REVIEWER_APPROVAL
    )
    orchestrator = SwarmOrchestrator(story_key, config)
    return orchestrator.run_iteration_loop("DEV", "REVIEWER", task, max_iterations)


def run_architecture_review(story_key: str, task: str) -> SwarmResult:
    """Run an architecture review swarm."""
    config = SwarmConfig(
        max_iterations=2, consensus_type=ConsensusType.MAJORITY, parallel_execution=True
    )
    orchestrator = SwarmOrchestrator(story_key, config)
    return orchestrator.run_swarm(["ARCHITECT", "DEV", "REVIEWER"], task)


if __name__ == "__main__":
    print("=== Swarm Orchestrator Demo ===\n")
    print("This module orchestrates multi-agent collaboration.")
    print("\nExample usage:")
    print("""
    from lib.swarm_orchestrator import run_swarm, run_dev_review_loop

    # Full swarm with multiple agents
    result = run_swarm(
        story_key="3-5",
        agents=["ARCHITECT", "DEV", "REVIEWER"],
        task="Design and implement user authentication",
        max_iterations=3
    )
    print(result.to_summary())

    # Simple DEV -> REVIEWER loop
    result = run_dev_review_loop(
        story_key="3-5",
        task="Implement login endpoint",
        max_iterations=2
    )
    """)
