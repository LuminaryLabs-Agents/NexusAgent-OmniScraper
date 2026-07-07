"""Run ledger utilities."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import time
from typing import Any


@dataclass(slots=True)
class LedgerEvent:
    stage: str
    message: str
    data: dict[str, Any] = field(default_factory=dict)
    timestamp_epoch: float = field(default_factory=time.time)


class RunLedger:
    def __init__(self, output_dir: str | Path) -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.path = self.output_dir / "run-ledger.jsonl"

    def append(self, stage: str, message: str, **data: Any) -> None:
        event = LedgerEvent(stage=stage, message=message, data=data)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
