# Override Templates

Pre-configured templates for customizing agent behavior. **No override files exist by default** - you create them by copying templates from this directory.

## Quick Start

```bash
# 1. Create your user profile (applies to all agents)
cp templates/user-profile.template.yaml user-profile.yaml

# 2. Copy an agent persona template
cp templates/dev/senior-fullstack.yaml dev.override.yaml

# 3. Edit the copied files to customize for your project
```

## User Profile Template

The `user-profile.template.yaml` configures global settings for all agents:
- Your name and preferred language
- Technical experience level
- Code style preferences
- Project-specific context

## Agent Persona Templates

Each agent has pre-built persona templates in their respective directories:

| Agent | Templates | Description |
|-------|-----------|-------------|
| [`dev/`](dev/) | 5 templates | Developer personas (senior, junior, security, performance, prototyper) |
| [`reviewer/`](reviewer/) | 3 templates | Code reviewer styles (thorough, mentoring, quick) |
| [`sm/`](sm/) | 3 templates | Scrum master approaches (agile coach, tech lead, startup) |
| [`architect/`](architect/) | 3 templates | Architecture focus (enterprise, cloud-native, minimalist) |
| [`ba/`](ba/) | 3 templates | Business analyst styles (requirements, agile, domain) |
| [`pm/`](pm/) | 3 templates | Project management approaches (traditional, agile, hybrid) |
| [`writer/`](writer/) | 3 templates | Documentation focus (API, user guide, docs-as-code) |
| [`maintainer/`](maintainer/) | 3 templates | Maintenance styles (OSS, legacy, DevOps) |

### Using the Personalization Wizard

The easiest way to apply templates is with the wizard:

```bash
python3 tooling/scripts/personalize_agent.py [agent]

# Or use the Claude Code slash command
/personalize dev
```

## How to Use

1. **Copy the template** to the overrides directory (one level up):
   ```bash
   # From the templates directory:
   cp user-profile.template.yaml ../user-profile.yaml
   cp dev/senior-fullstack.yaml ../dev.override.yaml
   ```

2. **Customize** the copied file:
   - Update your name, preferences, and project context
   - Add project-specific memories
   - Adjust rules to match your conventions

3. **Test** by running a story or invoking an agent

**Note**: Override files are git-ignored by default to keep your personal settings private.

## Template Structure

Each template includes:

- **persona**: Customizes the agent's role and communication style
- **additional_rules**: Extra rules appended to the base agent
- **memories**: Facts the agent should always remember
- **critical_actions**: Actions to perform before completing tasks
- **Framework sections**: Commented sections for popular frameworks

## Creating Custom Templates

Use these templates as starting points. Key sections to customize:

```yaml
# Your persona
persona:
  role: "Your Role Title"
  identity: "Description of approach"
  principles:
    - "Your guiding principles"

# Project-specific rules
additional_rules:
  - "Your coding standards"

# What the agent should always know
memories:
  - "Project-specific facts"

# Verification steps
critical_actions:
  - "Pre-completion checks"
```

## Contributing New Templates

We welcome new templates for:
- Game development (Unity, Unreal)
- Embedded systems
- Desktop applications (Electron, Tauri)
- Blockchain/Web3
- Specific frameworks (Django, Rails, Spring Boot)

See [CONTRIBUTING.md](../../../../CONTRIBUTING.md) for guidelines.
