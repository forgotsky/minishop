"""
Devflow Library - Core modules for the Devflow automation system.

This package provides:
- colors: Shared terminal color codes
- platform: Cross-platform detection utilities
- cost_tracker: Token usage and cost tracking
- cost_display: Terminal-based cost monitoring display
- cost_config: Configuration management for costs
- currency_converter: Multi-currency support
- context_monitor: Real-time context window tracking
- errors: Enhanced error handling
- agent_router: Dynamic agent selection
- agent_handoff: Structured agent transitions
- shared_memory: Cross-agent knowledge sharing
- swarm_orchestrator: Multi-agent collaboration
- validation_loop: Three-tier validation framework

Usage:
    from lib.cost_tracker import CostTracker
    from lib.context_monitor import ContextMonitor, StatusLine, get_status_manager
    from lib.agent_router import AgentRouter
    from lib.colors import Colors
    from lib.platform import get_platform, IS_WINDOWS
"""

__version__ = "1.20.1"

# Lazy imports to avoid circular dependencies
__all__ = [
    "colors",
    "platform",
    "cost_tracker",
    "cost_display",
    "cost_config",
    "currency_converter",
    "context_monitor",
    "errors",
    "agent_router",
    "agent_handoff",
    "shared_memory",
    "swarm_orchestrator",
    "validation_loop",
]
