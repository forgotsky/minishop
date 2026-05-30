#!/usr/bin/env python3
"""
Shared Memory System - Cross-Agent Knowledge Sharing

Provides a shared memory pool and knowledge graph that all agents can read/write.
Enables agents to share decisions, learnings, and context across the workflow.

Features:
- Shared memory pool (all agents can contribute)
- Knowledge graph with queryable decisions
- Automatic timestamping and attribution
- Memory search and retrieval
- Decision tracking with context

Usage:
    from lib.shared_memory import SharedMemory, KnowledgeGraph

    # Shared memory
    memory = SharedMemory(story_key="3-5")
    memory.add("DEV", "Decided to use PostgreSQL for user data", tags=["database", "decision"])
    entries = memory.search("database")

    # Knowledge graph
    kg = KnowledgeGraph(story_key="3-5")
    kg.add_decision("ARCHITECT", "auth-approach", "Use JWT with refresh tokens",
                    context={"reason": "Stateless, scalable"})
    decision = kg.query("What authentication approach was decided?")
"""

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Storage paths
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
MEMORY_DIR = PROJECT_ROOT / "tooling" / ".automation" / "memory"
SHARED_MEMORY_DIR = MEMORY_DIR / "shared"
KNOWLEDGE_GRAPH_DIR = MEMORY_DIR / "knowledge"


@dataclass
class MemoryEntry:
    """A single shared memory entry."""

    id: str
    timestamp: str
    agent: str
    content: str
    tags: list[str] = field(default_factory=list)
    story_key: Optional[str] = None
    references: list[str] = field(default_factory=list)  # IDs of related entries

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(**data)

    def matches_query(self, query: str) -> bool:
        """Check if entry matches a search query."""
        query_lower = query.lower()
        return (
            query_lower in self.content.lower()
            or any(query_lower in tag.lower() for tag in self.tags)
            or query_lower in self.agent.lower()
        )


@dataclass
class Decision:
    """A tracked decision in the knowledge graph."""

    id: str
    timestamp: str
    agent: str
    topic: str
    decision: str
    context: dict[str, Any] = field(default_factory=dict)
    supersedes: Optional[str] = None  # ID of decision this replaces
    status: str = "active"  # active, superseded, revoked

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Decision":
        return cls(**data)


@dataclass
class HandoffSummary:
    """Summary passed from one agent to another."""

    id: str
    timestamp: str
    from_agent: str
    to_agent: str
    story_key: str
    summary: str
    key_decisions: list[str] = field(default_factory=list)
    blockers_resolved: list[str] = field(default_factory=list)
    watch_out_for: list[str] = field(default_factory=list)
    files_touched: list[str] = field(default_factory=list)
    next_steps: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "HandoffSummary":
        return cls(**data)

    def to_markdown(self) -> str:
        """Convert handoff to markdown format."""
        lines = [
            f"## Handoff: {self.from_agent} -> {self.to_agent}",
            "",
            f"**Story**: {self.story_key}",
            f"**Time**: {self.timestamp}",
            "",
            "### Summary",
            self.summary,
            "",
        ]

        if self.key_decisions:
            lines.append("### Key Decisions")
            for decision in self.key_decisions:
                lines.append(f"- {decision}")
            lines.append("")

        if self.blockers_resolved:
            lines.append("### Blockers Resolved")
            for blocker in self.blockers_resolved:
                lines.append(f"-  {blocker}")
            lines.append("")

        if self.watch_out_for:
            lines.append("###  Watch Out For")
            for warning in self.watch_out_for:
                lines.append(f"- {warning}")
            lines.append("")

        if self.files_touched:
            lines.append("### Files Modified")
            for file in self.files_touched:
                lines.append(f"- `{file}`")
            lines.append("")

        if self.next_steps:
            lines.append("### Next Steps")
            for i, step in enumerate(self.next_steps, 1):
                lines.append(f"{i}. {step}")
            lines.append("")

        return "\n".join(lines)


class SharedMemory:
    """Cross-agent shared memory pool."""

    def __init__(self, story_key: Optional[str] = None):
        self.story_key = story_key
        self.memory_dir = SHARED_MEMORY_DIR
        self.memory_dir.mkdir(parents=True, exist_ok=True)
        self.entries: list[MemoryEntry] = []
        self._load()

    def _get_file_path(self) -> Path:
        """Get the memory file path."""
        if self.story_key:
            return self.memory_dir / f"shared_{self.story_key}.json"
        return self.memory_dir / "shared_global.json"

    def _load(self):
        """Load existing memory entries."""
        file_path = self._get_file_path()
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    self.entries = [MemoryEntry.from_dict(e) for e in data.get("entries", [])]
            except json.JSONDecodeError as e:
                print(f"Warning: Corrupted memory file {file_path.name}, starting fresh: {e}")
                self.entries = []
            except KeyError as e:
                print(f"Warning: Invalid memory structure in {file_path.name}: {e}")
                self.entries = []

    def _save(self):
        """Save memory entries to disk."""
        file_path = self._get_file_path()
        with open(file_path, "w") as f:
            json.dump(
                {
                    "story_key": self.story_key,
                    "last_updated": datetime.now().isoformat(),
                    "entries": [e.to_dict() for e in self.entries],
                },
                f,
                indent=2,
            )

    def _generate_id(self) -> str:
        """Generate a unique ID for an entry."""
        import uuid

        return f"mem_{uuid.uuid4().hex[:8]}"

    def add(
        self,
        agent: str,
        content: str,
        tags: Optional[list[str]] = None,
        references: Optional[list[str]] = None,
    ) -> MemoryEntry:
        """Add a new memory entry."""
        entry = MemoryEntry(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            agent=agent,
            content=content,
            tags=tags or [],
            story_key=self.story_key,
            references=references or [],
        )
        self.entries.append(entry)
        self._save()
        return entry

    def search(
        self,
        query: str,
        agent: Optional[str] = None,
        tags: Optional[list[str]] = None,
        limit: int = 10,
    ) -> list[MemoryEntry]:
        """Search memory entries."""
        results = []

        for entry in reversed(self.entries):  # Most recent first
            if agent and entry.agent != agent:
                continue
            if tags and not any(t in entry.tags for t in tags):
                continue
            if query and not entry.matches_query(query):
                continue
            results.append(entry)
            if len(results) >= limit:
                break

        return results

    def get_by_agent(self, agent: str, limit: int = 20) -> list[MemoryEntry]:
        """Get all entries from a specific agent."""
        return [e for e in reversed(self.entries) if e.agent == agent][:limit]

    def get_recent(self, limit: int = 20) -> list[MemoryEntry]:
        """Get most recent entries."""
        return list(reversed(self.entries))[:limit]

    def get_by_tags(self, tags: list[str]) -> list[MemoryEntry]:
        """Get entries matching any of the given tags."""
        return [e for e in self.entries if any(t in e.tags for t in tags)]

    def to_context_string(self, limit: int = 10) -> str:
        """Convert recent memory to a context string for agents."""
        recent = self.get_recent(limit)
        if not recent:
            return "No shared memories yet."

        lines = ["## Shared Team Memory", ""]
        for entry in recent:
            tags_str = f" [{', '.join(entry.tags)}]" if entry.tags else ""
            lines.append(f"- **{entry.agent}** ({entry.timestamp[:10]}){tags_str}: {entry.content}")

        return "\n".join(lines)


class KnowledgeGraph:
    """Queryable knowledge graph for agent decisions."""

    def __init__(self, story_key: Optional[str] = None):
        self.story_key = story_key
        self.knowledge_dir = KNOWLEDGE_GRAPH_DIR
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        self.decisions: dict[str, Decision] = {}
        self.topic_index: dict[str, list[str]] = {}  # topic -> decision IDs
        self.handoffs: list[HandoffSummary] = []
        self._load()

    def _get_file_path(self) -> Path:
        """Get the knowledge graph file path."""
        if self.story_key:
            return self.knowledge_dir / f"kg_{self.story_key}.json"
        return self.knowledge_dir / "kg_global.json"

    def _load(self):
        """Load existing knowledge graph."""
        file_path = self._get_file_path()
        if file_path.exists():
            try:
                with open(file_path) as f:
                    data = json.load(f)
                    self.decisions = {
                        k: Decision.from_dict(v) for k, v in data.get("decisions", {}).items()
                    }
                    self.topic_index = data.get("topic_index", {})
                    self.handoffs = [HandoffSummary.from_dict(h) for h in data.get("handoffs", [])]
            except json.JSONDecodeError as e:
                print(f"Warning: Corrupted knowledge graph {file_path.name}, starting fresh: {e}")
            except KeyError as e:
                print(f"Warning: Invalid knowledge graph structure in {file_path.name}: {e}")

    def _save(self):
        """Save knowledge graph to disk."""
        file_path = self._get_file_path()
        with open(file_path, "w") as f:
            json.dump(
                {
                    "story_key": self.story_key,
                    "last_updated": datetime.now().isoformat(),
                    "decisions": {k: v.to_dict() for k, v in self.decisions.items()},
                    "topic_index": self.topic_index,
                    "handoffs": [h.to_dict() for h in self.handoffs],
                },
                f,
                indent=2,
            )

    def _generate_id(self) -> str:
        """Generate a unique decision ID."""
        import uuid

        return f"dec_{uuid.uuid4().hex[:8]}"

    def add_decision(
        self,
        agent: str,
        topic: str,
        decision: str,
        context: Optional[dict[str, Any]] = None,
        supersedes: Optional[str] = None,
    ) -> Decision:
        """Record a decision in the knowledge graph."""
        decision_id = self._generate_id()

        # Mark superseded decision
        if supersedes and supersedes in self.decisions:
            self.decisions[supersedes].status = "superseded"

        dec = Decision(
            id=decision_id,
            timestamp=datetime.now().isoformat(),
            agent=agent,
            topic=topic,
            decision=decision,
            context=context or {},
            supersedes=supersedes,
            status="active",
        )

        self.decisions[decision_id] = dec

        # Update topic index
        topic_key = topic.lower().replace(" ", "-")
        if topic_key not in self.topic_index:
            self.topic_index[topic_key] = []
        self.topic_index[topic_key].append(decision_id)

        self._save()
        return dec

    def query(self, question: str) -> Optional[dict[str, Any]]:
        """Query the knowledge graph with a natural language question."""
        question_lower = question.lower()

        # Extract potential topics from the question
        keywords = self._extract_keywords(question_lower)

        # Search for matching decisions
        matches = []
        for dec in self.decisions.values():
            if dec.status != "active":
                continue

            score = 0
            dec_text = f"{dec.topic} {dec.decision}".lower()

            for keyword in keywords:
                if keyword in dec_text:
                    score += 1
                if keyword in dec.topic.lower():
                    score += 2  # Topic matches are more relevant

            if score > 0:
                matches.append((score, dec))

        if not matches:
            return None

        # Return best match
        matches.sort(key=lambda x: x[0], reverse=True)
        best = matches[0][1]

        return {
            "decision": best.decision,
            "agent": best.agent,
            "topic": best.topic,
            "timestamp": best.timestamp,
            "context": best.context,
            "confidence": "high" if matches[0][0] > 2 else "medium",
        }

    def _extract_keywords(self, text: str) -> list[str]:
        """Extract relevant keywords from text."""
        # Remove common question words
        stop_words = {
            "what",
            "which",
            "who",
            "how",
            "why",
            "when",
            "where",
            "is",
            "are",
            "was",
            "were",
            "did",
            "does",
            "do",
            "the",
            "a",
            "an",
            "decided",
            "recommended",
            "suggested",
            "approach",
            "about",
        }

        words = re.findall(r"\b\w+\b", text.lower())
        return [w for w in words if w not in stop_words and len(w) > 2]

    def get_decisions_by_agent(self, agent: str) -> list[Decision]:
        """Get all active decisions by an agent."""
        return [d for d in self.decisions.values() if d.agent == agent and d.status == "active"]

    def get_decisions_by_topic(self, topic: str) -> list[Decision]:
        """Get all decisions for a topic."""
        topic_key = topic.lower().replace(" ", "-")
        decision_ids = self.topic_index.get(topic_key, [])
        return [
            self.decisions[did]
            for did in decision_ids
            if did in self.decisions and self.decisions[did].status == "active"
        ]

    def add_handoff(
        self,
        from_agent: str,
        to_agent: str,
        story_key: str,
        summary: str,
        key_decisions: Optional[list[str]] = None,
        blockers_resolved: Optional[list[str]] = None,
        watch_out_for: Optional[list[str]] = None,
        files_touched: Optional[list[str]] = None,
        next_steps: Optional[list[str]] = None,
    ) -> HandoffSummary:
        """Create a handoff summary between agents."""
        import uuid

        handoff = HandoffSummary(
            id=f"handoff_{uuid.uuid4().hex[:8]}",
            timestamp=datetime.now().isoformat(),
            from_agent=from_agent,
            to_agent=to_agent,
            story_key=story_key,
            summary=summary,
            key_decisions=key_decisions or [],
            blockers_resolved=blockers_resolved or [],
            watch_out_for=watch_out_for or [],
            files_touched=files_touched or [],
            next_steps=next_steps or [],
        )

        self.handoffs.append(handoff)
        self._save()
        return handoff

    def get_latest_handoff(self, to_agent: str) -> Optional[HandoffSummary]:
        """Get the most recent handoff for an agent."""
        for handoff in reversed(self.handoffs):
            if handoff.to_agent == to_agent:
                return handoff
        return None

    def get_handoffs_for_story(self, story_key: str) -> list[HandoffSummary]:
        """Get all handoffs for a story."""
        return [h for h in self.handoffs if h.story_key == story_key]

    def to_context_string(self) -> str:
        """Convert knowledge graph to context string for agents."""
        lines = ["## Project Knowledge Base", ""]

        # Active decisions
        active = [d for d in self.decisions.values() if d.status == "active"]
        if active:
            lines.append("### Active Decisions")
            for dec in sorted(active, key=lambda x: x.timestamp, reverse=True)[:10]:
                lines.append(f"- **{dec.topic}** ({dec.agent}): {dec.decision}")
            lines.append("")

        # Recent handoffs
        if self.handoffs:
            lines.append("### Recent Handoffs")
            for handoff in self.handoffs[-5:]:
                lines.append(
                    f"- {handoff.from_agent} -> {handoff.to_agent}: {handoff.summary[:100]}..."
                )
            lines.append("")

        return "\n".join(lines)


# Convenience functions for quick access
def get_shared_memory(story_key: Optional[str] = None) -> SharedMemory:
    """Get or create shared memory instance."""
    return SharedMemory(story_key)


def get_knowledge_graph(story_key: Optional[str] = None) -> KnowledgeGraph:
    """Get or create knowledge graph instance."""
    return KnowledgeGraph(story_key)


def record_decision(
    agent: str,
    topic: str,
    decision: str,
    story_key: Optional[str] = None,
    context: Optional[dict[str, Any]] = None,
) -> Decision:
    """Quick function to record a decision."""
    kg = get_knowledge_graph(story_key)
    return kg.add_decision(agent, topic, decision, context)


def share_learning(
    agent: str, content: str, story_key: Optional[str] = None, tags: Optional[list[str]] = None
) -> MemoryEntry:
    """Quick function to share a learning."""
    memory = get_shared_memory(story_key)
    return memory.add(agent, content, tags)


def create_handoff(
    from_agent: str, to_agent: str, story_key: str, summary: str, **kwargs
) -> HandoffSummary:
    """Quick function to create a handoff."""
    kg = get_knowledge_graph(story_key)
    return kg.add_handoff(from_agent, to_agent, story_key, summary, **kwargs)


def query_knowledge(question: str, story_key: Optional[str] = None) -> Optional[dict[str, Any]]:
    """Quick function to query the knowledge graph."""
    kg = get_knowledge_graph(story_key)
    return kg.query(question)


if __name__ == "__main__":
    # Demo usage
    print("=== Shared Memory Demo ===\n")

    # Create shared memory
    memory = SharedMemory(story_key="demo-story")

    # Add some entries
    memory.add(
        "ARCHITECT", "Decided to use PostgreSQL for user data", tags=["database", "decision"]
    )
    memory.add(
        "DEV",
        "Implemented user service with repository pattern",
        tags=["implementation", "patterns"],
    )
    memory.add(
        "REVIEWER", "Found missing input validation in auth module", tags=["review", "security"]
    )

    # Search
    print("Search results for 'database':")
    for entry in memory.search("database"):
        print(f"  - {entry.agent}: {entry.content}")

    print("\n" + memory.to_context_string())

    print("\n=== Knowledge Graph Demo ===\n")

    # Create knowledge graph
    kg = KnowledgeGraph(story_key="demo-story")

    # Add decisions
    kg.add_decision(
        "ARCHITECT",
        "authentication",
        "Use JWT with refresh tokens",
        context={"reason": "Stateless, scalable"},
    )
    kg.add_decision(
        "ARCHITECT",
        "database",
        "PostgreSQL for user data",
        context={"reason": "ACID compliance needed"},
    )
    kg.add_decision(
        "DEV", "state-management", "Use Redux Toolkit", context={"reason": "Team familiarity"}
    )

    # Query
    print("Query: 'What authentication approach was decided?'")
    result = kg.query("What authentication approach was decided?")
    if result:
        print(f"  Answer: {result['decision']} (by {result['agent']})")

    # Create handoff
    handoff = kg.add_handoff(
        from_agent="SM",
        to_agent="DEV",
        story_key="demo-story",
        summary="Story context created with all acceptance criteria defined",
        key_decisions=["Use existing UserService", "Follow repository pattern"],
        watch_out_for=["Rate limiting on profile uploads"],
        next_steps=["Implement user profile endpoint", "Add validation", "Write tests"],
    )

    print("\n" + handoff.to_markdown())
