"""Render docs/API.md from FastAPI's live OpenAPI schema."""

from pathlib import Path
from typing import Any

from app.main import app

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "API.md"


def schema_type(schema: dict[str, Any] | None) -> str:
    if not schema:
        return "—"
    ref = schema.get("$ref")
    if ref:
        return ref.rsplit("/", 1)[-1]
    if "anyOf" in schema or "oneOf" in schema:
        variants = schema.get("anyOf", schema.get("oneOf", []))
        return " | ".join(schema_type(variant) for variant in variants)
    if schema.get("type") == "array":
        return f"array of {schema_type(schema.get('items'))}"
    value = schema.get("type", "object")
    if "enum" in schema:
        value += " (" + ", ".join(map(str, schema["enum"])) + ")"
    return value


def render() -> str:
    spec = app.openapi()
    paths = spec.get("paths", {})
    tags = {tag: [] for tag in ("auth", "student", "teacher", "system")}
    for path, methods in paths.items():
        for method, operation in methods.items():
            tag = (operation.get("tags") or ["system"])[0]
            tags.setdefault(tag, []).append((path, method.upper(), operation))

    lines = [
        "# API reference",
        "",
        "Generated from the FastAPI OpenAPI schema by `PYTHONPATH=backend uv run python "
        "scripts/export_api_docs.py`.",
        "",
        f"OpenAPI version: `{spec.get('openapi', 'unknown')}` · "
        f"API version: `{spec.get('info', {}).get('version', 'unknown')}`",
        "",
        "All routes are under `/api/v1` except the system endpoints. Authenticated routes use a "
        "bearer token. Student identity is derived from the token; student endpoints accept no "
        "student ID.",
        "",
        'Errors use `{"error":{"code":string,"message":string,"details":object|null}}`. '
        "Login failures share one response. Attendance writes accept `dry_run=true` to preview "
        "without saving.",
        "",
    ]
    section_names = {
        "auth": "Authentication",
        "student": "Student routes",
        "teacher": "Teacher routes",
        "system": "System routes",
    }
    for tag, title in section_names.items():
        operations = sorted(tags.get(tag, []), key=lambda item: (item[0], item[1]))
        if not operations:
            continue
        lines.extend(
            [
                f"## {title}",
                "",
                "| Method | Path | Summary | Parameters | Request | Responses |",
                "| --- | --- | --- | --- | --- | --- |",
            ]
        )
        for path, method, operation in operations:
            params = operation.get("parameters", [])
            param_text = ", ".join(f"`{param['name']}` ({param['in']})" for param in params) or "—"
            request_schema = (
                operation.get("requestBody", {})
                .get("content", {})
                .get("application/json", {})
                .get("schema")
            )
            if request_schema is None:
                request_schema = (
                    operation.get("requestBody", {})
                    .get("content", {})
                    .get("multipart/form-data", {})
                    .get("schema")
                )
            request_text = schema_type(request_schema)
            responses = ", ".join(f"`{code}`" for code in operation.get("responses", {}))
            success_schema = next(
                (
                    response.get("content", {}).get("application/json", {}).get("schema")
                    for code, response in operation.get("responses", {}).items()
                    if code.startswith("2")
                    and response.get("content", {}).get("application/json", {}).get("schema")
                ),
                None,
            )
            if success_schema:
                responses += f" · {schema_type(success_schema)}"
            summary = operation.get("summary", "")
            cells = (f"`{method}`", f"`{path}`", summary, param_text, request_text, responses)
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")

    schemas = spec.get("components", {}).get("schemas", {})
    if schemas:
        lines.extend(["## OpenAPI schemas", ""])
        for name, schema in sorted(schemas.items()):
            properties = schema.get("properties", {})
            if not properties:
                continue
            required = set(schema.get("required", []))
            lines.extend(
                [
                    f"### `{name}`",
                    "",
                    "| Field | Type | Required | Notes |",
                    "| --- | --- | --- | --- |",
                ]
            )
            for field, field_schema in properties.items():
                field_type = schema_type(field_schema)
                notes = field_schema.get("description", "")
                required_text = "yes" if field in required else "no"
                cells = (f"`{field}`", field_type, required_text, notes)
                lines.append("| " + " | ".join(cells) + " |")
            lines.append("")
    return "\n".join(lines).rstrip() + "\n"


if __name__ == "__main__":
    OUTPUT.write_text(render(), encoding="utf-8")
    print(f"Wrote {OUTPUT.relative_to(ROOT)} from {len(app.openapi()['paths'])} OpenAPI paths.")
