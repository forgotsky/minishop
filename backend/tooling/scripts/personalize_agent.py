#!/usr/bin/env python3
"""
Agent Personalization Wizard

Interactive wizard to customize agent personas and create override files.
Guides users through selecting templates and customizing settings.

Usage:
    python3 personalize_agent.py [agent_name]
    python3 personalize_agent.py              # Interactive selection
    python3 personalize_agent.py dev          # Personalize dev agent
    python3 personalize_agent.py --all        # Personalize all agents
"""

import argparse
import shutil
import sys
from pathlib import Path
from typing import Optional

from lib.colors import Colors

# Find project paths
SCRIPT_DIR = Path(__file__).parent.resolve()
PROJECT_ROOT = SCRIPT_DIR.parent.parent
OVERRIDES_DIR = PROJECT_ROOT / ".automation" / "overrides"
TEMPLATES_DIR = OVERRIDES_DIR / "templates"
AGENTS_DIR = PROJECT_ROOT / ".automation" / "agents"


def print_banner():
    """Print the wizard banner."""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║           AGENT PERSONALIZATION WIZARD                        ║
╠═══════════════════════════════════════════════════════════════╣
║  Customize your AI agents for your project and preferences    ║
╚═══════════════════════════════════════════════════════════════╝{Colors.END}
""")


def print_step(step_num: int, title: str):
    """Print a step header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}═══ Step {step_num}: {title} ═══{Colors.END}\n")


def get_available_agents() -> list[str]:
    """Get list of available agents."""
    agents = []
    if AGENTS_DIR.exists():
        for file in AGENTS_DIR.glob("*.md"):
            agents.append(file.stem)
    return sorted(agents)


def get_agent_templates(agent_name: str) -> list[dict]:
    """Get available templates for an agent."""
    templates = []
    agent_template_dir = TEMPLATES_DIR / agent_name

    if agent_template_dir.exists():
        for file in agent_template_dir.glob("*.yaml"):
            if file.name != "README.md":
                # Read first few lines to get description
                content = file.read_text()
                first_line = content.split("\n")[0].replace("#", "").strip()
                templates.append({"name": file.stem, "path": file, "description": first_line})

    return templates


def prompt_choice(prompt: str, options: list[str], default: int = 0) -> int:
    """Prompt user to choose from options."""
    print(f"{Colors.YELLOW}{prompt}{Colors.END}")
    for i, opt in enumerate(options):
        marker = "->" if i == default else " "
        print(f"  {marker} [{i + 1}] {opt}")

    while True:
        try:
            response = input(
                f"\nEnter choice [1-{len(options)}] (default: {default + 1}): "
            ).strip()
            if not response:
                return default
            choice = int(response) - 1
            if 0 <= choice < len(options):
                return choice
            print(f"{Colors.RED}Please enter a number between 1 and {len(options)}{Colors.END}")
        except ValueError:
            print(f"{Colors.RED}Please enter a valid number{Colors.END}")


def prompt_yes_no(prompt: str, default: bool = True) -> bool:
    """Prompt for yes/no answer."""
    default_str = "Y/n" if default else "y/N"
    response = input(f"{Colors.YELLOW}{prompt} [{default_str}]: {Colors.END}").strip().lower()
    if not response:
        return default
    return response in ("y", "yes")


def prompt_input(prompt: str, default: str = "") -> str:
    """Prompt for text input."""
    if default:
        response = input(
            f"{Colors.YELLOW}{prompt}{Colors.END} [{Colors.BLUE}{default}{Colors.END}]: "
        ).strip()
        return response if response else default
    return input(f"{Colors.YELLOW}{prompt}: {Colors.END}").strip()


def prompt_list(prompt: str, existing: list[str] = None) -> list[str]:
    """Prompt for a list of items."""
    print(f"{Colors.YELLOW}{prompt}{Colors.END}")
    print(f"{Colors.CYAN}(Enter items one per line, empty line to finish){Colors.END}")

    if existing:
        print("\nCurrent items:")
        for item in existing:
            print(f"  - {item}")
        if not prompt_yes_no("Keep these items?", default=True):
            existing = []

    items = existing or []
    print("\nEnter new items:")
    while True:
        item = input("  - ").strip()
        if not item:
            break
        items.append(item)

    return items


def get_user_profile() -> dict:
    """Get or create user profile."""
    profile_path = OVERRIDES_DIR / "user-profile.yaml"

    if profile_path.exists():
        print(f"{Colors.GREEN}Found existing user profile{Colors.END}")
        if not prompt_yes_no("Update user profile?", default=False):
            return {}

    print_step(1, "User Profile")

    profile = {
        "name": prompt_input("Your name", "Developer"),
        "technical_level": prompt_choice(
            "Your technical level:", ["Junior", "Mid-level", "Senior", "Principal/Staff"], default=2
        ),
        "communication_style": prompt_choice(
            "Preferred communication style:",
            [
                "Concise - brief and to the point",
                "Balanced - moderate detail",
                "Detailed - thorough explanations",
            ],
            default=1,
        ),
    }

    level_map = ["junior", "mid", "senior", "principal"]
    style_map = ["concise", "balanced", "detailed"]

    return {
        "user": {
            "name": profile["name"],
            "technical_level": level_map[profile["technical_level"]],
            "communication_style": style_map[profile["communication_style"]],
        }
    }


def customize_agent(agent_name: str) -> Optional[dict]:
    """Run customization wizard for a single agent."""
    print(f"\n{Colors.BOLD}Personalizing: {agent_name.upper()} Agent{Colors.END}")
    print("=" * 50)

    # Check for templates
    templates = get_agent_templates(agent_name)

    override = {}

    # Step 1: Template selection
    if templates:
        print_step(1, "Select Base Template")
        print(f"Found {len(templates)} pre-built persona(s) for {agent_name}:\n")

        options = ["Start from scratch (no template)"]
        for t in templates:
            options.append(f"{t['name']}: {t['description']}")

        choice = prompt_choice("Choose a starting point:", options, default=1)

        if choice > 0:
            template = templates[choice - 1]
            print(f"\n{Colors.GREEN}Using template: {template['name']}{Colors.END}")
            # Copy template content (in a real implementation, parse YAML)
            shutil.copy(template["path"], OVERRIDES_DIR / f"{agent_name}.override.yaml")
            print(f"Template copied to: {agent_name}.override.yaml")

            if not prompt_yes_no("Customize further?", default=True):
                return None

    # Step 2: Persona customization
    print_step(2, "Persona Definition")

    if prompt_yes_no("Define a custom persona?", default=True):
        override["persona"] = {
            "role": prompt_input("Role title", f"Senior {agent_name.title()} Specialist"),
            "identity": prompt_input(
                "Identity description", "A focused professional who delivers quality work"
            ),
        }

        print("\nDefine your core principles (what guides your decisions):")
        principles = prompt_list("Principles:")
        if principles:
            override["persona"]["principles"] = principles

    # Step 3: Rules
    print_step(3, "Additional Rules")

    if prompt_yes_no("Add custom coding/working rules?", default=True):
        rules = prompt_list("Enter rules the agent should follow:")
        if rules:
            override["additional_rules"] = rules

    # Step 4: Memories
    print_step(4, "Project Context (Memories)")

    if prompt_yes_no("Add project-specific knowledge?", default=True):
        memories = prompt_list("Enter facts the agent should always remember:")
        if memories:
            override["memories"] = memories

    # Step 5: Critical actions
    print_step(5, "Critical Actions")

    if prompt_yes_no("Define actions that must happen before completing tasks?", default=True):
        actions = prompt_list("Enter critical verification steps:")
        if actions:
            override["critical_actions"] = actions

    # Step 6: Model and budget
    print_step(6, "Model & Budget")

    if prompt_yes_no("Configure model and budget?", default=False):
        model_choice = prompt_choice(
            "Preferred model:",
            ["Sonnet (faster, cheaper)", "Opus (smarter, more expensive)"],
            default=0,
        )
        override["model"] = "sonnet" if model_choice == 0 else "opus"

        budget = prompt_input("Max budget per task (USD)", "15.00")
        try:
            override["max_budget_usd"] = float(budget)
        except ValueError:
            pass

    return override if override else None


def save_override(agent_name: str, override: dict):
    """Save override to YAML file."""

    override_path = OVERRIDES_DIR / f"{agent_name}.override.yaml"

    # Add header comment
    content = f"# {agent_name.title()} Agent Override\n"
    content += "# Generated by Personalization Wizard\n"
    content += "# Customize further as needed\n\n"

    # Simple YAML-like output (avoiding yaml dependency issues)
    def write_yaml(data, indent=0):
        result = ""
        prefix = "  " * indent
        for key, value in data.items():
            if isinstance(value, dict):
                result += f"{prefix}{key}:\n"
                result += write_yaml(value, indent + 1)
            elif isinstance(value, list):
                result += f"{prefix}{key}:\n"
                for item in value:
                    result += f'{prefix}  - "{item}"\n'
            elif isinstance(value, (int, float)):
                result += f"{prefix}{key}: {value}\n"
            else:
                result += f'{prefix}{key}: "{value}"\n'
        return result

    content += write_yaml(override)

    override_path.write_text(content)
    print(f"\n{Colors.GREEN} Saved: {override_path}{Colors.END}")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive wizard to personalize AI agent behavior"
    )
    parser.add_argument("agent", nargs="?", help="Agent name to personalize")
    parser.add_argument("--all", action="store_true", help="Personalize all agents")
    parser.add_argument("--list", action="store_true", help="List available agents and templates")

    args = parser.parse_args()

    print_banner()

    # Ensure directories exist
    OVERRIDES_DIR.mkdir(parents=True, exist_ok=True)

    # List mode
    if args.list:
        print(f"{Colors.BOLD}Available Agents:{Colors.END}")
        for agent in get_available_agents():
            templates = get_agent_templates(agent)
            template_count = len(templates)
            print(f"  • {agent} ({template_count} template(s))")
            for t in templates:
                print(f"      - {t['name']}: {t['description']}")
        return

    # Get user profile first
    profile = get_user_profile()
    if profile:
        # Save user profile
        profile_path = OVERRIDES_DIR / "user-profile.yaml"
        content = "# User Profile\n# Global preferences for all agents\n\n"
        for section, values in profile.items():
            content += f"{section}:\n"
            for key, value in values.items():
                content += f'  {key}: "{value}"\n'
        profile_path.write_text(content)
        print(f"\n{Colors.GREEN} User profile saved{Colors.END}")

    # Determine agents to personalize
    agents = get_available_agents()

    if args.all:
        agents_to_personalize = agents
    elif args.agent:
        if args.agent not in agents:
            print(f"{Colors.RED}Unknown agent: {args.agent}{Colors.END}")
            print(f"Available: {', '.join(agents)}")
            return 1
        agents_to_personalize = [args.agent]
    else:
        # Interactive agent selection
        print_step(2, "Select Agent to Personalize")
        options = agents + ["All agents"]
        choice = prompt_choice("Which agent would you like to personalize?", options)

        if choice == len(agents):
            agents_to_personalize = agents
        else:
            agents_to_personalize = [agents[choice]]

    # Personalize each agent
    for agent in agents_to_personalize:
        override = customize_agent(agent)
        if override:
            save_override(agent, override)

    print(f"\n{Colors.GREEN}{Colors.BOLD} Personalization complete!{Colors.END}")
    print(f"\nYour overrides are in: {OVERRIDES_DIR}")
    print("They will be applied automatically when running agents.")
    print("\nTo modify later, edit the .override.yaml files directly.")


if __name__ == "__main__":
    sys.exit(main() or 0)
