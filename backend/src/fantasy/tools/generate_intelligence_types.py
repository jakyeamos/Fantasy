from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from fantasy.main import create_app

SCHEMAS = [
    "AnalyzeUrlResponse",
    "BriefItem",
    "EventDetail",
    "EventType",
    "FootballEvent",
    "ImpactSummary",
    "IntelligenceRunResult",
    "LeagueImpact",
    "MorningBrief",
    "ParseStatus",
    "SourceObservation",
    "SourceOutcome",
    "SourceTier",
    "VerificationState",
]


def _type(schema: dict[str, Any]) -> str:
    if "$ref" in schema:
        return str(schema["$ref"]).rsplit("/", 1)[-1]
    if "anyOf" in schema:
        return " | ".join(dict.fromkeys(_type(item) for item in schema["anyOf"]))
    if "enum" in schema:
        return " | ".join(json.dumps(item) for item in schema["enum"])
    if "const" in schema:
        return json.dumps(schema["const"])
    kind = schema.get("type")
    if kind == "array":
        return f"Array<{_type(schema.get('items', {}))}>"
    if kind == "object":
        additional = schema.get("additionalProperties")
        if isinstance(additional, dict):
            return f"Record<string, {_type(additional)}>"
        properties = schema.get("properties", {})
        required = set(schema.get("required", []))
        fields = [
            f"{name}{'' if name in required else '?'}: {_type(value)}"
            for name, value in properties.items()
        ]
        return "{ " + "; ".join(fields) + " }"
    return {"string": "string", "integer": "number", "number": "number",
            "boolean": "boolean", "null": "null"}.get(kind, "unknown")


def render() -> str:
    schemas = create_app().openapi()["components"]["schemas"]
    blocks = [
        "// Generated from the FastAPI OpenAPI schema. Do not hand edit.",
        "// Run: uv run python -m fantasy.tools.generate_intelligence_types",
        "",
    ]
    for name in SCHEMAS:
        schema = schemas[name]
        blocks.append(f"export type {name} = {_type(schema)}")
        blocks.append("")
    return "\n".join(blocks)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[4]
    target = root / "frontend" / "src" / "api" / "intelligence.generated.ts"
    output = render()
    if args.check:
        return 0 if target.exists() and target.read_text() == output else 1
    target.write_text(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
