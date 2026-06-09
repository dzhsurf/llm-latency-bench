from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from llm_bench.config import resolve_dataset_root


@dataclass
class DatasetItem:
    id: str
    domain: str
    target_tokens: int
    case_index: int
    output_style: str
    measured_tokens: int
    path: Path
    prompt: str
    task: str


def load_manifest(root: Path | None = None) -> list[DatasetItem]:
    root = root or resolve_dataset_root()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Dataset manifest not found: {manifest_path}")

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    items: list[DatasetItem] = []
    for entry in manifest["items"]:
        rel_path = entry["path"]
        file_path = root / rel_path
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        items.append(
            DatasetItem(
                id=entry["id"],
                domain=entry["domain"],
                target_tokens=entry["target_tokens"],
                case_index=int(entry.get("case_index", 1)),
                output_style=entry.get("output_style", data.get("output_style", "normal")),
                measured_tokens=entry["measured_tokens"],
                path=file_path,
                prompt=data["prompt"],
                task=data.get("task", ""),
            )
        )
    return items


def filter_items(
    items: list[DatasetItem],
    *,
    domains: dict[str, list[int]],
) -> list[DatasetItem]:
    selected: list[DatasetItem] = []
    for item in items:
        lengths = domains.get(item.domain)
        if lengths is None:
            continue
        if item.target_tokens in lengths:
            selected.append(item)
    return selected
