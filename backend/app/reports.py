from __future__ import annotations

import csv
import io
import json
from typing import Any


def _series_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    series = payload.get("series")
    return [dict(row) for row in series if isinstance(row, dict)] if isinstance(series, list) else []


def export_report(title: str, format: str, payload: dict[str, Any]) -> str:
    rows = _series_rows(payload)

    if format == "json":
        return json.dumps({"title": title, **payload}, indent=2)

    if format == "csv":
        output = io.StringIO()
        writer = csv.writer(output)
        if not rows:
            writer.writerow(["title", "note"])
            writer.writerow([title, "No benchmark series available"])
            return output.getvalue()

        keys: list[str] = []
        for row in rows:
            for key in row:
                if key not in keys:
                    keys.append(key)
        writer.writerow(keys)
        for row in rows:
            writer.writerow([row.get(key, "") for key in keys])
        return output.getvalue()

    lines = [f"# {title}", ""]
    config = payload.get("config")
    if isinstance(config, dict):
        lines.append("## Configuration")
        lines.append("")
        for key, value in config.items():
            rendered = ", ".join(str(item) for item in value) if isinstance(value, list) else value
            lines.append(f"- **{key.replace('_', ' ').title()}**: {rendered}")
        lines.append("")

    lines.append("## Results")
    lines.append("")
    if not rows:
        lines.append("No benchmark series available.")
        return "\n".join(lines) + "\n"

    keys = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    lines.append("| " + " | ".join(key.replace("_", " ").title() for key in keys) + " |")
    lines.append("| " + " | ".join("---" for _ in keys) + " |")
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(key, "")) for key in keys) + " |")

    skipped = payload.get("skipped")
    if isinstance(skipped, list) and skipped:
        lines.extend(["", "## Skipped Runs", ""])
        lines.append("| Input Size | Algorithm | Reason |")
        lines.append("| --- | --- | --- |")
        for item in skipped:
            lines.append(
                f"| {item.get('input_size', '')} | "
                f"{item.get('algorithm', '')} | {item.get('reason', '')} |"
            )

    lines.extend(
        [
            "",
            "Measurements exclude dataset generation, projection, matrix construction, "
            "network calls and rendering.",
            "",
        ]
    )
    return "\n".join(lines)
