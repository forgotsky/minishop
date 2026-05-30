#!/usr/bin/env python3
"""
Personality System - Dynamic Adversarial Persona Management

Provides dynamic personality selection and adversarial stance management
for multi-agent swarm debates. Enables agents to take opposing viewpoints
and challenge each other's designs.

Features:
- Persona loading from YAML templates
- Adversarial stance matching (finds natural oppositions)
- Convergence detection (identifies when debate is stabilizing)
- Personality handoff (preserves persona context across phases)

Usage:
    from lib.personality_system import (
        PersonalitySelector,
        ConvergenceDetector,
        PersonalityHandoff
    )

    selector = PersonalitySelector()
    personas = selector.select_adversarial_personas(
        task="Design authentication system",
        num_agents=3
    )

    detector = ConvergenceDetector()
    if detector.has_converged(iterations):
        # Debate has stabilized
"""

import hashlib
import re
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

try:
    import yaml

    HAS_YAML = True
except ImportError:
    HAS_YAML = False
    yaml = None

PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
TEMPLATES_DIR = PROJECT_ROOT / "tooling" / ".automation" / "overrides" / "templates"


@dataclass
class AdversarialStance:
    """Defines an agent's adversarial position in debates."""

    primary_concern: str  # e.g., "security", "velocity", "simplicity"
    opposes: list[str] = field(default_factory=list)  # Stances this naturally opposes
    challenge_triggers: list[str] = field(default_factory=list)  # Phrases that trigger challenges
    debate_style: str = "assertive"  # assertive, questioning, evidence-based
    concession_threshold: float = 0.7  # How much agreement needed to concede

    def conflicts_with(self, other: "AdversarialStance") -> bool:
        """Check if this stance naturally conflicts with another."""
        return other.primary_concern in self.opposes or self.primary_concern in other.opposes


@dataclass
class PersonalityProfile:
    """Complete personality profile for an agent."""

    name: str
    agent_type: str  # DEV, REVIEWER, ARCHITECT, etc.
    template_path: str
    role: str
    identity: str
    communication_style: str
    principles: list[str] = field(default_factory=list)
    additional_rules: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    critical_actions: list[str] = field(default_factory=list)
    model: str = "sonnet"
    max_budget_usd: float = 10.0
    adversarial_stance: Optional[AdversarialStance] = None

    # Extended attributes for complex personas
    technical_preferences: dict = field(default_factory=dict)
    behavior: dict = field(default_factory=dict)
    constraints: dict = field(default_factory=dict)
    mantras: list[str] = field(default_factory=list)

    def to_prompt_injection(self) -> str:
        """Generate prompt text to inject this personality."""
        lines = [
            f"## Your Persona: {self.name}",
            "",
            f"**Role**: {self.role}",
            f"**Identity**: {self.identity}",
            f"**Communication Style**: {self.communication_style}",
            "",
        ]

        if self.principles:
            lines.append("### Core Principles")
            for p in self.principles:
                lines.append(f"- {p}")
            lines.append("")

        if self.adversarial_stance:
            lines.append("### Your Stance in This Debate")
            lines.append(f"**Primary Concern**: {self.adversarial_stance.primary_concern}")
            lines.append(f"**Debate Style**: {self.adversarial_stance.debate_style}")
            if self.adversarial_stance.opposes:
                lines.append(
                    f"**Challenge perspectives focused on**: {', '.join(self.adversarial_stance.opposes)}"
                )
            lines.append("")
            lines.append("When you see arguments that prioritize the concerns you oppose,")
            lines.append("push back firmly with evidence and alternative approaches.")
            lines.append("")

        if self.additional_rules:
            lines.append("### Rules to Follow")
            for r in self.additional_rules[:5]:  # Limit for token efficiency
                lines.append(f"- {r}")
            lines.append("")

        if self.mantras:
            lines.append("### Mantras")
            for m in self.mantras[:3]:
                lines.append(f'- "{m}"')
            lines.append("")

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "name": self.name,
            "agent_type": self.agent_type,
            "template_path": self.template_path,
            "role": self.role,
            "identity": self.identity,
            "model": self.model,
            "adversarial_stance": (
                {
                    "primary_concern": self.adversarial_stance.primary_concern,
                    "opposes": self.adversarial_stance.opposes,
                    "debate_style": self.adversarial_stance.debate_style,
                }
                if self.adversarial_stance
                else None
            ),
        }


@dataclass
class DebatePosition:
    """Tracks an agent's position during debate."""

    agent: str
    persona_name: str
    key_arguments: list[str] = field(default_factory=list)
    concessions_made: list[str] = field(default_factory=list)
    challenges_raised: list[str] = field(default_factory=list)
    confidence: float = 1.0  # Decreases as agent concedes points

    def position_hash(self) -> str:
        """Generate hash of current position for change detection."""
        content = "|".join(sorted(self.key_arguments))
        return hashlib.md5(content.encode()).hexdigest()[:8]


@dataclass
class PersonalityHandoff:
    """Handoff context that includes personality state."""

    spawned_by: str  # Agent that initiated the swarm
    selected_personas: list[PersonalityProfile]
    debate_summary: str
    consensus_points: list[str]
    unresolved_tensions: list[str]
    recommended_approach: str
    confidence: float  # How strong the consensus is (0-1)
    total_rounds: int
    termination_reason: str  # "consensus", "convergence", "budget", "max_rounds"
    positions: list[DebatePosition] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Generate markdown summary for handoff."""
        lines = [
            "## Adversarial Debate Summary",
            "",
            f"**Initiated by**: {self.spawned_by}",
            f"**Rounds**: {self.total_rounds}",
            f"**Termination**: {self.termination_reason}",
            f"**Consensus Confidence**: {self.confidence:.0%}",
            "",
            "### Participating Personas",
        ]

        for p in self.selected_personas:
            stance = (
                f" (Focus: {p.adversarial_stance.primary_concern})" if p.adversarial_stance else ""
            )
            lines.append(f"- **{p.name}** ({p.agent_type}){stance}")

        lines.append("")
        lines.append("### Consensus Points")
        for point in self.consensus_points:
            lines.append(f"- {point}")

        if self.unresolved_tensions:
            lines.append("")
            lines.append("### Unresolved Tensions (for human review)")
            for tension in self.unresolved_tensions:
                lines.append(f"- [WARNING] {tension}")

        lines.append("")
        lines.append("### Recommended Approach")
        lines.append(self.recommended_approach)

        if self.debate_summary:
            lines.append("")
            lines.append("### Debate Summary")
            lines.append(self.debate_summary)

        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "spawned_by": self.spawned_by,
            "selected_personas": [p.to_dict() for p in self.selected_personas],
            "debate_summary": self.debate_summary,
            "consensus_points": self.consensus_points,
            "unresolved_tensions": self.unresolved_tensions,
            "recommended_approach": self.recommended_approach,
            "confidence": self.confidence,
            "total_rounds": self.total_rounds,
            "termination_reason": self.termination_reason,
        }


class PersonalityLoader:
    """Loads personality profiles from YAML templates."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._cache: dict[str, PersonalityProfile] = {}

    def list_available(self, agent_type: Optional[str] = None) -> list[str]:
        """List available persona templates."""
        templates = []
        search_dir = self.templates_dir

        if agent_type:
            search_dir = self.templates_dir / agent_type.lower()
            if not search_dir.exists():
                return []

        for yaml_file in search_dir.rglob("*.yaml"):
            if yaml_file.name.startswith("user-"):
                continue  # Skip user templates
            rel_path = yaml_file.relative_to(self.templates_dir)
            templates.append(str(rel_path))

        return sorted(templates)

    def load(self, template_path: str) -> Optional[PersonalityProfile]:
        """Load a persona from template path."""
        if template_path in self._cache:
            return self._cache[template_path]

        full_path = self.templates_dir / template_path
        if not full_path.exists():
            return None

        if not HAS_YAML:
            # Create a basic profile from path when yaml not available
            return self._create_fallback_profile(template_path)

        try:
            with open(full_path) as f:
                data = yaml.safe_load(f)

            profile = self._parse_profile(data, template_path)
            self._cache[template_path] = profile
            return profile

        except Exception as e:
            print(f"[WARNING] Failed to load persona {template_path}: {e}")
            return self._create_fallback_profile(template_path)

    def _create_fallback_profile(self, template_path: str) -> PersonalityProfile:
        """Create a basic profile when yaml loading isn't available."""
        parts = template_path.split("/")
        agent_type = parts[0].upper() if len(parts) > 1 else "UNKNOWN"
        name = Path(template_path).stem.replace("-", " ").title()

        return PersonalityProfile(
            name=name,
            agent_type=agent_type,
            template_path=template_path,
            role=name,
            identity=f"A {name.lower()} focused on quality",
            communication_style="professional",
        )

    def _parse_profile(self, data: dict, template_path: str) -> PersonalityProfile:
        """Parse YAML data into PersonalityProfile."""
        # Extract agent type from path
        parts = template_path.split("/")
        agent_type = parts[0].upper() if len(parts) > 1 else "UNKNOWN"

        # Handle different schema formats
        persona = data.get("persona", {})
        personality = data.get("personality", {})

        # Extract name
        name = (
            persona.get("name")
            or persona.get("role")
            or data.get("name")
            or Path(template_path).stem.replace("-", " ").title()
        )

        # Extract role and identity
        role = persona.get("role", name)
        identity = (
            persona.get("identity")
            or persona.get("description")
            or personality.get("description", "")
        )

        # Extract communication style
        comm_style = persona.get("communication_style", "")
        if not comm_style and personality.get("communication_style"):
            cs = personality["communication_style"]
            comm_style = cs.get("tone", "") if isinstance(cs, dict) else str(cs)

        # Extract adversarial stance if present
        adversarial_stance = None
        stance_data = data.get("adversarial_stance")
        if stance_data:
            adversarial_stance = AdversarialStance(
                primary_concern=stance_data.get("primary_concern", "quality"),
                opposes=stance_data.get("opposes", []),
                challenge_triggers=stance_data.get("challenge_triggers", []),
                debate_style=stance_data.get("debate_style", "assertive"),
                concession_threshold=stance_data.get("concession_threshold", 0.7),
            )

        return PersonalityProfile(
            name=name,
            agent_type=agent_type,
            template_path=template_path,
            role=role,
            identity=identity,
            communication_style=comm_style,
            principles=persona.get("principles", []),
            additional_rules=data.get("additional_rules", []),
            memories=data.get("memories", []),
            critical_actions=data.get("critical_actions", []),
            model=data.get("model", "sonnet"),
            max_budget_usd=data.get("max_budget_usd", 10.0),
            adversarial_stance=adversarial_stance,
            technical_preferences=data.get("technical_preferences", {}),
            behavior=data.get("behavior", {}),
            constraints=data.get("constraints", {}),
            mantras=data.get("mantras", []),
        )


# Predefined adversarial pairings - personas that naturally oppose each other
ADVERSARIAL_PAIRINGS = {
    # Security vs Velocity
    "security_velocity": [
        ("dev/security-focused.yaml", "dev/rapid-prototyper.yaml"),
        ("reviewer/thorough-critic.yaml", "reviewer/quick-sanity.yaml"),
    ],
    # Enterprise vs Pragmatic
    "enterprise_pragmatic": [
        ("architect/enterprise-architect.yaml", "architect/pragmatic-minimalist.yaml"),
    ],
    # Thoroughness vs Speed
    "thorough_speed": [
        ("reviewer/thorough-critic.yaml", "reviewer/quick-sanity.yaml"),
        ("ba/requirements-engineer.yaml", "ba/agile-storyteller.yaml"),
    ],
    # Traditional vs Agile
    "traditional_agile": [
        ("pm/traditional-pm.yaml", "pm/agile-pm.yaml"),
    ],
    # Stability vs Innovation
    "stability_innovation": [
        ("maintainer/legacy-steward.yaml", "dev/rapid-prototyper.yaml"),
        ("architect/enterprise-architect.yaml", "architect/cloud-native.yaml"),
    ],
}

# Task keyword to concern mapping
TASK_CONCERN_MAPPING = {
    # Security-related keywords
    "auth": "security",
    "login": "security",
    "password": "security",
    "encrypt": "security",
    "token": "security",
    "permission": "security",
    "access": "security",
    "vulnerability": "security",
    # Performance-related keywords
    "performance": "performance",
    "optimize": "performance",
    "speed": "performance",
    "latency": "performance",
    "cache": "performance",
    "scale": "performance",
    # Architecture-related keywords
    "design": "architecture",
    "architect": "architecture",
    "structure": "architecture",
    "pattern": "architecture",
    "microservice": "architecture",
    "monolith": "architecture",
    # Quality-related keywords
    "test": "quality",
    "review": "quality",
    "refactor": "quality",
    "clean": "quality",
    "maintain": "quality",
    # Velocity-related keywords
    "mvp": "velocity",
    "prototype": "velocity",
    "quick": "velocity",
    "fast": "velocity",
    "deadline": "velocity",
    "ship": "velocity",
}

# Concern to persona mapping (which personas care about which concerns)
CONCERN_PERSONAS = {
    "security": [
        "dev/security-focused.yaml",
        "reviewer/thorough-critic.yaml",
    ],
    "performance": [
        "dev/performance-engineer.yaml",
        "architect/cloud-native.yaml",
    ],
    "architecture": [
        "architect/enterprise-architect.yaml",
        "architect/pragmatic-minimalist.yaml",
        "architect/cloud-native.yaml",
    ],
    "quality": [
        "reviewer/thorough-critic.yaml",
        "reviewer/mentoring-reviewer.yaml",
        "maintainer/legacy-steward.yaml",
    ],
    "velocity": [
        "dev/rapid-prototyper.yaml",
        "reviewer/quick-sanity.yaml",
        "pm/agile-pm.yaml",
    ],
    "simplicity": [
        "architect/pragmatic-minimalist.yaml",
        "dev/senior-fullstack.yaml",
    ],
    "compliance": [
        "architect/enterprise-architect.yaml",
        "ba/requirements-engineer.yaml",
    ],
    "user_experience": [
        "ba/domain-expert.yaml",
        "writer/user-guide-author.yaml",
    ],
}


class PersonalitySelector:
    """Selects adversarial personas based on task analysis."""

    def __init__(self, templates_dir: Optional[Path] = None):
        self.loader = PersonalityLoader(templates_dir)

    def analyze_task(self, task: str) -> list[str]:
        """Analyze task to determine relevant concerns."""
        task_lower = task.lower()
        concerns = set()

        for keyword, concern in TASK_CONCERN_MAPPING.items():
            if keyword in task_lower:
                concerns.add(concern)

        # Default concerns if none detected
        if not concerns:
            concerns = {"quality", "architecture", "velocity"}

        return list(concerns)

    def find_opposing_personas(self, concerns: list[str], num_agents: int = 3) -> list[str]:
        """Find personas that will naturally oppose each other on these concerns."""
        candidates = []

        # Get personas for each concern
        for concern in concerns:
            if concern in CONCERN_PERSONAS:
                candidates.extend(CONCERN_PERSONAS[concern])

        # Dedupe while preserving order
        seen = set()
        unique_candidates = []
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        # If we have adversarial pairings, prefer those
        for _pairing_type, pairs in ADVERSARIAL_PAIRINGS.items():
            for pair in pairs:
                if pair[0] in unique_candidates and pair[1] in unique_candidates:
                    # This pair is relevant - prioritize them
                    unique_candidates.remove(pair[0])
                    unique_candidates.remove(pair[1])
                    unique_candidates = [pair[0], pair[1]] + unique_candidates

        return unique_candidates[:num_agents]

    def select_adversarial_personas(
        self,
        task: str,
        num_agents: int = 3,
        required_agents: Optional[list[str]] = None,
    ) -> list[PersonalityProfile]:
        """Select adversarial personas for a task.

        Args:
            task: The task description
            num_agents: Number of agents to select
            required_agents: Optional list of agent types that must be included

        Returns:
            List of PersonalityProfile with adversarial stances
        """
        concerns = self.analyze_task(task)
        profiles = []

        # If required agents specified, select best persona for each agent type
        if required_agents:
            for agent_type in required_agents:
                profile = self._select_best_persona_for_agent(agent_type, concerns)
                if profile:
                    if not profile.adversarial_stance:
                        profile.adversarial_stance = self._infer_stance(profile, concerns)
                    profiles.append(profile)
        else:
            # No specific agents required - select based on concerns
            template_paths = self.find_opposing_personas(concerns, num_agents)
            for path in template_paths:
                profile = self.loader.load(path)
                if profile:
                    if not profile.adversarial_stance:
                        profile.adversarial_stance = self._infer_stance(profile, concerns)
                    profiles.append(profile)

        return profiles[:num_agents]

    def _select_best_persona_for_agent(
        self, agent_type: str, concerns: list[str]
    ) -> Optional[PersonalityProfile]:
        """Select the best persona for a given agent type based on task concerns."""
        # Map agent types to their persona directories
        agent_dir_map = {
            "DEV": "dev",
            "REVIEWER": "reviewer",
            "ARCHITECT": "architect",
            "SM": "sm",
            "PM": "pm",
            "BA": "ba",
            "WRITER": "writer",
            "MAINTAINER": "maintainer",
            "SECURITY": "dev",  # Use dev/security-focused for SECURITY agent
        }

        agent_dir = agent_dir_map.get(agent_type, agent_type.lower())
        available = self.loader.list_available(agent_dir)

        if not available:
            return None

        # Score personas based on concern alignment
        best_score = -1
        best_path = available[0]  # Default to first available

        # Concern-to-persona preference mapping
        concern_preferences = {
            "security": ["security-focused", "thorough-critic"],
            "performance": ["performance-engineer", "cloud-native"],
            "velocity": ["rapid-prototyper", "quick-sanity", "agile"],
            "architecture": ["enterprise-architect", "pragmatic-minimalist", "cloud-native"],
            "quality": ["thorough-critic", "mentoring", "senior"],
            "simplicity": ["pragmatic-minimalist", "rapid-prototyper"],
        }

        for path in available:
            path_lower = path.lower()
            score = 0

            for concern in concerns:
                preferences = concern_preferences.get(concern, [])
                for pref in preferences:
                    if pref in path_lower:
                        score += 1

            if score > best_score:
                best_score = score
                best_path = path

        return self.loader.load(best_path)

    def _infer_stance(
        self, profile: PersonalityProfile, task_concerns: list[str]
    ) -> AdversarialStance:
        """Infer adversarial stance from profile characteristics."""
        # Default stance based on agent type and profile attributes
        stance_map = {
            "DEV": {
                "security-focused": AdversarialStance(
                    primary_concern="security",
                    opposes=["velocity", "shortcuts"],
                    debate_style="evidence-based",
                ),
                "rapid-prototyper": AdversarialStance(
                    primary_concern="velocity",
                    opposes=["over_engineering", "premature_optimization"],
                    debate_style="assertive",
                ),
                "performance-engineer": AdversarialStance(
                    primary_concern="performance",
                    opposes=["bloat", "inefficiency"],
                    debate_style="evidence-based",
                ),
                "default": AdversarialStance(
                    primary_concern="implementation_quality",
                    opposes=["complexity", "ambiguity"],
                    debate_style="questioning",
                ),
            },
            "REVIEWER": {
                "thorough-critic": AdversarialStance(
                    primary_concern="correctness",
                    opposes=["shortcuts", "untested_code", "security_gaps"],
                    debate_style="evidence-based",
                ),
                "quick-sanity": AdversarialStance(
                    primary_concern="pragmatism",
                    opposes=["over_engineering", "bikeshedding"],
                    debate_style="assertive",
                ),
                "default": AdversarialStance(
                    primary_concern="quality",
                    opposes=["technical_debt"],
                    debate_style="questioning",
                ),
            },
            "ARCHITECT": {
                "enterprise-architect": AdversarialStance(
                    primary_concern="scalability",
                    opposes=["shortcuts", "monolith_only", "vendor_lockin"],
                    debate_style="evidence-based",
                ),
                "pragmatic-minimalist": AdversarialStance(
                    primary_concern="simplicity",
                    opposes=["over_engineering", "premature_abstraction"],
                    debate_style="assertive",
                ),
                "cloud-native": AdversarialStance(
                    primary_concern="scalability",
                    opposes=["legacy_patterns", "tight_coupling"],
                    debate_style="questioning",
                ),
                "default": AdversarialStance(
                    primary_concern="architecture_quality",
                    opposes=["accidental_complexity"],
                    debate_style="questioning",
                ),
            },
        }

        agent_stances = stance_map.get(profile.agent_type, {})
        template_name = Path(profile.template_path).stem

        return agent_stances.get(
            template_name,
            agent_stances.get(
                "default",
                AdversarialStance(
                    primary_concern="quality", opposes=["poor_design"], debate_style="questioning"
                ),
            ),
        )


class ConvergenceDetector:
    """Detects when a debate has converged (positions stabilized)."""

    def __init__(
        self,
        similarity_threshold: float = 0.8,
        stability_rounds: int = 2,
        max_new_arguments_per_round: int = 2,
    ):
        self.similarity_threshold = similarity_threshold
        self.stability_rounds = stability_rounds
        self.max_new_arguments = max_new_arguments_per_round
        self.position_history: list[dict[str, DebatePosition]] = []

    def record_round(self, positions: dict[str, DebatePosition]):
        """Record positions from a debate round."""
        self.position_history.append(positions)

    def has_converged(self) -> bool:
        """Check if debate has converged based on position stability."""
        if len(self.position_history) < self.stability_rounds:
            return False

        # Check last N rounds for stability
        recent = self.position_history[-self.stability_rounds :]

        # Compare position hashes
        for agent in recent[0].keys():
            hashes = [
                round_pos.get(agent, DebatePosition(agent, "")).position_hash()
                for round_pos in recent
            ]
            if len(set(hashes)) > 1:
                # Positions still changing
                return False

        return True

    def calculate_agreement_score(self) -> float:
        """Calculate how much agents agree (0-1)."""
        if not self.position_history:
            return 0.0

        latest = self.position_history[-1]
        all_arguments = []

        for pos in latest.values():
            all_arguments.extend(pos.key_arguments)

        if not all_arguments:
            return 1.0  # No arguments = agreement by default

        # Count overlapping arguments
        unique_args = set(all_arguments)
        overlap_score = 1 - (len(unique_args) / max(len(all_arguments), 1))

        return min(1.0, overlap_score + 0.3)  # Bias toward agreement

    def get_convergence_reason(self) -> str:
        """Get human-readable convergence status."""
        if not self.position_history:
            return "No debate recorded"

        if self.has_converged():
            agreement = self.calculate_agreement_score()
            if agreement > 0.9:
                return "Strong consensus reached"
            elif agreement > 0.7:
                return "Moderate agreement with minor differences"
            else:
                return "Positions stabilized but significant disagreement remains"

        return "Debate still active"

    def extract_consensus_points(
        self, responses: list[dict[str, Any]]
    ) -> tuple[list[str], list[str]]:
        """Extract points of consensus and remaining tensions.

        Args:
            responses: List of agent responses with content

        Returns:
            Tuple of (consensus_points, tensions)
        """
        consensus = []
        tensions = []

        # Simple extraction based on common patterns
        all_approvals = []
        all_issues = []

        for resp in responses:
            content = resp.get("content", "")

            # Extract approvals
            approval_patterns = [
                r"agree.* (?:that|with)\s+(.+?)(?:\.|$)",
                r"consensus.* (?:on|that)\s+(.+?)(?:\.|$)",
                r"(?:we|all) (?:should|need to)\s+(.+?)(?:\.|$)",
            ]
            for pattern in approval_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                all_approvals.extend(matches)

            # Extract issues
            issue_patterns = [
                r"disagree.* (?:that|with|about)\s+(.+?)(?:\.|$)",
                r"concern.* (?:about|regarding)\s+(.+?)(?:\.|$)",
                r"(?:but|however).* (.+?)(?:\.|$)",
            ]
            for pattern in issue_patterns:
                matches = re.findall(pattern, content, re.IGNORECASE)
                all_issues.extend(matches)

        # Dedupe and clean
        consensus = list({a.strip() for a in all_approvals if len(a) > 10})[:5]
        tensions = list({i.strip() for i in all_issues if len(i) > 10})[:5]

        return consensus, tensions

    def summarize_debate(self, iterations: list[dict[str, Any]]) -> str:
        """Generate a summary of the debate progression."""
        if not iterations:
            return "No debate occurred."

        num_rounds = len(iterations)
        lines = [f"The debate progressed through {num_rounds} round(s)."]

        # Track how positions evolved
        if num_rounds > 1:
            lines.append("Initial positions were challenged and refined through cross-examination.")

        agreement = self.calculate_agreement_score()
        if agreement > 0.8:
            lines.append("Agents reached substantial agreement on core approach.")
        elif agreement > 0.5:
            lines.append(
                "Agents found common ground on key points while maintaining some differences."
            )
        else:
            lines.append("Significant disagreements remain that may require human arbitration.")

        return " ".join(lines)


def extract_arguments_from_response(content: str) -> list[str]:
    """Extract key arguments from agent response content."""
    arguments = []

    # Look for structured arguments
    patterns = [
        r"(?:I (?:believe|think|argue|propose) (?:that )?(.+?)(?:\.|$))",
        r"(?:My (?:position|view|recommendation) is (?:that )?(.+?)(?:\.|$))",
        r"(?:We should (.+?)(?:\.|$))",
        r"(?:The (?:best|right|correct) approach is (.+?)(?:\.|$))",
    ]

    for pattern in patterns:
        matches = re.findall(pattern, content, re.IGNORECASE)
        arguments.extend(matches)

    # Also look for bullet points
    bullet_matches = re.findall(r"^[-*]\s+(.+?)$", content, re.MULTILINE)
    arguments.extend(bullet_matches)

    # Clean and dedupe
    cleaned = []
    for arg in arguments:
        arg = arg.strip()
        if len(arg) > 10 and arg not in cleaned:
            cleaned.append(arg)

    return cleaned[:10]  # Limit


def calculate_position_similarity(pos1: DebatePosition, pos2: DebatePosition) -> float:
    """Calculate similarity between two debate positions."""
    if not pos1.key_arguments and not pos2.key_arguments:
        return 1.0

    all_args = pos1.key_arguments + pos2.key_arguments
    if not all_args:
        return 1.0

    # Use sequence matching for similarity
    text1 = " ".join(pos1.key_arguments)
    text2 = " ".join(pos2.key_arguments)

    return SequenceMatcher(None, text1, text2).ratio()


if __name__ == "__main__":
    print("=== Personality System Demo ===\n")

    # Demo personality selection
    selector = PersonalitySelector()

    task = "Design a secure authentication system with OAuth support"
    print(f"Task: {task}\n")

    concerns = selector.analyze_task(task)
    print(f"Detected concerns: {concerns}\n")

    personas = selector.select_adversarial_personas(task, num_agents=3)
    print("Selected adversarial personas:")
    for p in personas:
        print(f"  - {p.name} ({p.agent_type})")
        if p.adversarial_stance:
            print(f"    Focus: {p.adversarial_stance.primary_concern}")
            print(f"    Opposes: {p.adversarial_stance.opposes}")
        print()

    # Demo convergence detection
    print("=== Convergence Detection Demo ===\n")
    detector = ConvergenceDetector()

    # Simulate debate rounds
    round1 = {
        "agent1": DebatePosition(
            "agent1", "Security Advocate", key_arguments=["Use OAuth 2.0", "Enforce MFA"]
        ),
        "agent2": DebatePosition(
            "agent2", "Pragmatist", key_arguments=["Start with basic auth", "Add OAuth later"]
        ),
    }
    detector.record_round(round1)
    print(f"After round 1: Converged={detector.has_converged()}")

    round2 = {
        "agent1": DebatePosition(
            "agent1",
            "Security Advocate",
            key_arguments=["Use OAuth 2.0", "Enforce MFA", "OK to start simple"],
        ),
        "agent2": DebatePosition(
            "agent2",
            "Pragmatist",
            key_arguments=["Start with OAuth", "Add MFA in phase 2"],
        ),
    }
    detector.record_round(round2)
    print(f"After round 2: Converged={detector.has_converged()}")
    print(f"Agreement score: {detector.calculate_agreement_score():.2f}")
    print(f"Status: {detector.get_convergence_reason()}")
