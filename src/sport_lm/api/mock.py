from __future__ import annotations

from copy import deepcopy
from typing import Any


class SyntheticSportsAdapter:
    """In-memory adapter used only by the public, offline demonstration."""

    def __init__(self) -> None:
        self._subjects: dict[str, dict[str, Any]] = {}
        self._idempotency_results: dict[str, dict[str, Any]] = {}
        self.write_count = 0

    async def query_user_info(self, subject_id: str) -> dict[str, Any]:
        state = self._subjects.get(
            subject_id,
            {"subject_id": subject_id, "selected_items": []},
        )
        return {"ErrCode": 0, "Message": "ok", "data": deepcopy(state)}

    async def update_user_data(
        self,
        submit_data: dict[str, Any],
        *,
        idempotency_key: str,
    ) -> dict[str, Any]:
        if idempotency_key in self._idempotency_results:
            replay = deepcopy(self._idempotency_results[idempotency_key])
            replay["idempotent_replay"] = True
            return replay

        self.write_count += 1
        operation_id = f"synthetic-enrollment-{self.write_count:03d}"
        stored = {
            "subject_id": submit_data["subject_id"],
            "selected_items": list(submit_data.get("selected_items", [])),
            "operation_id": operation_id,
        }
        self._subjects[submit_data["subject_id"]] = stored
        result = {
            "ErrCode": 0,
            "Message": "synthetic update completed",
            "data": deepcopy(stored),
            "idempotent_replay": False,
        }
        self._idempotency_results[idempotency_key] = deepcopy(result)
        return result
