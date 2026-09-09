# How Bedrock learns without rewriting its foundation

Bedrock v0.2 uses three levels of learning.

## Level 1: episodic memory

After a successful run, Bedrock stores a small local episode containing the task, result, and tools used. Relevant episodes are retrieved on later tasks. The memory is marked as untrusted context so it cannot override system rules.

## Level 2: durable lessons

The model may call `remember_lesson` for a reusable lesson. This always pauses for the local user's approval. Secrets and raw private conversations must not be stored.

## Level 3: recipe skills

The model may call `propose_recipe_skill` to combine existing tools into a reusable new tool. A skill has:

- a name and description;
- a strict parameter schema;
- one to eight ordered steps;
- placeholders such as `{{input.text}}` and `{{steps.0.result}}`.

The proposal is validated and requires approval before installation. Its risk is inherited from the riskiest child tool, so a learned skill containing file writes still requires approval whenever it runs.

Example concept:

```json
{
  "name": "write_timestamped_note",
  "description": "Write a note prefixed with the current local time",
  "parameters": {
    "type": "object",
    "properties": {
      "path": {"type": "string"},
      "text": {"type": "string"}
    },
    "required": ["path", "text"],
    "additionalProperties": false
  },
  "steps": [
    {"tool": "get_current_time", "arguments": {}},
    {
      "tool": "write_text_file",
      "arguments": {
        "path": "{{input.path}}",
        "content": "{{steps.0.result}} - {{input.text}}"
      }
    }
  ]
}
```

## What Bedrock does not learn automatically

It does not generate Python and import it into the running process. Truly new low-level capabilities require a later plugin-builder layer with a separate OS process/container, no network by default, read-only core source, tests, signed manifests, and explicit promotion. That is intentionally outside the v0.2 trusted core.
