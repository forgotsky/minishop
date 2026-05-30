#!/usr/bin/env python3
"""
Create Persona - Custom Agent Persona Builder

This interactive tool helps create custom agent personas for the Devflow
workflow system. It generates properly formatted agent files that can be
used with the run-story.sh automation.

Usage:
    python create-persona.py                    # Interactive mode
    python create-persona.py --name qa          # Quick create with defaults
    python create-persona.py --from-template    # Create from existing template
    python create-persona.py --list             # List existing personas
    python create-persona.py --validate <name>  # Validate a persona file
"""

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

from lib.colors import Colors

# Persona templates
PERSONA_TEMPLATES = {
    "developer": {
        "role": "Software Developer",
        "focus": "Writing clean, maintainable code",
        "model": "sonnet",
        "responsibilities": [
            "Implement features according to specifications",
            "Write unit and integration tests",
            "Follow coding standards and best practices",
            "Document code appropriately",
        ],
        "principles": [
            "Write code that is easy to understand and maintain",
            "Test first when possible",
            "Keep functions small and focused",
            "Handle errors gracefully",
        ],
    },
    "reviewer": {
        "role": "Code Reviewer",
        "focus": "Ensuring code quality and best practices",
        "model": "sonnet",
        "responsibilities": [
            "Review code for correctness and quality",
            "Identify potential bugs and security issues",
            "Suggest improvements and optimizations",
            "Ensure coding standards compliance",
        ],
        "principles": [
            "Be constructive, not critical",
            "Focus on important issues first",
            "Explain the 'why' behind suggestions",
            "Acknowledge good patterns",
        ],
    },
    "architect": {
        "role": "Software Architect",
        "focus": "System design and technical decisions",
        "model": "opus",
        "responsibilities": [
            "Design system architecture",
            "Make technology decisions",
            "Document architectural decisions (ADRs)",
            "Ensure scalability and maintainability",
        ],
        "principles": [
            "Separation of concerns",
            "Dependency inversion",
            "Design for change",
            "Keep it simple",
        ],
    },
    "tester": {
        "role": "QA Engineer",
        "focus": "Quality assurance and testing",
        "model": "sonnet",
        "responsibilities": [
            "Design test strategies",
            "Write automated tests",
            "Perform exploratory testing",
            "Report and track bugs",
        ],
        "principles": [
            "Test early, test often",
            "Cover edge cases",
            "Automate repetitive tests",
            "Think like a user",
        ],
    },
    "security": {
        "role": "Security Engineer",
        "focus": "Application security and vulnerability prevention",
        "model": "opus",
        "responsibilities": [
            "Review code for security vulnerabilities",
            "Recommend security best practices",
            "Audit authentication and authorization",
            "Identify potential attack vectors",
        ],
        "principles": [
            "Defense in depth",
            "Principle of least privilege",
            "Never trust user input",
            "Secure by default",
        ],
    },
    "devops": {
        "role": "DevOps Engineer",
        "focus": "CI/CD, infrastructure, and deployment",
        "model": "sonnet",
        "responsibilities": [
            "Set up and maintain CI/CD pipelines",
            "Manage infrastructure as code",
            "Monitor and optimize deployments",
            "Automate operational tasks",
        ],
        "principles": [
            "Automate everything",
            "Infrastructure as code",
            "Monitor proactively",
            "Fail fast, recover faster",
        ],
    },
    "documentation": {
        "role": "Technical Writer",
        "focus": "Clear and comprehensive documentation",
        "model": "sonnet",
        "responsibilities": [
            "Write user documentation",
            "Create API documentation",
            "Maintain README files",
            "Document processes and procedures",
        ],
        "principles": [
            "Write for the audience",
            "Keep it simple and clear",
            "Include examples",
            "Keep docs up to date",
        ],
    },
}


@dataclass
class PersonaConfig:
    """Configuration for a custom persona."""

    name: str
    role: str
    focus: str
    model: str = "sonnet"
    responsibilities: list[str] = field(default_factory=list)
    principles: list[str] = field(default_factory=list)
    working_directories: dict[str, str] = field(default_factory=dict)
    tech_stack: list[str] = field(default_factory=list)
    critical_rules: list[str] = field(default_factory=list)
    communication_style: str = ""
    custom_sections: dict[str, str] = field(default_factory=dict)


def print_header():
    """Print the tool header."""
    print()
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print(f"{Colors.CYAN}  CUSTOM PERSONA BUILDER{Colors.NC}")
    print(f"{Colors.CYAN}{'═' * 70}{Colors.NC}")
    print()


def prompt(message: str, default: str = "", required: bool = False) -> str:
    """Prompt for user input."""
    if default:
        display = f"{Colors.BLUE}{message}{Colors.NC} [{default}]: "
    else:
        display = f"{Colors.BLUE}{message}{Colors.NC}: "

    while True:
        value = input(display).strip()
        if not value and default:
            return default
        if not value and required:
            print(f"{Colors.YELLOW}This field is required.{Colors.NC}")
            continue
        return value


def prompt_list(message: str, min_items: int = 0) -> list[str]:
    """Prompt for a list of items."""
    print(f"{Colors.BLUE}{message}{Colors.NC}")
    print("  (Enter items one per line, empty line to finish)")

    items = []
    while True:
        item = input(f"  {len(items) + 1}. ").strip()
        if not item:
            if len(items) >= min_items:
                break
            print(f"{Colors.YELLOW}Please enter at least {min_items} item(s).{Colors.NC}")
            continue
        items.append(item)

    return items


def prompt_choice(message: str, choices: list[str], default: str = "") -> str:
    """Prompt for a choice from a list."""
    print(f"{Colors.BLUE}{message}{Colors.NC}")
    for i, choice in enumerate(choices, 1):
        marker = " (default)" if choice == default else ""
        print(f"  {i}. {choice}{marker}")

    while True:
        value = input("Choice: ").strip()
        if not value and default:
            return default

        # Accept number or text
        if value.isdigit():
            idx = int(value) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        elif value in choices:
            return value

        print(f"{Colors.YELLOW}Please enter a valid choice.{Colors.NC}")


def interactive_create() -> PersonaConfig:
    """Interactive persona creation wizard."""
    print(f"{Colors.BOLD}Let's create your custom agent persona!{Colors.NC}")
    print()

    # Basic info
    name = prompt("Persona name (e.g., 'qa', 'frontend-dev')", required=True)
    name = name.lower().replace(" ", "-")

    # Check for template
    print()
    print(f"{Colors.BOLD}Would you like to start from a template?{Colors.NC}")
    templates = list(PERSONA_TEMPLATES.keys())
    templates.insert(0, "none (start fresh)")
    template = prompt_choice("Select template", templates, "none (start fresh)")

    if template != "none (start fresh)" and template in PERSONA_TEMPLATES:
        tpl = PERSONA_TEMPLATES[template]
        role = prompt("Role", tpl["role"])
        focus = prompt("Focus", tpl["focus"])
        model = prompt_choice("Model", ["sonnet", "opus", "haiku"], tpl["model"])
        responsibilities = tpl["responsibilities"].copy()
        principles = tpl["principles"].copy()

        print()
        print(
            f"{Colors.GREEN}Template loaded!{Colors.NC} Default responsibilities and principles applied."
        )
        modify = prompt("Would you like to modify them? (y/n)", "n")

        if modify.lower() == "y":
            print()
            print("Current responsibilities:")
            for r in responsibilities:
                print(f"  - {r}")
            if prompt("Modify responsibilities? (y/n)", "n").lower() == "y":
                responsibilities = prompt_list("Enter responsibilities", 1)

            print()
            print("Current principles:")
            for p in principles:
                print(f"  - {p}")
            if prompt("Modify principles? (y/n)", "n").lower() == "y":
                principles = prompt_list("Enter principles", 1)
    else:
        role = prompt("Role (e.g., 'Senior QA Engineer')", required=True)
        focus = prompt("Focus (one-line description)", required=True)
        model = prompt_choice("Model", ["sonnet", "opus", "haiku"], "sonnet")

        print()
        responsibilities = prompt_list("What are this agent's responsibilities?", 2)

        print()
        principles = prompt_list("What principles should this agent follow?", 2)

    # Communication style
    print()
    communication_style = prompt(
        "Communication style (e.g., 'Technical and detailed', 'Friendly and explanatory')",
        "Professional and clear",
    )

    # Working directories (optional)
    print()
    add_dirs = prompt("Add working directories? (y/n)", "n")
    working_dirs = {}
    if add_dirs.lower() == "y":
        print("Enter directory mappings (name: path), empty to finish:")
        while True:
            dir_name = input("  Name: ").strip()
            if not dir_name:
                break
            dir_path = input("  Path: ").strip()
            working_dirs[dir_name] = dir_path

    # Tech stack (optional)
    print()
    add_tech = prompt("Add tech stack context? (y/n)", "n")
    tech_stack = []
    if add_tech.lower() == "y":
        tech_stack = prompt_list("Enter technologies this agent works with")

    # Critical rules
    print()
    add_rules = prompt("Add critical rules (must-do actions)? (y/n)", "n")
    critical_rules = []
    if add_rules.lower() == "y":
        critical_rules = prompt_list("Enter critical rules")

    return PersonaConfig(
        name=name,
        role=role,
        focus=focus,
        model=model,
        responsibilities=responsibilities,
        principles=principles,
        working_directories=working_dirs,
        tech_stack=tech_stack,
        critical_rules=critical_rules,
        communication_style=communication_style,
    )


def generate_persona_markdown(config: PersonaConfig) -> str:
    """Generate the persona markdown file content."""
    lines = [
        f"# {config.role} Agent",
        "",
        f"You are a {config.role}. {config.focus}",
        "",
    ]

    # Responsibilities
    lines.extend(
        [
            "## Responsibilities",
            "",
        ]
    )
    for i, resp in enumerate(config.responsibilities, 1):
        lines.append(f"{i}. {resp}")
    lines.append("")

    # Working directories
    if config.working_directories:
        lines.extend(
            [
                "## Working Directory",
                "",
            ]
        )
        for name, path in config.working_directories.items():
            lines.append(f"- **{name}**: `{path}`")
        lines.append("")

    # Tech stack
    if config.tech_stack:
        lines.extend(
            [
                "## Tech Stack",
                "",
            ]
        )
        for tech in config.tech_stack:
            lines.append(f"- {tech}")
        lines.append("")

    # Principles
    lines.extend(
        [
            "## Principles",
            "",
        ]
    )
    for i, principle in enumerate(config.principles, 1):
        lines.append(
            f"{i}. **{principle.split(':')[0]}**"
            + (f": {':'.join(principle.split(':')[1:])}" if ":" in principle else "")
        )
    lines.append("")

    # Communication style
    if config.communication_style:
        lines.extend(
            [
                "## Communication Style",
                "",
                config.communication_style,
                "",
            ]
        )

    # Critical rules
    if config.critical_rules:
        lines.extend(
            [
                "## Critical Rules",
                "",
            ]
        )
        for rule in config.critical_rules:
            lines.append(f"- {rule}")
        lines.append("")

    # Context management (standard section)
    lines.extend(
        [
            "## Context Management",
            "",
            "You are running in an automated pipeline with limited context window. To avoid losing work:",
            "",
            "1. **Work incrementally** - Complete and save files one at a time",
            "2. **Checkpoint frequently** - After each significant change, ensure the file is written",
            "3. **Monitor your progress** - If you notice you've been working for a while, prioritize critical items",
            "4. **Self-assess context usage** - If you estimate you're past 80% of your context:",
            "   - Finish the current file you're working on",
            "   - Write a summary of remaining work",
            "   - Complete what you can rather than leaving partial work",
            "",
            "If you sense context is running low, output a warning:",
            "```",
            " CONTEXT WARNING: Approaching context limit. Prioritizing completion of current task.",
            "```",
            "",
        ]
    )

    # Model recommendation
    lines.extend(
        [
            "## Model",
            "",
            f"Recommended model: `{config.model}`",
            "",
        ]
    )

    return "\n".join(lines)


def generate_override_yaml(config: PersonaConfig) -> str:
    """Generate an override YAML file for the persona."""
    lines = [
        f"# {config.name.upper()} Agent Override",
        "# Customize this agent's behavior without modifying the core agent file",
        "# These settings survive updates to the core agent",
        "",
        "# Additional rules (appended to base agent rules)",
        "additional_rules:",
    ]

    for rule in config.critical_rules or config.principles[:2]:
        lines.append(f'  - "{rule}"')

    lines.extend(
        [
            "",
            "# Memories - facts this agent should always remember",
            "memories:",
            '  - "Example memory: add project-specific context here"',
            "",
            "# Critical actions - must be done before completing any task",
            "critical_actions:",
        ]
    )

    for rule in config.critical_rules or ["Verify work meets requirements"]:
        lines.append(f'  - "{rule}"')

    lines.extend(
        [
            "",
            f"# Model override (recommended: {config.model})",
            f'# model: "{config.model}"',
            "",
            "# Budget override (optional)",
            "# max_budget_usd: 10.00",
            "",
        ]
    )

    return "\n".join(lines)


def save_persona(config: PersonaConfig, project_root: Path) -> tuple:
    """Save the persona files."""
    agents_dir = project_root / "tooling" / ".automation" / "agents"
    overrides_dir = project_root / "tooling" / ".automation" / "overrides"

    agents_dir.mkdir(parents=True, exist_ok=True)
    overrides_dir.mkdir(parents=True, exist_ok=True)

    # Save agent file
    agent_file = agents_dir / f"{config.name}.md"
    agent_content = generate_persona_markdown(config)
    agent_file.write_text(agent_content)

    # Save override template
    override_file = overrides_dir / f"{config.name}.override.yaml"
    if not override_file.exists():
        override_content = generate_override_yaml(config)
        override_file.write_text(override_content)

    return agent_file, override_file


def list_personas(project_root: Path):
    """List existing personas."""
    agents_dir = project_root / "tooling" / ".automation" / "agents"

    print(f"{Colors.BOLD}Available Agent Personas:{Colors.NC}")
    print()

    if not agents_dir.exists():
        print(f"  {Colors.YELLOW}No agents directory found.{Colors.NC}")
        return

    for agent_file in sorted(agents_dir.glob("*.md")):
        name = agent_file.stem

        # Extract first line (role)
        content = agent_file.read_text()
        first_line = content.split("\n")[0]
        role = first_line.replace("# ", "").replace(" Agent", "")

        # Check for override
        override_file = (
            project_root / "tooling" / ".automation" / "overrides" / f"{name}.override.yaml"
        )
        has_override = "[OK]" if override_file.exists() else " "

        print(f"  {Colors.GREEN}{name:15}{Colors.NC} │ {role:25} │ Override: {has_override}")

    print()


def validate_persona(name: str, project_root: Path) -> bool:
    """Validate a persona file."""
    agent_file = project_root / "tooling" / ".automation" / "agents" / f"{name}.md"

    if not agent_file.exists():
        print(f"{Colors.RED}[X] Agent file not found: {agent_file}{Colors.NC}")
        return False

    print(f"{Colors.BOLD}Validating persona: {name}{Colors.NC}")
    print()

    content = agent_file.read_text()
    errors = []
    warnings = []

    # Check for required sections
    required_sections = ["Responsibilities", "Principles"]
    for section in required_sections:
        if f"## {section}" not in content:
            errors.append(f"Missing required section: {section}")

    # Check for role definition
    if not content.startswith("# "):
        errors.append("Missing role heading (should start with '# Role Agent')")

    # Check for context management
    if "Context Management" not in content:
        warnings.append("Missing Context Management section (recommended)")

    # Print results
    for error in errors:
        print(f"  {Colors.RED}[ERROR]{Colors.NC} {error}")

    for warning in warnings:
        print(f"  {Colors.YELLOW}[WARNING]{Colors.NC} {warning}")

    if not errors and not warnings:
        print(f"  {Colors.GREEN}[OK] Persona is valid!{Colors.NC}")

    print()
    return len(errors) == 0


def main():
    parser = argparse.ArgumentParser(description="Create custom agent personas")
    parser.add_argument("--name", help="Quick create with this name")
    parser.add_argument(
        "--template", help="Use this template (developer, reviewer, architect, etc.)"
    )
    parser.add_argument("--list", action="store_true", help="List existing personas")
    parser.add_argument("--validate", help="Validate a persona file")
    parser.add_argument(
        "--from-template", action="store_true", help="Create from template selection"
    )
    args = parser.parse_args()

    # Find project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent.parent

    print_header()

    if args.list:
        list_personas(project_root)
        return

    if args.validate:
        valid = validate_persona(args.validate, project_root)
        sys.exit(0 if valid else 1)

    if args.name and args.template:
        # Quick create with template
        if args.template not in PERSONA_TEMPLATES:
            print(f"{Colors.RED}Unknown template: {args.template}{Colors.NC}")
            print(f"Available: {', '.join(PERSONA_TEMPLATES.keys())}")
            sys.exit(1)

        tpl = PERSONA_TEMPLATES[args.template]
        config = PersonaConfig(
            name=args.name,
            role=tpl["role"],
            focus=tpl["focus"],
            model=tpl["model"],
            responsibilities=tpl["responsibilities"],
            principles=tpl["principles"],
        )
    elif args.from_template:
        # Template selection mode
        print(f"{Colors.BOLD}Available Templates:{Colors.NC}")
        print()
        for name, tpl in PERSONA_TEMPLATES.items():
            print(f"  {Colors.GREEN}{name:15}{Colors.NC} - {tpl['role']}: {tpl['focus']}")
        print()

        template = prompt_choice(
            "Select a template",
            list(PERSONA_TEMPLATES.keys()),
        )

        persona_name = prompt("Persona name", template)
        tpl = PERSONA_TEMPLATES[template]

        config = PersonaConfig(
            name=persona_name,
            role=tpl["role"],
            focus=tpl["focus"],
            model=tpl["model"],
            responsibilities=tpl["responsibilities"],
            principles=tpl["principles"],
        )
    else:
        # Interactive mode
        config = interactive_create()

    # Save files
    print()
    agent_file, override_file = save_persona(config, project_root)

    print(f"{Colors.GREEN}[OK] Persona created successfully!{Colors.NC}")
    print()
    print(f"  Agent file:    {agent_file}")
    print(f"  Override file: {override_file}")
    print()
    print(f"{Colors.BOLD}Next steps:{Colors.NC}")
    print(f"  1. Review and customize: {agent_file}")
    print(f"  2. Add project-specific memories: {override_file}")
    print(f"  3. Use with: ./run-story.sh <story> --agent {config.name}")
    print()


if __name__ == "__main__":
    main()
