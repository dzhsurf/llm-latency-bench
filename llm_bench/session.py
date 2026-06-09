from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from typing import TYPE_CHECKING

from llm_bench.config import BenchConfig
from llm_bench.datasets import DatasetItem

if TYPE_CHECKING:
    from llm_bench.runner import RunRecord

SESSION_VERSION = 1


def sort_items(items: list[DatasetItem]) -> list[DatasetItem]:
    return sorted(items, key=lambda i: (i.domain, i.target_tokens, i.case_index, i.id))


def plan_units(items: list[DatasetItem], concurrency_levels: list[int]) -> list[dict[str, Any]]:
    return [
        {"dataset_id": item.id, "concurrency": concurrency}
        for item in sort_items(items)
        for concurrency in concurrency_levels
    ]


def generate_session_id() -> str:
    date = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"{date}-{uuid.uuid4().hex[:8]}"


def session_dir(base_dir: str | Path, session_id: str) -> Path:
    return Path(base_dir) / session_id


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(path)


def config_fingerprint(config: BenchConfig, planned_units: list[dict[str, Any]]) -> str:
    payload = {
        "run": config.run.model_dump(),
        "matrix": config.matrix.model_dump(),
        "load": config.load_test.model_dump(),
        "planned_units": planned_units,
    }
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def unit_key(dataset_id: str, concurrency: int) -> tuple[str, int]:
    return (dataset_id, concurrency)


def record_from_dict(data: dict[str, Any]) -> RunRecord:
    from llm_bench.runner import RunRecord as RR

    return RR(**data)


def records_to_dicts(records: list[RunRecord]) -> list[dict[str, Any]]:
    return [asdict(r) for r in records]


class SessionStore:
    def __init__(self, path: Path, *, session_id: str, meta: dict[str, Any]) -> None:
        self.path = path
        self.session_id = session_id
        self.meta = meta
        self._completed: set[tuple[str, int]] = set()
        self._load_checkpoint()

    @property
    def total_units(self) -> int:
        return len(self.meta.get("planned_units", []))

    @property
    def completed_count(self) -> int:
        return len(self._completed)

    @property
    def elapsed_s(self) -> float:
        return float(self._checkpoint.get("elapsed_s", 0.0))

    @classmethod
    def create(
        cls,
        base_dir: str | Path,
        session_id: str,
        *,
        config: BenchConfig,
        config_path: str | None,
        planned_units: list[dict[str, Any]],
    ) -> SessionStore:
        path = session_dir(base_dir, session_id)
        if path.exists():
            raise FileExistsError(f"Session directory already exists: {path}")

        path.mkdir(parents=True, exist_ok=False)
        fingerprint = config_fingerprint(config, planned_units)
        meta = {
            "version": SESSION_VERSION,
            "session_id": session_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "config_path": config_path,
            "config": {
                "endpoint": config.endpoint.model_dump(),
                "run": config.run.model_dump(),
                "matrix": config.matrix.model_dump(),
                "load": config.load_test.model_dump(),
                "output": config.output.model_dump(),
            },
            "config_fingerprint": fingerprint,
            "planned_units": planned_units,
        }
        atomic_write_json(path / "meta.json", meta)
        atomic_write_json(
            path / "checkpoint.json",
            {
                "completed_units": [],
                "completed_count": 0,
                "total_units": len(planned_units),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "elapsed_s": 0.0,
            },
        )
        (path / "records.jsonl").touch()
        return cls(path, session_id=session_id, meta=meta)

    @classmethod
    def load(cls, base_dir: str | Path, session_id: str) -> SessionStore:
        path = session_dir(base_dir, session_id)
        meta_path = path / "meta.json"
        if not meta_path.is_file():
            raise FileNotFoundError(f"Session not found: {path}")

        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        if meta.get("version") != SESSION_VERSION:
            raise ValueError(f"Unsupported session version: {meta.get('version')}")

        return cls(path, session_id=session_id, meta=meta)

    def config_from_meta(self) -> BenchConfig:
        data = self.meta["config"]
        return BenchConfig.model_validate(
            {
                "endpoint": data["endpoint"],
                "run": data["run"],
                "matrix": data["matrix"],
                "load": data["load"],
                "output": data["output"],
            }
        )

    def _load_checkpoint(self) -> None:
        checkpoint_path = self.path / "checkpoint.json"
        if checkpoint_path.is_file():
            self._checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
        else:
            self._checkpoint = {
                "completed_units": [],
                "completed_count": 0,
                "total_units": self.total_units,
                "elapsed_s": 0.0,
            }

        self._completed = {
            unit_key(u["dataset_id"], int(u["concurrency"]))
            for u in self._checkpoint.get("completed_units", [])
        }

    def is_unit_done(self, dataset_id: str, concurrency: int) -> bool:
        return unit_key(dataset_id, concurrency) in self._completed

    def remaining_units(self) -> list[dict[str, Any]]:
        return [
            u
            for u in self.meta["planned_units"]
            if not self.is_unit_done(u["dataset_id"], int(u["concurrency"]))
        ]

    def load_records(self) -> list[RunRecord]:
        records_path = self.path / "records.jsonl"
        if not records_path.is_file():
            return []

        records: list[RunRecord] = []
        for line in records_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entry = json.loads(line)
            records.extend(record_from_dict(r) for r in entry.get("records", []))
        return records

    def append_unit(
        self,
        dataset_id: str,
        concurrency: int,
        records: list[RunRecord],
        elapsed_delta: float,
    ) -> None:
        key = unit_key(dataset_id, concurrency)
        if key in self._completed:
            return

        line = json.dumps(
            {
                "dataset_id": dataset_id,
                "concurrency": concurrency,
                "records": records_to_dicts(records),
            },
            separators=(",", ":"),
        )
        with (self.path / "records.jsonl").open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")

        self._completed.add(key)
        completed_units = [
            {"dataset_id": ds, "concurrency": cc} for ds, cc in sorted(self._completed)
        ]
        elapsed_total = self.elapsed_s + elapsed_delta
        checkpoint = {
            "completed_units": completed_units,
            "completed_count": len(completed_units),
            "total_units": self.total_units,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "elapsed_s": elapsed_total,
        }
        atomic_write_json(self.path / "checkpoint.json", checkpoint)
        self._checkpoint = checkpoint
