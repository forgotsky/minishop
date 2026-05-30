# Writer Agent Persona Templates

Pre-built personality configurations for the **Writer** (Technical Writer) agent.

## Available Templates

| Template | Focus | Best For |
|----------|-------|----------|
| `api-documentarian.yaml` | API docs, references, developer experience | API products, developer platforms |
| `user-guide-author.yaml` | End-user documentation, tutorials, help | Consumer products, SaaS applications |
| `docs-as-code.yaml` | Automated docs, living documentation, CI/CD | Engineering teams, open source projects |

## Usage

```bash
# Use the personalization wizard
python3 tooling/scripts/personalize_agent.py writer

# Or manually copy a template
cp tooling/.automation/overrides/templates/writer/docs-as-code.yaml \
   .automation/overrides/writer.override.yaml
```

## Customization

Each template can be further customized by editing the generated override file.
See the main [Override Templates README](../README.md) for details.
