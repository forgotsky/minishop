#!/usr/bin/env python3
"""
Agent Handoff System - Structured Handoffs Between Agents

Creates explicit handoff summaries when transitioning work between agents.
Ensures context is preserved and the next agent has all necessary information.

Features:
- Automatic context extraction
- Git diff analysis for file changes
- Decision tracking
- Warning/blocker identification
- Structured handoff documents

Usage:
    from lib.agent_handoff import HandoffGenerator, create_handoff

    generator = HandoffGenerator(story_key="3-5")
    handoff = generator.generate(
        from_agent="SM",
        to_agent="DEV",
        work_summary="Created story context with all acceptance criteria"
    )
    print(handoff.to_markdown())
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Import shared memory for integration
try:
    from shared_memory import (
        HandoffSummary,
        get_knowledge_graph,
        get_shared_memory,
    )
except ImportError:
    from lib.shared_memory import (
        HandoffSummary,
        get_knowledge_graph,
        get_shared_memory,
    )


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent


@dataclass
class FileChange:
    """Represents a changed file."""

    path: str
    status: str  # added, modified, deleted
    additions: int = 0
    deletions: int = 0

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
        }


@dataclass
class AgentWorkSummary:
    """Summary of work done by an agent."""

    agent: str
    story_key: str
    start_time: str
    end_time: str
    description: str
    files_changed: list[FileChange] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)
    blockers_encountered: list[str] = field(default_factory=list)
    blockers_resolved: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    questions_for_next: list[str] = field(default_factory=list)
    artifacts_created: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "story_key": self.story_key,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "description": self.description,
            "files_changed": [f.to_dict() for f in self.files_changed],
            "decisions_made": self.decisions_made,
            "blockers_encountered": self.blockers_encountered,
            "blockers_resolved": self.blockers_resolved,
            "warnings": self.warnings,
            "questions_for_next": self.questions_for_next,
            "artifacts_created": self.artifacts_created,
        }


# Standard handoff templates for each agent transition
HANDOFF_TEMPLATES = {
    ("SM", "DEV"): {
        "focus_areas": [
            "Story acceptance criteria",
            "Technical context and constraints",
            "Related files and patterns to follow",
            "Known blockers or dependencies",
        ],
        "expected_questions": [
            "What patterns should I follow?",
            "Are there existing similar implementations?",
            "What tests are expected?",
        ],
    },
    ("SM", "ARCHITECT"): {
        "focus_areas": [
            "High-level requirements",
            "System constraints",
            "Integration points",
            "Scale requirements",
        ],
        "expected_questions": [
            "What are the non-functional requirements?",
            "What existing systems need integration?",
            "What are the performance targets?",
        ],
    },
    ("ARCHITECT", "DEV"): {
        "focus_areas": [
            "Architecture decisions",
            "Design patterns to use",
            "Component structure",
            "Interface definitions",
        ],
        "expected_questions": [
            "What patterns should I implement?",
            "How should components communicate?",
            "What are the boundaries?",
        ],
    },
    ("DEV", "REVIEWER"): {
        "focus_areas": [
            "Implementation approach",
            "Key decisions made",
            "Areas of uncertainty",
            "Test coverage",
        ],
        "expected_questions": [
            "Why was this approach chosen?",
            "What alternatives were considered?",
            "What edge cases were handled?",
        ],
    },
    ("REVIEWER", "DEV"): {
        "focus_areas": [
            "Issues found",
            "Required changes",
            "Suggestions (optional)",
            "Approval status",
        ],
        "expected_questions": [
            "Which issues are blocking?",
            "Are there acceptable alternatives?",
            "What's the priority order?",
        ],
    },
    ("BA", "DEV"): {
        "focus_areas": [
            "Refined requirements",
            "Acceptance criteria",
            "User stories",
            "Edge cases",
        ],
        "expected_questions": [
            "What are the exact acceptance criteria?",
            "What user flows need support?",
            "What error scenarios exist?",
        ],
    },
}


class HandoffGenerator:
    """Generates structured handoffs between agents."""

    def __init__(self, story_key: str, project_root: Optional[Path] = None):
        self.story_key = story_key
        self.project_root = project_root or PROJECT_ROOT
        self.knowledge_graph = get_knowledge_graph(story_key)
        self.shared_memory = get_shared_memory(story_key)

    def get_git_changes(self, since_commit: Optional[str] = None) -> list[FileChange]:
        """Get list of changed files from git."""
        try:
            if since_commit:
                cmd = ["git", "diff", "--numstat", since_commit]
            else:
                cmd = ["git", "diff", "--numstat", "HEAD~1"]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.project_root))

            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    additions = int(parts[0]) if parts[0] != "-" else 0
                    deletions = int(parts[1]) if parts[1] != "-" else 0
                    path = parts[2]

                    status = "modified"
                    if additions > 0 and deletions == 0:
                        status = "added"
                    elif additions == 0 and deletions > 0:
                        status = "deleted"

                    changes.append(
                        FileChange(
                            path=path, status=status, additions=additions, deletions=deletions
                        )
                    )

            return changes
        except subprocess.SubprocessError as e:
            # Git command failed - likely not a git repo or git not installed
            print(f"Warning: Could not get git changes: {e}")
            return []
        except OSError as e:
            print(f"Warning: Error accessing git: {e}")
            return []

    def get_staged_changes(self) -> list[FileChange]:
        """Get staged changes from git."""
        try:
            result = subprocess.run(
                ["git", "diff", "--cached", "--numstat"],
                capture_output=True,
                text=True,
                cwd=str(self.project_root),
            )

            changes = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                parts = line.split("\t")
                if len(parts) >= 3:
                    changes.append(
                        FileChange(
                            path=parts[2],
                            status="staged",
                            additions=int(parts[0]) if parts[0] != "-" else 0,
                            deletions=int(parts[1]) if parts[1] != "-" else 0,
                        )
                    )

            return changes
        except subprocess.SubprocessError as e:
            print(f"Warning: Could not get staged changes: {e}")
            return []
        except OSError as e:
            print(f"Warning: Error accessing git for staged changes: {e}")
            return []

    def extract_decisions_from_memory(self, agent: str) -> list[str]:
        """Extract decisions made by an agent from shared memory."""
        decisions = self.knowledge_graph.get_decisions_by_agent(agent)
        return [f"{d.topic}: {d.decision}" for d in decisions]

    def extract_warnings_from_log(self, log_content: str) -> list[str]:
        """Extract warnings from agent log output."""
        warnings = []
        warning_patterns = [
            r"\[WARNING\]\s*(.+)",
            r"WARNING:\s*(.+)",
            r"WARN:\s*(.+)",
            r"Watch out.*?:\s*(.+)",
            r"Note:\s*(.+)",
        ]

        for pattern in warning_patterns:
            matches = re.findall(pattern, log_content, re.IGNORECASE)
            warnings.extend(matches)

        return list(set(warnings))[:5]  # Dedupe and limit

    def generate(
        self,
        from_agent: str,
        to_agent: str,
        work_summary: str,
        decisions_made: Optional[list[str]] = None,
        blockers_resolved: Optional[list[str]] = None,
        warnings: Optional[list[str]] = None,
        files_changed: Optional[list[FileChange]] = None,
        next_steps: Optional[list[str]] = None,
        log_content: Optional[str] = None,
    ) -> HandoffSummary:
        """Generate a handoff from one agent to another."""

        # Auto-detect file changes if not provided
        if files_changed is None:
            files_changed = self.get_git_changes()

        # Auto-extract decisions from memory
        if decisions_made is None:
            decisions_made = self.extract_decisions_from_memory(from_agent)

        # Auto-extract warnings from log
        if warnings is None and log_content:
            warnings = self.extract_warnings_from_log(log_content)

        # Get template for this transition
        template = HANDOFF_TEMPLATES.get((from_agent, to_agent), {})

        # Generate next steps if not provided
        if next_steps is None:
            next_steps = self._generate_next_steps(from_agent, to_agent, files_changed, template)

        # Create handoff
        handoff = self.knowledge_graph.add_handoff(
            from_agent=from_agent,
            to_agent=to_agent,
            story_key=self.story_key,
            summary=work_summary,
            key_decisions=decisions_made or [],
            blockers_resolved=blockers_resolved or [],
            watch_out_for=warnings or [],
            files_touched=[f.path for f in files_changed] if files_changed else [],
            next_steps=next_steps or [],
        )

        # Also record in shared memory
        self.shared_memory.add(
            agent=from_agent,
            content=f"Handed off to {to_agent}: {work_summary}",
            tags=["handoff", to_agent.lower()],
        )

        return handoff

    def _generate_next_steps(
        self, from_agent: str, to_agent: str, files: list[FileChange], template: dict
    ) -> list[str]:
        """Generate suggested next steps for the receiving agent."""
        steps = []

        # Generic steps based on agent transition
        if to_agent == "DEV":
            steps.append("Review the acceptance criteria in the story context")
            if files:
                steps.append(f"Examine the {len(files)} files that have context")
            steps.append("Implement the required functionality")
            steps.append("Write tests for the implementation")

        elif to_agent == "REVIEWER":
            if files:
                steps.append(f"Review the {len(files)} changed files")
            steps.append("Check for code quality and best practices")
            steps.append("Verify test coverage")
            steps.append("Provide actionable feedback")

        elif to_agent == "ARCHITECT":
            steps.append("Analyze the requirements for design implications")
            steps.append("Document key architectural decisions")
            steps.append("Define component interfaces")

        elif to_agent == "SM":
            steps.append("Review the completed work")
            steps.append("Update story status")
            steps.append("Prepare for next phase or story")

        return steps

    def get_latest_handoff_for(self, agent: str) -> Optional[HandoffSummary]:
        """Get the most recent handoff for an agent."""
        return self.knowledge_graph.get_latest_handoff(agent)

    def generate_context_for_agent(self, agent: str) -> str:
        """Generate full context string for an agent including handoffs."""
        lines = [f"## Context for {agent}", ""]

        # Get latest handoff
        handoff = self.get_latest_handoff_for(agent)
        if handoff:
            lines.append("### Handoff from Previous Agent")
            lines.append(handoff.to_markdown())
            lines.append("")

        # Get relevant shared memory
        recent_memory = self.shared_memory.get_recent(5)
        if recent_memory:
            lines.append("### Recent Team Activity")
            for entry in recent_memory:
                lines.append(f"- **{entry.agent}**: {entry.content}")
            lines.append("")

        # Get relevant decisions
        decisions = list(self.knowledge_graph.decisions.values())
        active_decisions = [d for d in decisions if d.status == "active"]
        if active_decisions:
            lines.append("### Active Decisions")
            for dec in active_decisions[-5:]:
                lines.append(f"- **{dec.topic}** ({dec.agent}): {dec.decision}")
            lines.append("")

        return "\n".join(lines)


class WorkTracker:
    """Tracks work in progress for handoff generation."""

    def __init__(self, story_key: str, agent: str):
        self.story_key = story_key
        self.agent = agent
        self.start_time = datetime.now().isoformat()
        self.decisions: list[str] = []
        self.blockers: list[str] = []
        self.warnings: list[str] = []
        self.notes: list[str] = []
        self.files_touched: list[str] = []
        self.shared_memory = get_shared_memory(story_key)
        self.knowledge_graph = get_knowledge_graph(story_key)

    def record_decision(self, topic: str, decision: str, context: Optional[dict[str, Any]] = None):
        """Record a decision made during work."""
        self.decisions.append(f"{topic}: {decision}")
        self.knowledge_graph.add_decision(
            agent=self.agent, topic=topic, decision=decision, context=context or {}
        )

    def record_blocker(self, blocker: str, resolved: bool = False):
        """Record a blocker encountered."""
        if resolved:
            self.blockers.append(f" {blocker} (resolved)")
        else:
            self.blockers.append(f" {blocker}")

    def record_warning(self, warning: str):
        """Record a warning for the next agent."""
        self.warnings.append(warning)

    def record_note(self, note: str):
        """Record a general note."""
        self.notes.append(note)
        self.shared_memory.add(agent=self.agent, content=note, tags=["note"])

    def record_file(self, file_path: str):
        """Record a file that was touched."""
        if file_path not in self.files_touched:
            self.files_touched.append(file_path)

    def generate_handoff(self, to_agent: str, summary: str) -> HandoffSummary:
        """Generate a handoff based on tracked work."""
        generator = HandoffGenerator(self.story_key)

        # Separate resolved and unresolved blockers
        resolved = [
            b.replace(" ", "").replace(" (resolved)", "") for b in self.blockers if b.startswith("")
        ]

        return generator.generate(
            from_agent=self.agent,
            to_agent=to_agent,
            work_summary=summary,
            decisions_made=self.decisions,
            blockers_resolved=resolved,
            warnings=self.warnings,
            next_steps=self.notes if self.notes else None,
        )


# Convenience functions
def create_handoff(
    from_agent: str, to_agent: str, story_key: str, summary: str, **kwargs
) -> HandoffSummary:
    """Quick function to create a handoff."""
    generator = HandoffGenerator(story_key)
    return generator.generate(from_agent, to_agent, summary, **kwargs)


def get_agent_context(agent: str, story_key: str) -> str:
    """Get full context for an agent including handoffs."""
    generator = HandoffGenerator(story_key)
    return generator.generate_context_for_agent(agent)


def start_work_tracking(story_key: str, agent: str) -> WorkTracker:
    """Start tracking work for handoff generation."""
    return WorkTracker(story_key, agent)


if __name__ == "__main__":
    # Demo usage
    print("=== Handoff System Demo ===\n")

    # Simulate a workflow
    story_key = "demo-handoff"

    # SM starts work
    tracker = start_work_tracking(story_key, "SM")
    tracker.record_decision(
        "implementation-approach",
        "Use existing UserService class",
        {"reason": "Follows established patterns"},
    )
    tracker.record_decision(
        "testing-strategy",
        "Unit tests for service, integration for API",
        {"coverage_target": "80%"},
    )
    tracker.record_warning("Rate limiting on profile image uploads")
    tracker.record_note("Existing user.py has the patterns to follow")

    # Generate handoff to DEV
    handoff = tracker.generate_handoff(
        to_agent="DEV",
        summary="Created story context for user profile feature. Requirements are clear, patterns are established.",
    )

    print(handoff.to_markdown())

    print("\n" + "=" * 60 + "\n")

    # DEV receives context
    generator = HandoffGenerator(story_key)
    context = generator.generate_context_for_agent("DEV")
    print(context)
