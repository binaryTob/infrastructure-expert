#!/usr/bin/env python3
"""Validate skill frontmatter, catalog dependencies, and workflow ordering."""

from __future__ import annotations

import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS_DIR = ROOT / "skills"
INDEX_PATH = SKILLS_DIR / "_index.yaml"
SCHEMA_PATH = SKILLS_DIR / "_schema.yaml"
SYNC_FIELDS = ("category", "phase", "risk", "execution_mode", "depends_on", "provides", "triggers")


def load_yaml(path: Path) -> dict:
    with path.open(encoding="utf-8") as handle:
        value = yaml.safe_load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"{path}: expected a YAML mapping")
    return value


def load_frontmatter(path: Path) -> dict:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: missing opening frontmatter delimiter")
    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise ValueError(f"{path}: missing closing frontmatter delimiter") from exc
    value = yaml.safe_load("\n".join(lines[1:end]))
    if not isinstance(value, dict):
        raise ValueError(f"{path}: frontmatter must be a YAML mapping")
    return value


def normalized(value: object) -> object:
    return [] if value is None else value


def main() -> int:
    errors: list[str] = []

    try:
        catalog = load_yaml(INDEX_PATH)
        schema = load_yaml(SCHEMA_PATH)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    entries = catalog.get("skills")
    workflows = catalog.get("workflows")
    if not isinstance(entries, list):
        print("ERROR: skills/_index.yaml: 'skills' must be a list", file=sys.stderr)
        return 1
    if not isinstance(workflows, dict):
        print("ERROR: skills/_index.yaml: 'workflows' must be a mapping", file=sys.stderr)
        return 1

    by_id: dict[str, dict] = {}
    required = set(schema.get("required", []))

    for position, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            errors.append(f"catalog entry {position}: expected mapping")
            continue
        skill_id = entry.get("id")
        relative_file = entry.get("file")
        if not isinstance(skill_id, str) or not skill_id:
            errors.append(f"catalog entry {position}: missing id")
            continue
        if skill_id in by_id:
            errors.append(f"duplicate skill id: {skill_id}")
            continue
        by_id[skill_id] = entry
        if not isinstance(relative_file, str) or not relative_file:
            errors.append(f"{skill_id}: missing file")
            continue

        path = SKILLS_DIR / relative_file
        if not path.is_file():
            errors.append(f"{skill_id}: file does not exist: skills/{relative_file}")
            continue
        try:
            metadata = load_frontmatter(path)
        except (OSError, ValueError, yaml.YAMLError) as exc:
            errors.append(str(exc))
            continue
        if metadata.get("id") != skill_id:
            errors.append(f"{skill_id}: frontmatter id is {metadata.get('id')!r}")
        missing = sorted(required - metadata.keys())
        if missing:
            errors.append(f"{skill_id}: missing required frontmatter: {', '.join(missing)}")
        for field in SYNC_FIELDS:
            if normalized(entry.get(field)) != normalized(metadata.get(field)):
                errors.append(f"{skill_id}: index/frontmatter differ for {field}")

    skill_ids = set(by_id)
    for skill_id, entry in by_id.items():
        dependencies = entry.get("depends_on", []) or []
        if not isinstance(dependencies, list):
            errors.append(f"{skill_id}: depends_on must be a list")
            continue
        for dependency in dependencies:
            if dependency not in skill_ids:
                errors.append(f"{skill_id}: unknown dependency {dependency}")

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(skill_id: str, trail: list[str]) -> None:
        if skill_id in visiting:
            errors.append(f"dependency cycle: {' -> '.join(trail + [skill_id])}")
            return
        if skill_id in visited:
            return
        visiting.add(skill_id)
        for dependency in by_id[skill_id].get("depends_on", []) or []:
            if dependency in by_id:
                visit(dependency, trail + [skill_id])
        visiting.remove(skill_id)
        visited.add(skill_id)

    for skill_id in by_id:
        visit(skill_id, [])

    for workflow_name, workflow in workflows.items():
        sequence = workflow.get("sequence") if isinstance(workflow, dict) else None
        if not isinstance(sequence, list):
            errors.append(f"workflow {workflow_name}: sequence must be a list")
            continue
        if len(sequence) != len(set(sequence)):
            errors.append(f"workflow {workflow_name}: duplicate skill in sequence")
        positions = {skill_id: index for index, skill_id in enumerate(sequence)}
        for skill_id in sequence:
            if skill_id not in by_id:
                errors.append(f"workflow {workflow_name}: unknown skill {skill_id}")
                continue
            for dependency in by_id[skill_id].get("depends_on", []) or []:
                if dependency not in positions:
                    errors.append(f"workflow {workflow_name}: {skill_id} missing dependency {dependency}")
                elif positions[dependency] > positions[skill_id]:
                    errors.append(f"workflow {workflow_name}: {dependency} must precede {skill_id}")

    catalog_files = {entry.get("file") for entry in entries if isinstance(entry, dict)}
    for path in SKILLS_DIR.glob("**/*.md"):
        relative = path.relative_to(SKILLS_DIR).as_posix()
        if relative.startswith("common/") or relative == "_template.md":
            continue
        if relative not in catalog_files:
            errors.append(f"uncataloged skill file: skills/{relative}")

    for error in errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(f"Validated {len(by_id)} skills and {len(workflows)} workflows: {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
