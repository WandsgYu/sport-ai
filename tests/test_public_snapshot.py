from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import tempfile
import unittest

from src.sport_lm.api.sports import query_user_info, update_user_data
from src.sport_lm.main import main
from src.sport_lm.security.privacy import pseudonymize, redact_text, sanitize
from src.sport_lm.tools import run_tool
from src.sport_lm.utils.event_log import log_event


class PublicSnapshotTests(unittest.TestCase):
    def test_legacy_adapter_is_disabled(self) -> None:
        query = asyncio.run(query_user_info("subject-demo-001"))
        update = asyncio.run(
            update_user_data(
                {"subject_id": "subject-demo-001", "selected_items": []}
            )
        )
        self.assertEqual(query["ErrCode"], 503)
        self.assertEqual(update["ErrCode"], 503)
        self.assertIsNone(query["data"])

    def test_cross_subject_tool_access_is_rejected(self) -> None:
        result = asyncio.run(
            run_tool(
                "query_user_info",
                json.dumps({"subject_id": "subject-demo-002"}),
                "missing.md",
                {"subject_id": "subject-demo-001"},
            )
        )
        self.assertEqual(json.loads(result)["ErrCode"], 403)

    def test_redaction_covers_common_sensitive_values(self) -> None:
        phone = "138" + "0013" + "8000"
        email = "demo" + "@" + "example.invalid"
        ip_address = ".".join(["203", "0", "113", "10"])
        identity_number = "110101" + "19900101" + "1234"
        sample_url = "https" + "://" + "internal.invalid/a"
        raw = (
            f"phone {phone} email {email} ip {ip_address} "
            f"id {identity_number} token=do-not-log url {sample_url}"
        )
        redacted = redact_text(raw)
        for value in (
            phone,
            email,
            ip_address,
            identity_number,
            "do-not-log",
            sample_url,
        ):
            self.assertNotIn(value, redacted)

    def test_recursive_sanitizer_removes_private_keys(self) -> None:
        payload = sanitize(
            {
                "type": "tool_call",
                "arguments": {"phone": "synthetic-private-value"},
                "nested": {"secret": "private-value"},
            }
        )
        self.assertEqual(payload["arguments"], "[REDACTED]")
        self.assertEqual(payload["nested"]["secret"], "[REDACTED]")

    def test_event_log_never_persists_raw_private_content(self) -> None:
        original_cwd = Path.cwd()
        with tempfile.TemporaryDirectory() as temp_dir:
            os.chdir(temp_dir)
            try:
                log_event(
                    {
                        "type": "user_input",
                        "request_id": "request-demo",
                        "subject_ref": pseudonymize("channel-user-demo"),
                        "text": "synthetic-private-message",
                        "result": {"secret": "private-value"},
                    }
                )
                stored = Path("logs/events.jsonl").read_text(encoding="utf-8")
            finally:
                os.chdir(original_cwd)
        self.assertNotIn("synthetic-private-message", stored)
        self.assertNotIn("private-value", stored)

    def test_public_entry_point_refuses_to_start(self) -> None:
        with self.assertRaises(SystemExit):
            main()


if __name__ == "__main__":
    unittest.main()
