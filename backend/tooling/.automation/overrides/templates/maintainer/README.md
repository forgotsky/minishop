# Maintainer Agent Persona Templates

Pre-built personality configurations for the **Maintainer** agent.

## Available Templates

| Template | Focus | Best For |
|----------|-------|----------|
| `oss-maintainer.yaml` | Open source, community, contributions | Open source projects, community-driven development |
| `legacy-steward.yaml` | Legacy systems, stability, careful changes | Enterprise legacy systems, critical infrastructure |
| `devops-maintainer.yaml` | Infrastructure, automation, reliability | Platform teams, SRE, DevOps |

## Usage

```bash
# Use the personalization wizard
python3 tooling/scripts/personalize_agent.py maintainer

# Or manually copy a template
cp tooling/.automation/overrides/templates/maintainer/oss-maintainer.yaml \
   .automation/overrides/maintainer.override.yaml
```

## Customization

Each template can be further customized by editing the generated override file.
See the main [Override Templates README](../README.md) for details.
