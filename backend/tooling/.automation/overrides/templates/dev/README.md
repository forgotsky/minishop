# Dev Agent Persona Templates

Pre-built personas for the Developer agent. Copy one to create your override file.

## Available Personas

| Persona | Best For |
|---------|----------|
| `senior-fullstack.yaml` | Full-stack development, architectural decisions |
| `junior-mentored.yaml` | Learning-focused, extra documentation |
| `security-focused.yaml` | Security-critical applications |
| `performance-engineer.yaml` | High-performance, optimization-heavy work |
| `rapid-prototyper.yaml` | Quick MVPs, hackathons, proof of concepts |

## How to Use

```bash
# From the overrides/templates directory:
cp dev/senior-fullstack.yaml ../dev.override.yaml

# Then customize the copied file for your project
```

## Creating Custom Personas

Use these templates as inspiration. Key elements to customize:

- **persona.role** - Your specific job title/role
- **persona.principles** - Your core development values
- **additional_rules** - Coding standards and patterns
- **memories** - Project-specific knowledge
- **critical_actions** - Pre-completion verification steps
