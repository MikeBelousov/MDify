from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any


@dataclass
class WorkerResult:
    ok: bool
    input_path: str
    worker: str
    output_path: str | None = None
    engine: str | None = None
    ocr_used: bool = False
    warnings: list[str] = field(default_factory=list)
    error_code: str | None = None
    message: str | None = None
    details: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def success(
        cls,
        *,
        input_path: str,
        output_path: str,
        worker: str,
        engine: str,
        ocr_used: bool = False,
        warnings: list[str] | None = None,
    ) -> "WorkerResult":
        return cls(
            ok=True,
            input_path=input_path,
            output_path=output_path,
            worker=worker,
            engine=engine,
            ocr_used=ocr_used,
            warnings=warnings or [],
        )

    @classmethod
    def error(
        cls,
        *,
        input_path: str,
        worker: str,
        error_code: str,
        message: str,
        details: dict[str, Any] | None = None,
        warnings: list[str] | None = None,
    ) -> "WorkerResult":
        return cls(
            ok=False,
            input_path=input_path,
            worker=worker,
            error_code=error_code,
            message=message,
            details=details or {},
            warnings=warnings or [],
        )

    def to_json(self) -> str:
        payload: dict[str, Any] = {
            "ok": self.ok,
            "input_path": self.input_path,
            "worker": self.worker,
            "warnings": self.warnings,
        }
        if self.output_path is not None:
            payload["output_path"] = self.output_path
        if self.engine is not None:
            payload["engine"] = self.engine
        payload["ocr_used"] = self.ocr_used
        if self.error_code is not None:
            payload["error_code"] = self.error_code
        if self.message is not None:
            payload["message"] = self.message
        if self.details:
            payload["details"] = self.details
        return json.dumps(payload, ensure_ascii=False, sort_keys=True)
