# Architect Agent Persona Templates

Pre-built personality configurations for the **Architect** agent.

## Available Templates

| Template | Focus | Best For |
|----------|-------|----------|
| `enterprise-architect.yaml` | Scalability, governance, long-term vision | Large organizations, complex systems |
| `cloud-native.yaml` | Distributed systems, microservices, cloud patterns | Modern cloud applications |
| `pragmatic-minimalist.yaml` | Simplicity, YAGNI, right-sizing solutions | Startups, MVPs, cost-conscious projects |

## Usage

```bash
# Use the personalization wizard
python3 tooling/scripts/personalize_agent.py architect

# Or manually copy a template
cp tooling/.automation/overrides/templates/architect/cloud-native.yaml \
   .automation/overrides/architect.override.yaml
```

## Customization

Each template can be further customized by editing the generated override file.
See the main [Override Templates README](../README.md) for details.
