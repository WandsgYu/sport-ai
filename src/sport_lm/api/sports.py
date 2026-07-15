"""Public placeholder for the removed legacy-platform adapter.

The private project used a platform-specific API and schema. None of its
addresses, credentials, request fields, response fields, or write behavior are
part of this educational snapshot.
"""

from __future__ import annotations

from typing import Any


PUBLIC_SNAPSHOT_MESSAGE = (
    "The legacy-platform adapter is intentionally unavailable in the public "
    "reference snapshot."
)


def _unavailable_result() -> dict[str, Any]:
    return {
        "ErrCode": 503,
        "Message": PUBLIC_SNAPSHOT_MESSAGE,
        "data": None,
    }


async def query_user_info(subject_id: str) -> dict[str, Any]:
    """Return a safe failure without contacting any external business system."""

    del subject_id
    return _unavailable_result()


async def update_user_data(submit_data: dict[str, Any]) -> dict[str, Any]:
    """Return a safe failure without performing any write operation."""

    del submit_data
    return _unavailable_result()
