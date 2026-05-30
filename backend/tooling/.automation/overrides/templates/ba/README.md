# Business Analyst Agent Persona Templates

Pre-built personality configurations for the **BA** (Business Analyst) agent.

## Available Templates

| Template | Focus | Best For |
|----------|-------|----------|
| `requirements-engineer.yaml` | Formal requirements, traceability, specifications | Enterprise, regulated industries |
| `agile-storyteller.yaml` | User stories, acceptance criteria, BDD | Agile teams, product development |
| `domain-expert.yaml` | Domain modeling, ubiquitous language, DDD | Complex business domains |

## Usage

```bash
# Use the personalization wizard
python3 tooling/scripts/personalize_agent.py ba

# Or manually copy a template
cp tooling/.automation/overrides/templates/ba/agile-storyteller.yaml \
   .automation/overrides/ba.override.yaml
```

## Customization

Each template can be further customized by editing the generated override file.
See the main [Override Templates README](../README.md) for details.
