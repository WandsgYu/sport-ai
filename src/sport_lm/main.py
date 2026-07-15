"""Non-deployable entry point for the public reference snapshot."""

from __future__ import annotations


PUBLIC_SNAPSHOT_NOTICE = (
    "Sport-LM is a sanitized learning snapshot. The private platform adapter, "
    "data model, credentials, and deployment entry point are not included."
)


def main() -> None:
    raise SystemExit(PUBLIC_SNAPSHOT_NOTICE)


if __name__ == "__main__":
    main()
