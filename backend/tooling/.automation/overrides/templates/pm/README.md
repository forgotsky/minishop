# Project Manager Agent Persona Templates

Pre-built personality configurations for the **PM** (Project Manager) agent.

## Available Templates

| Template | Focus | Best For |
|----------|-------|----------|
| `traditional-pm.yaml` | Waterfall, Gantt charts, formal planning | Traditional enterprises, fixed-scope projects |
| `agile-pm.yaml` | Sprints, velocity, iterative delivery | Agile teams, product development |
| `hybrid-delivery.yaml` | Flexible methodology, stakeholder balance | Mixed environments, transformation projects |

## Usage

```bash
# Use the personalization wizard
python3 tooling/scripts/personalize_agent.py pm

# Or manually copy a template
cp tooling/.automation/overrides/templates/pm/agile-pm.yaml \
   .automation/overrides/pm.override.yaml
```

## Customization

Each template can be further customized by editing the generated override file.
See the main [Override Templates README](../README.md) for details.
